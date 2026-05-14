import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.core.compliance import (
    ComplianceAuditLog,
    ComplianceEventType,
    GDPRComplianceManager,
    GDPRLegalBasis,
    ProcessingPurpose,
    SOC2AuditManager,
    SOC2Principle,
)


class ComplianceContractTests(unittest.TestCase):
    def test_record_consent_hash_matches_existing_sha256_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager = GDPRComplianceManager(data_dir=tmp)
            consent = manager.record_consent(
                user_id="user-001",
                purposes=[ProcessingPurpose.AUTHENTICATION],
                legal_basis=GDPRLegalBasis.CONSENT,
                consent_text="I consent to authentication processing.",
                ip_address="127.0.0.1",
                user_agent="contract-test",
            )

        expected = hashlib.sha256(b"I consent to authentication processing.").hexdigest()
        self.assertEqual(consent.consent_text_hash, expected)

    def test_soc2_log_hash_matches_existing_sha256_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager = SOC2AuditManager(signing_key=b"signing-key", data_dir=tmp)
            log = ComplianceAuditLog(
                log_id="log-001",
                timestamp="2026-04-03T12:00:00",
                event_type=ComplianceEventType.ACCESS_GRANTED,
                user_id="user-001",
                ip_address="127.0.0.1",
                user_agent="contract-test",
                resource_type="vault",
                resource_id="vault-001",
                action="read",
                details={"scope": "metadata", "ok": True},
                principles=[SOC2Principle.SECURITY],
                previous_hash="0" * 64,
                log_hash="",
            )

            digest = manager._compute_hash(log)

        seed = (
            f"{log.timestamp}:{log.event_type.value}:{log.user_id}:"
            f"{log.resource_type}:{log.resource_id}:{log.action}:"
            f"{json.dumps(log.details)}:{log.previous_hash}"
        )
        expected = hashlib.sha256(seed.encode()).hexdigest()
        self.assertEqual(digest, expected)


if __name__ == "__main__":
    unittest.main()
