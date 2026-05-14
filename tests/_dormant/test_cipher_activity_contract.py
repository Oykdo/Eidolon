#!/usr/bin/env python3
"""
Contract tests for the Cipher Activity Processor (use-to-earn pipeline).

Verifies:
- Metrics ingestion and validation
- Resonance delta computation (activity → resonance gain)
- Entropy delta computation (inactivity → entropy growth, activity → decay)
- Epoch rate limiting (1 per 24h)
- Inactivity grace period before entropy penalty
- Score clamping (0-100)
- Persistent history
- End-to-end yield impact via resonance/entropy factors
"""

import sys
import types
import shutil
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

if "Eidolon" not in sys.modules:
    sys.modules["Eidolon"] = types.ModuleType("Eidolon")

import pytest

from core.cipher_activity_processor import (
    CipherActivityMetrics,
    CipherActivityProcessor,
    EpochResult,
    EPOCH_DURATION_SECONDS,
    ENTROPY_DECAY_PER_ACTIVE_EPOCH,
    ENTROPY_GROWTH_PER_INACTIVE_EPOCH,
    INACTIVITY_GRACE_EPOCHS,
    MAX_RESONANCE_GAIN_PER_EPOCH,
    RESONANCE_PER_CONVERSATION,
    RESONANCE_PER_KEY_VERIFICATION,
    RESONANCE_PER_MESSAGE,
)
from core.eidolon_economy import resonance_factor, entropy_factor


@pytest.fixture
def tmp_dir():
    d = tempfile.mkdtemp(prefix="cipher_activity_test_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def processor(tmp_dir):
    return CipherActivityProcessor(storage_dir=tmp_dir)


@pytest.fixture
def t0():
    return datetime(2026, 4, 10, 12, 0, 0, tzinfo=timezone.utc)


VAULT = "vault_test_001"


# ============================================================================
# METRICS DATACLASS
# ============================================================================

class TestCipherActivityMetrics:
    def test_empty_metrics_not_active(self):
        m = CipherActivityMetrics()
        assert m.is_active() is False

    def test_messages_make_active(self):
        m = CipherActivityMetrics(messages_sent=1)
        assert m.is_active() is True

    def test_conversations_make_active(self):
        m = CipherActivityMetrics(active_conversations=1)
        assert m.is_active() is True

    def test_verifications_make_active(self):
        m = CipherActivityMetrics(key_verifications=1)
        assert m.is_active() is True

    def test_from_dict_clamps_negatives(self):
        m = CipherActivityMetrics.from_dict({"messages_sent": -5})
        assert m.messages_sent == 0

    def test_roundtrip(self):
        m = CipherActivityMetrics(messages_sent=10, active_conversations=3, key_verifications=1)
        d = m.to_dict()
        m2 = CipherActivityMetrics.from_dict(d)
        assert m2.messages_sent == 10
        assert m2.active_conversations == 3
        assert m2.key_verifications == 1


# ============================================================================
# RESONANCE DELTA
# ============================================================================

class TestResonanceDelta:
    def test_zero_activity_gives_zero_resonance(self):
        m = CipherActivityMetrics()
        assert CipherActivityProcessor.compute_resonance_delta(m) == 0.0

    def test_messages_contribute(self):
        m = CipherActivityMetrics(messages_sent=20)
        delta = CipherActivityProcessor.compute_resonance_delta(m)
        assert delta == 20 * RESONANCE_PER_MESSAGE

    def test_conversations_contribute(self):
        m = CipherActivityMetrics(active_conversations=3)
        delta = CipherActivityProcessor.compute_resonance_delta(m)
        assert abs(delta - 3 * RESONANCE_PER_CONVERSATION) < 0.001

    def test_verifications_contribute(self):
        m = CipherActivityMetrics(key_verifications=2)
        delta = CipherActivityProcessor.compute_resonance_delta(m)
        assert delta == 2 * RESONANCE_PER_KEY_VERIFICATION

    def test_combined_activity(self):
        m = CipherActivityMetrics(messages_sent=10, active_conversations=2, key_verifications=1)
        expected = 10 * 0.05 + 2 * 0.8 + 1 * 2.0
        assert CipherActivityProcessor.compute_resonance_delta(m) == expected

    def test_capped_at_max(self):
        m = CipherActivityMetrics(messages_sent=500, active_conversations=20, key_verifications=10)
        delta = CipherActivityProcessor.compute_resonance_delta(m)
        assert delta == MAX_RESONANCE_GAIN_PER_EPOCH


# ============================================================================
# ENTROPY DELTA
# ============================================================================

class TestEntropyDelta:
    def test_active_epoch_decays_entropy(self):
        m = CipherActivityMetrics(messages_sent=5)
        delta = CipherActivityProcessor.compute_entropy_delta(m, 0)
        assert delta == ENTROPY_DECAY_PER_ACTIVE_EPOCH
        assert delta < 0  # Must be negative (decay)

    def test_inactive_within_grace_no_penalty(self):
        m = CipherActivityMetrics()
        for i in range(INACTIVITY_GRACE_EPOCHS):
            delta = CipherActivityProcessor.compute_entropy_delta(m, i)
            assert delta == 0.0

    def test_inactive_after_grace_grows_entropy(self):
        m = CipherActivityMetrics()
        delta = CipherActivityProcessor.compute_entropy_delta(m, INACTIVITY_GRACE_EPOCHS)
        assert delta == ENTROPY_GROWTH_PER_INACTIVE_EPOCH
        assert delta > 0  # Must be positive (growth)

    def test_activity_resets_entropy_growth(self):
        m = CipherActivityMetrics(messages_sent=1)
        # Even after 100 inactive epochs, activity still decays entropy
        delta = CipherActivityProcessor.compute_entropy_delta(m, 100)
        assert delta == ENTROPY_DECAY_PER_ACTIVE_EPOCH


# ============================================================================
# EPOCH PROCESSING
# ============================================================================

class TestEpochProcessing:
    def test_first_epoch_always_allowed(self, processor, t0):
        metrics = CipherActivityMetrics(messages_sent=10, active_conversations=2)
        result = processor.process_epoch(VAULT, metrics, now=t0)
        assert not result.was_rate_limited
        assert result.is_active
        assert result.resonance_delta > 0

    def test_rate_limited_within_epoch(self, processor, t0):
        metrics = CipherActivityMetrics(messages_sent=10)
        processor.process_epoch(VAULT, metrics, now=t0)
        # Second submission within same epoch
        t1 = t0 + timedelta(hours=12)
        result = processor.process_epoch(VAULT, metrics, now=t1)
        assert result.was_rate_limited
        assert result.resonance_delta == 0

    def test_next_epoch_allowed_after_24h(self, processor, t0):
        metrics = CipherActivityMetrics(messages_sent=10)
        processor.process_epoch(VAULT, metrics, now=t0)
        t1 = t0 + timedelta(seconds=EPOCH_DURATION_SECONDS)
        result = processor.process_epoch(VAULT, metrics, now=t1)
        assert not result.was_rate_limited

    def test_resonance_increases_from_activity(self, processor, t0):
        metrics = CipherActivityMetrics(messages_sent=20, active_conversations=3)
        result = processor.process_epoch(VAULT, metrics, current_resonance=50.0, now=t0)
        assert result.resonance_after > result.resonance_before

    def test_entropy_decreases_from_activity(self, processor, t0):
        metrics = CipherActivityMetrics(messages_sent=5)
        result = processor.process_epoch(
            VAULT, metrics, current_entropy=20.0, now=t0
        )
        assert result.entropy_after < result.entropy_before

    def test_inactivity_streak_tracked(self, processor, t0):
        empty = CipherActivityMetrics()
        for i in range(5):
            t = t0 + timedelta(days=i)
            result = processor.process_epoch(VAULT, empty, now=t)
        assert result.consecutive_inactive_epochs == 5

    def test_activity_resets_inactivity_streak(self, processor, t0):
        empty = CipherActivityMetrics()
        for i in range(4):
            processor.process_epoch(VAULT, empty, now=t0 + timedelta(days=i))
        active = CipherActivityMetrics(messages_sent=5)
        result = processor.process_epoch(VAULT, active, now=t0 + timedelta(days=4))
        assert result.consecutive_inactive_epochs == 0


# ============================================================================
# CLAMPING
# ============================================================================

class TestClamping:
    def test_resonance_capped_at_100(self, processor, t0):
        metrics = CipherActivityMetrics(messages_sent=50, active_conversations=5, key_verifications=3)
        result = processor.process_epoch(
            VAULT, metrics, current_resonance=98.0, now=t0
        )
        assert result.resonance_after <= 100.0

    def test_resonance_floor_at_0(self, processor, t0):
        # Resonance doesn't go below 0 (no negative gain from activity)
        metrics = CipherActivityMetrics()
        result = processor.process_epoch(
            VAULT, metrics, current_resonance=0.0, now=t0
        )
        assert result.resonance_after >= 0.0

    def test_entropy_floor_at_0(self, processor, t0):
        metrics = CipherActivityMetrics(messages_sent=100)
        result = processor.process_epoch(
            VAULT, metrics, current_entropy=0.5, now=t0
        )
        assert result.entropy_after >= 0.0

    def test_entropy_capped_at_100(self, processor, t0):
        empty = CipherActivityMetrics()
        result = processor.process_epoch(
            VAULT, empty, current_entropy=99.5,
            now=t0,
        )
        # Even with grace period (delta=0), entropy stays bounded
        assert result.entropy_after <= 100.0


# ============================================================================
# PERSISTENCE
# ============================================================================

class TestPersistence:
    def test_summary_tracks_lifetime(self, processor, t0):
        for i in range(3):
            m = CipherActivityMetrics(messages_sent=10, active_conversations=2, key_verifications=1)
            processor.process_epoch(VAULT, m, now=t0 + timedelta(days=i))
        summary = processor.get_vault_activity_summary(VAULT)
        assert summary["total_epochs_processed"] == 3
        assert summary["lifetime_messages"] == 30
        assert summary["lifetime_conversations"] == 6
        assert summary["lifetime_key_verifications"] == 3

    def test_history_limited_to_30(self, processor, t0):
        m = CipherActivityMetrics(messages_sent=1)
        for i in range(40):
            processor.process_epoch(VAULT, m, now=t0 + timedelta(days=i))
        history = processor.get_recent_history(VAULT, limit=100)
        assert len(history) <= 30

    def test_recent_history_returns_last_n(self, processor, t0):
        m = CipherActivityMetrics(messages_sent=1)
        for i in range(10):
            processor.process_epoch(VAULT, m, now=t0 + timedelta(days=i))
        recent = processor.get_recent_history(VAULT, limit=3)
        assert len(recent) == 3

    def test_reset_clears_state(self, processor, t0):
        m = CipherActivityMetrics(messages_sent=10)
        processor.process_epoch(VAULT, m, now=t0)
        processor.reset_vault_metrics(VAULT)
        summary = processor.get_vault_activity_summary(VAULT)
        assert summary["total_epochs_processed"] == 0


# ============================================================================
# END-TO-END: activity → resonance/entropy → yield factor
# ============================================================================

class TestEndToEndYieldImpact:
    def test_active_vault_better_yield_factors(self, processor, t0):
        """Simulate 7 days of active usage and verify yield factors improve."""
        resonance = 50.0
        entropy = 20.0

        for day in range(7):
            metrics = CipherActivityMetrics(
                messages_sent=30,
                active_conversations=5,
                key_verifications=1,
            )
            result = processor.process_epoch(
                VAULT, metrics,
                current_resonance=resonance,
                current_entropy=entropy,
                now=t0 + timedelta(days=day),
            )
            resonance = result.resonance_after
            entropy = result.entropy_after

        # Resonance should have increased
        assert resonance > 50.0
        # Entropy should have decreased
        assert entropy < 20.0

        # Yield factors should be favorable
        res_f = resonance_factor(resonance)
        ent_f = entropy_factor(entropy)
        assert res_f > 1.0    # Above neutral
        assert ent_f > 0.9    # Low penalty

    def test_inactive_vault_worse_yield_factors(self, processor, t0):
        """Simulate 10 days of inactivity and verify yield factors degrade."""
        resonance = 60.0
        entropy = 10.0

        for day in range(10):
            metrics = CipherActivityMetrics()  # zero activity
            result = processor.process_epoch(
                VAULT, metrics,
                current_resonance=resonance,
                current_entropy=entropy,
                now=t0 + timedelta(days=day),
            )
            resonance = result.resonance_after
            entropy = result.entropy_after

        # Resonance unchanged (no activity, no gain)
        assert resonance == 60.0
        # Entropy should have grown (after grace period)
        assert entropy > 10.0

        ent_f = entropy_factor(entropy)
        assert ent_f < 1.0  # Yield penalized
