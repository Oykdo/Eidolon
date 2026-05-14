import hashlib
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.core.hardware_attestation import (
    ATTESTATION_VERSION,
    HardwareFingerprint,
    HardwareInfoCollector,
)


class HardwareAttestationContractTests(unittest.TestCase):
    def test_hardware_fingerprint_hash_matches_existing_sha256_contract(self):
        fingerprint = HardwareFingerprint(
            fingerprint_id="fp-001",
            version=ATTESTATION_VERSION,
            machine_id="machine-001",
            platform="win32",
            platform_version="10.0.0",
            hostname_hash="deadbeefcafebabe",
            cpu_brand="CPU",
            cpu_cores=8,
            cpu_arch="x86_64",
            ram_total_gb=32,
        )

        stable = {
            "machine_id": fingerprint.machine_id,
            "platform": fingerprint.platform,
            "cpu_brand": fingerprint.cpu_brand,
            "cpu_cores": fingerprint.cpu_cores,
            "cpu_arch": fingerprint.cpu_arch,
            "ram_total_gb": fingerprint.ram_total_gb,
        }
        expected = hashlib.sha256(json.dumps(stable, sort_keys=True).encode()).hexdigest()
        self.assertEqual(fingerprint.compute_hash(), expected)

    def test_collect_fingerprint_hostname_hash_matches_existing_sha256_prefix(self):
        with patch("src.core.hardware_attestation.HardwareInfoCollector.get_machine_id", return_value="machine-001"), \
             patch("src.core.hardware_attestation.HardwareInfoCollector.get_cpu_info", return_value=("CPU", 8, "x86_64")), \
             patch("src.core.hardware_attestation.HardwareInfoCollector.get_ram_total", return_value=32), \
             patch("src.core.hardware_attestation.HardwareInfoCollector.check_tpm_available", return_value=(False, None)), \
             patch("src.core.hardware_attestation.HardwareInfoCollector.check_secure_enclave", return_value=False), \
             patch("src.core.hardware_attestation.platform.node", return_value="eidolon-host"), \
             patch("src.core.hardware_attestation.platform.version", return_value="10.0.0"):
            fingerprint = HardwareInfoCollector.collect_fingerprint()

        expected = hashlib.sha256(b"eidolon-host").hexdigest()[:16]
        self.assertEqual(fingerprint.hostname_hash, expected)


if __name__ == "__main__":
    unittest.main()
