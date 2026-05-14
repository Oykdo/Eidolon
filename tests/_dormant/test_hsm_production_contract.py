import hashlib
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.core.hsm_production import FIPSLevel, HSMConfig, HSMType, SoftwareHSM


class HSMProductionContractTests(unittest.TestCase):
    def test_software_hsm_serial_matches_existing_sha256_contract(self):
        hsm = SoftwareHSM(HSMConfig(hsm_type=HSMType.SOFTWARE, fips_level=FIPSLevel.LEVEL_3))
        info = hsm.get_info()

        expected = hashlib.sha256(b"software-hsm").hexdigest()[:16]
        self.assertEqual(info["serial"], expected)


if __name__ == "__main__":
    unittest.main()
