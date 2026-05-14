import hashlib
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.core.rare_objects_certification import Certificate
from src.core.rare_objects_models import CertificationTier


class RareObjectsCertificationContractTests(unittest.TestCase):
    def test_certificate_verification_hash_matches_existing_sha256_contract(self):
        issued_at = datetime(2026, 4, 3, 12, 0, 0).isoformat()
        valid_until = (datetime(2026, 4, 3, 12, 0, 0) + timedelta(days=365)).isoformat()

        certificate = Certificate(
            certificate_id="CERT-2026-0001",
            object_id="OBJ-OMEGA-0001",
            fingerprint_hash="fp1234567890abcdef1234567890abcdef",
            certification_tier=CertificationTier.ADVANCED,
            issued_at=issued_at,
            valid_until=valid_until,
            object_name="Omega Speedmaster",
            object_category="horlogerie",
            creator_maker="Omega",
            verification_score=97.5,
            rarity_score=88,
        )

        expected_seed = f"{certificate.certificate_id}|{certificate.object_id}|{certificate.fingerprint_hash}|{certificate.issued_at}"
        expected = hashlib.sha256(expected_seed.encode()).hexdigest()
        self.assertEqual(certificate.verification_hash, expected)


if __name__ == "__main__":
    unittest.main()
