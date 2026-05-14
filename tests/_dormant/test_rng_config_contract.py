import hashlib
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.core.rng_config import ConfigurableRNG


class RNGConfigContractTests(unittest.TestCase):
    def test_string_seed_matches_existing_sha256_contract(self):
        with patch("src.core.rng_config.random.seed") as mocked_seed:
            ConfigurableRNG(seed="rng-contract-seed")

        expected = int(hashlib.sha256(b"rng-contract-seed").hexdigest()[:8], 16)
        mocked_seed.assert_called_once_with(expected)


if __name__ == "__main__":
    unittest.main()
