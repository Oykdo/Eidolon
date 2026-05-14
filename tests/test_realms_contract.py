"""
Eidolon Realms - Contract Tests

Tests the Realms temporal engine, ensuring:
- Epoch distribution follows tier multipliers
- Decay applies correctly to inactive realms
- Vesting schedule works as expected
- Governance voting weight is based on vested epochs
- Anti-replay protection works
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

from src.holo.realms import (
    RealmEngine,
    RealmRegistry,
    Realm,
    RealmMembership,
    RealmStatus,
    MemberRole,
    ProposalStatus,
)
from src.holo.realms.models import (
    REALM_CREATION_COST,
    TIER_EPOCH_MULTIPLIERS,
    EPOCH_TO_EIDOLON_BASE_RATE,
    INACTIVITY_DECAY_START_EPOCHS,
    DECAY_RATE_PER_EPOCH,
    VESTING_RATE_PER_WEEK,
    MIN_MEMBERSHIP_EPOCHS_FOR_VESTING,
    MIN_EPOCHS_TO_CREATE_PROPOSAL,
    MIN_EPOCHS_TO_VOTE,
)
from src.holo.realms.cipher_hook import CipherActivityHook, ActivityEvent


class TestRealmCreation:
    """Tests for Realm creation"""
    
    @pytest.fixture
    def temp_data_dir(self):
        """Create a temporary data directory"""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def engine(self, temp_data_dir):
        """Create a RealmEngine with temporary storage"""
        registry = RealmRegistry(data_dir=temp_data_dir)
        engine = RealmEngine(registry=registry)
        engine.set_current_epoch(1000)
        return engine
    
    def test_create_realm_success(self, engine):
        """Test successful realm creation"""
        realm, membership, tx = engine.create_realm(
            name="Test Realm",
            description="A test realm for unit testing",
            creator_vault_id="vault_001",
            creator_vault_tier="elite",
            creator_eidolon_balance=1000.0,
        )
        
        assert realm.name == "Test Realm"
        assert realm.creator_vault_id == "vault_001"
        assert realm.created_at_epoch == 1000
        assert realm.status == RealmStatus.ACTIVE.value
        assert membership.role == MemberRole.CREATOR.value
        assert membership.vault_tier == "elite"
        assert tx["cost"] == REALM_CREATION_COST
    
    def test_create_realm_insufficient_balance(self, engine):
        """Test realm creation fails with insufficient balance"""
        with pytest.raises(ValueError, match="Insufficient EIDOLON"):
            engine.create_realm(
                name="Test Realm",
                description="A test realm",
                creator_vault_id="vault_001",
                creator_eidolon_balance=100.0,  # Less than REALM_CREATION_COST
            )
    
    def test_create_realm_invalid_name(self, engine):
        """Test realm creation fails with invalid name"""
        with pytest.raises(ValueError, match="at least 3 characters"):
            engine.create_realm(
                name="AB",  # Too short
                description="A test realm",
                creator_vault_id="vault_001",
                creator_eidolon_balance=1000.0,
            )


class TestMembership:
    """Tests for Realm membership"""
    
    @pytest.fixture
    def temp_data_dir(self):
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def engine_with_realm(self, temp_data_dir):
        registry = RealmRegistry(data_dir=temp_data_dir)
        engine = RealmEngine(registry=registry)
        engine.set_current_epoch(1000)
        
        realm, _, _ = engine.create_realm(
            name="Test Realm",
            description="A test realm",
            creator_vault_id="creator_vault",
            creator_eidolon_balance=1000.0,
        )
        return engine, realm
    
    def test_join_realm(self, engine_with_realm):
        """Test joining a realm"""
        engine, realm = engine_with_realm
        
        membership = engine.join_realm(
            realm_id=realm.id,
            vault_id="member_vault",
            vault_tier="pioneer",
        )
        
        assert membership.realm_id == realm.id
        assert membership.vault_id == "member_vault"
        assert membership.vault_tier == "pioneer"
        assert membership.role == MemberRole.MEMBER.value
        assert membership.epochs_accumulated == 0.0
    
    def test_join_realm_twice_fails(self, engine_with_realm):
        """Test that joining twice fails"""
        engine, realm = engine_with_realm
        
        engine.join_realm(realm_id=realm.id, vault_id="member_vault")
        
        with pytest.raises(ValueError, match="already member"):
            engine.join_realm(realm_id=realm.id, vault_id="member_vault")
    
    def test_leave_realm_with_vesting(self, engine_with_realm):
        """Test leaving a realm applies vesting"""
        engine, realm = engine_with_realm
        
        membership = engine.join_realm(
            realm_id=realm.id,
            vault_id="member_vault",
            vault_tier="pioneer",
        )
        
        # Simulate time passing (5 weeks = 840 epochs)
        engine.set_current_epoch(1000 + 840)
        
        # Manually add some epochs
        membership.epochs_accumulated = 100.0
        engine.registry.update_membership(membership)
        
        _, vesting_info = engine.leave_realm(realm.id, "member_vault")
        
        # After 5 weeks, should be 100% vested (5 * 20% = 100%)
        assert vesting_info["vested_ratio"] == 1.0
        assert vesting_info["epochs_retained"] == 100.0
        assert vesting_info["epochs_forfeited"] == 0.0
    
    def test_leave_realm_early_forfeit(self, engine_with_realm):
        """Test leaving early forfeits unvested epochs"""
        engine, realm = engine_with_realm
        
        membership = engine.join_realm(
            realm_id=realm.id,
            vault_id="member_vault",
        )
        
        # Simulate 1 week (168 epochs)
        engine.set_current_epoch(1000 + 168)
        
        membership.epochs_accumulated = 100.0
        engine.registry.update_membership(membership)
        
        _, vesting_info = engine.leave_realm(realm.id, "member_vault")
        
        # After 1 week, should be 20% vested
        assert vesting_info["vested_ratio"] == pytest.approx(0.2, rel=0.1)
        assert vesting_info["epochs_retained"] == pytest.approx(20.0, rel=1)
        assert vesting_info["epochs_forfeited"] == pytest.approx(80.0, rel=1)
    
    def test_creator_cannot_leave(self, engine_with_realm):
        """Test that realm creator cannot leave"""
        engine, realm = engine_with_realm
        
        with pytest.raises(ValueError, match="creator cannot leave"):
            engine.leave_realm(realm.id, "creator_vault")


class TestEpochDistribution:
    """Tests for epoch distribution with tier multipliers"""
    
    @pytest.fixture
    def temp_data_dir(self):
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def engine_with_members(self, temp_data_dir):
        registry = RealmRegistry(data_dir=temp_data_dir)
        engine = RealmEngine(registry=registry)
        engine.set_current_epoch(1000)
        
        realm, _, _ = engine.create_realm(
            name="Test Realm",
            description="A test realm",
            creator_vault_id="supreme_vault",
            creator_vault_tier="supreme",
            creator_eidolon_balance=1000.0,
        )
        
        # Add members with different tiers
        engine.join_realm(realm.id, "elite_vault", "elite")
        engine.join_realm(realm.id, "pioneer_vault", "pioneer")
        engine.join_realm(realm.id, "standard_vault", "standard")
        
        return engine, realm
    
    def test_tier_multipliers_applied(self, engine_with_members):
        """Test that tier multipliers affect epoch rewards"""
        engine, realm = engine_with_members
        
        # Queue activity for all members at current epoch
        for vault_id in ["supreme_vault", "elite_vault", "pioneer_vault", "standard_vault"]:
            engine.record_activity(realm.id, vault_id, "message")
        
        # Process tick (activities are processed immediately)
        ticks = engine.process_tick(1000)
        
        # Verify different tiers got different rewards
        supreme_m = engine.registry.get_membership(realm.id, "supreme_vault")
        elite_m = engine.registry.get_membership(realm.id, "elite_vault")
        pioneer_m = engine.registry.get_membership(realm.id, "pioneer_vault")
        standard_m = engine.registry.get_membership(realm.id, "standard_vault")
        
        # Supreme (2.5x) > Elite (1.5x) > Pioneer (0.3x) > Standard (0.1x)
        assert supreme_m.epochs_accumulated > elite_m.epochs_accumulated
        assert elite_m.epochs_accumulated > pioneer_m.epochs_accumulated
        assert pioneer_m.epochs_accumulated > standard_m.epochs_accumulated
    
    def test_eidolon_conversion_rate(self, engine_with_members):
        """Test EIDOLON conversion uses correct rate"""
        engine, realm = engine_with_members
        
        # Manually set epochs for testing
        membership = engine.registry.get_membership(realm.id, "elite_vault")
        membership.epochs_accumulated = 100.0
        membership.epochs_vested = 100.0
        engine.registry.update_membership(membership)
        
        result = engine.claim_eidolon(realm.id, "elite_vault")
        
        # elite tier multiplier = 1.5
        expected = 100.0 * EPOCH_TO_EIDOLON_BASE_RATE * TIER_EPOCH_MULTIPLIERS["elite"]
        assert result["eidolon_amount"] == pytest.approx(expected, rel=0.01)


class TestDecay:
    """Tests for realm decay mechanics"""
    
    @pytest.fixture
    def temp_data_dir(self):
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def engine_with_realm(self, temp_data_dir):
        registry = RealmRegistry(data_dir=temp_data_dir)
        engine = RealmEngine(registry=registry)
        engine.set_current_epoch(1000)
        
        realm, _, _ = engine.create_realm(
            name="Test Realm",
            description="A test realm",
            creator_vault_id="creator",
            creator_eidolon_balance=1000.0,
        )
        
        # Give the realm some epochs
        realm.total_epochs_earned = 1000.0
        engine.registry.update_realm(realm)
        
        return engine, realm
    
    def test_decay_starts_after_threshold(self, engine_with_realm):
        """Test decay only starts after inactivity threshold"""
        engine, realm = engine_with_realm
        
        # Simulate inactivity just below threshold
        new_epoch = 1000 + INACTIVITY_DECAY_START_EPOCHS - 1
        engine.set_current_epoch(new_epoch)
        ticks = engine.process_tick(new_epoch)
        
        realm = engine.registry.get_realm(realm.id)
        assert realm.decay_accumulated == 0.0
        # Status can be active or dormant depending on implementation
    
    def test_decay_applies_after_threshold(self, engine_with_realm):
        """Test decay applies after inactivity threshold"""
        engine, realm = engine_with_realm
        
        # Simulate inactivity past threshold
        new_epoch = 1000 + INACTIVITY_DECAY_START_EPOCHS + 10
        engine.set_current_epoch(new_epoch)
        ticks = engine.process_tick(new_epoch)
        
        realm = engine.registry.get_realm(realm.id)
        
        # Should have some decay now
        expected_decay = DECAY_RATE_PER_EPOCH * 1000.0  # Initial epochs
        assert realm.decay_accumulated == pytest.approx(expected_decay, rel=0.1)
        assert realm.total_epochs_earned < 1000.0
    
    def test_activity_resets_decay(self, engine_with_realm):
        """Test that activity resets decay tracking"""
        engine, realm = engine_with_realm
        
        # Simulate some inactivity
        engine.set_current_epoch(1000 + 100)
        engine.process_tick(1000 + 100)
        
        # Add activity at current epoch
        engine.set_current_epoch(1000 + 101)
        engine.record_activity(realm.id, "creator", "message")
        engine.process_tick(1000 + 101)
        
        realm = engine.registry.get_realm(realm.id)
        assert realm.last_activity_epoch == 1000 + 101
        assert realm.status == RealmStatus.ACTIVE.value


class TestGovernance:
    """Tests for governance mechanics"""
    
    @pytest.fixture
    def temp_data_dir(self):
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def engine_with_voters(self, temp_data_dir):
        registry = RealmRegistry(data_dir=temp_data_dir)
        engine = RealmEngine(registry=registry)
        engine.set_current_epoch(1000)
        
        realm, creator_membership, _ = engine.create_realm(
            name="Test Realm",
            description="A test realm",
            creator_vault_id="creator",
            creator_eidolon_balance=1000.0,
        )
        
        # Give creator enough epochs to create proposals
        creator_membership.epochs_accumulated = 200.0
        creator_membership.epochs_vested = 200.0
        engine.registry.update_membership(creator_membership)
        
        # Add voters with vested epochs
        for i in range(3):
            m = engine.join_realm(realm.id, f"voter_{i}")
            m.epochs_accumulated = 50.0
            m.epochs_vested = 50.0
            engine.registry.update_membership(m)
        
        # Set realm total for quorum calculation
        realm.total_epochs_earned = 350.0
        engine.registry.update_realm(realm)
        
        return engine, realm
    
    def test_create_proposal(self, engine_with_voters):
        """Test proposal creation"""
        engine, realm = engine_with_voters
        
        proposal = engine.create_proposal(
            realm_id=realm.id,
            creator_vault_id="creator",
            title="Test Proposal",
            description="This is a test proposal for governance",
        )
        
        assert proposal.title == "Test Proposal"
        assert proposal.status == ProposalStatus.ACTIVE.value
        assert proposal.voting_ends_epoch == engine.get_current_epoch() + 168  # 1 week
    
    def test_create_proposal_insufficient_epochs(self, engine_with_voters):
        """Test proposal creation fails without enough epochs"""
        engine, realm = engine_with_voters
        
        # voter_0 has only 50 epochs, needs 100
        with pytest.raises(ValueError, match="Insufficient vested epochs"):
            engine.create_proposal(
                realm_id=realm.id,
                creator_vault_id="voter_0",
                title="Test",
                description="This should fail",
            )
    
    def test_vote_weight_by_epochs(self, engine_with_voters):
        """Test voting weight is based on vested epochs"""
        engine, realm = engine_with_voters
        
        proposal = engine.create_proposal(
            realm_id=realm.id,
            creator_vault_id="creator",
            title="Test Proposal",
            description="This is a test proposal",
        )
        
        # Creator votes (200 vested epochs)
        vote1 = engine.vote(proposal.id, "creator", "for")
        assert vote1.weight == 200.0
        
        # Voter votes (50 vested epochs)
        vote2 = engine.vote(proposal.id, "voter_0", "against")
        assert vote2.weight == 50.0
        
        # Check proposal tallies
        proposal = engine.registry.get_proposal(proposal.id)
        assert proposal.votes_for_weight == 200.0
        assert proposal.votes_against_weight == 50.0
    
    def test_cannot_vote_twice(self, engine_with_voters):
        """Test that double voting fails"""
        engine, realm = engine_with_voters
        
        proposal = engine.create_proposal(
            realm_id=realm.id,
            creator_vault_id="creator",
            title="Test",
            description="Test proposal",
        )
        
        engine.vote(proposal.id, "voter_0", "for")
        
        with pytest.raises(ValueError, match="Already voted"):
            engine.vote(proposal.id, "voter_0", "against")


class TestCipherHook:
    """Tests for async Cipher activity hook"""
    
    def test_queue_activity(self):
        """Test activity queuing"""
        hook = CipherActivityHook()
        
        success = hook.notify(
            realm_id="realm_1",
            vault_id="vault_1",
            action_type="message",
            epoch=1000,
        )
        
        assert success
        assert hook.get_queue_size() == 1
    
    def test_anti_replay(self):
        """Test duplicate events are rejected"""
        hook = CipherActivityHook()
        
        # First notification succeeds
        success1 = hook.notify(
            realm_id="realm_1",
            vault_id="vault_1",
            action_type="message",
            epoch=1000,
            nonce="unique_nonce_123",
        )
        
        # Same nonce is rejected
        success2 = hook.notify(
            realm_id="realm_1",
            vault_id="vault_1",
            action_type="message",
            epoch=1000,
            nonce="unique_nonce_123",
        )
        
        assert success1
        assert not success2
        assert hook.get_queue_size() == 1
    
    def test_flush_clears_queue(self):
        """Test flush returns and clears events"""
        hook = CipherActivityHook()
        
        hook.notify("realm_1", "vault_1", "message", 1000)
        hook.notify("realm_1", "vault_2", "message", 1000)
        
        events = hook.flush()
        
        assert len(events) == 2
        assert hook.get_queue_size() == 0


class TestIntegrationScenario:
    """End-to-end integration tests"""
    
    @pytest.fixture
    def temp_data_dir(self):
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    def test_full_lifecycle(self, temp_data_dir):
        """Test full realm lifecycle: create, join, earn, claim, leave"""
        registry = RealmRegistry(data_dir=temp_data_dir)
        engine = RealmEngine(registry=registry)
        engine.set_current_epoch(1000)
        
        # 1. Create realm
        realm, _, _ = engine.create_realm(
            name="Integration Test Realm",
            description="Testing full lifecycle",
            creator_vault_id="alice",
            creator_vault_tier="elite",
            creator_eidolon_balance=1000.0,
        )
        
        # 2. Bob joins
        bob_membership = engine.join_realm(realm.id, "bob", "pioneer")
        
        # 3. Simulate activity over multiple epochs
        for epoch in range(1001, 1010):
            engine.set_current_epoch(epoch)
            engine.record_activity(realm.id, "alice", "message")
            engine.record_activity(realm.id, "bob", "message")
            engine.process_tick(epoch)
        
        # 4. Check epochs accumulated
        alice = engine.registry.get_membership(realm.id, "alice")
        bob = engine.registry.get_membership(realm.id, "bob")
        
        assert alice.epochs_accumulated > 0
        assert bob.epochs_accumulated > 0
        # Elite tier should earn more than pioneer
        assert alice.epochs_accumulated > bob.epochs_accumulated
        
        # 5. Fast forward for vesting (6 weeks)
        engine.set_current_epoch(1000 + 1008)  # ~6 weeks
        engine.process_tick(1000 + 1008)
        
        # Update vesting
        alice = engine.registry.get_membership(realm.id, "alice")
        bob = engine.registry.get_membership(realm.id, "bob")
        
        # 6. Claim EIDOLON
        if alice.epochs_vested > alice.eidolon_claimed:
            alice_claim = engine.claim_eidolon(realm.id, "alice")
            assert alice_claim["eidolon_amount"] > 0
        
        # 7. Bob leaves (should retain vested epochs)
        _, vesting = engine.leave_realm(realm.id, "bob")
        assert vesting["vested_ratio"] == 1.0  # Fully vested after 6 weeks
        
        # 8. Check realm stats
        stats = engine.get_realm_stats(realm.id)
        assert stats["member_count"] == 1  # Only Alice remains
        assert stats["total_epochs_earned"] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
