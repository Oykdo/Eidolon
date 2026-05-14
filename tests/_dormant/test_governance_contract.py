import hashlib
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.core.governance import DAOGovernance, StakingSystem


class GovernanceContractTests(unittest.TestCase):
    def test_register_validator_id_matches_existing_sha256_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            dao = DAOGovernance(data_dir=tmp)
            staking = StakingSystem(dao=dao, data_dir=tmp)
            dao.mint_tokens("validator-addr-01", 1_000, "bootstrap")

            validator = staking.register_validator(
                address="validator-addr-01",
                name="Validator One",
                description="Compatibility contract test",
                self_stake=250,
                commission_rate=Decimal("10.0"),
            )

        self.assertIsNotNone(validator)
        expected = hashlib.sha256(b"validator-addr-01").hexdigest()[:32]
        self.assertEqual(validator.validator_id, expected)


if __name__ == "__main__":
    unittest.main()
