import hashlib
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.core.physical_fingerprint import (
    PhysicalFingerprintBuilder,
    VisualCapture,
    WatchIdentifiers,
    hash_image_bytes,
    hash_image_file,
)


class PhysicalFingerprintContractTests(unittest.TestCase):
    def test_get_identity_hash_matches_existing_sha256_contract(self):
        identifiers = WatchIdentifiers(
            serial_number="PP5711-001234",
            case_number="CASE-42",
            caliber_reference="324 S C",
            brand="Patek Philippe",
            model="Nautilus 5711",
            reference_number="5711/1A-010",
            year_of_production=2020,
            movement_type="automatic",
        )
        seed = "PP5711-001234:CASE-42:324 S C:Patek Philippe:Nautilus 5711"
        expected = hashlib.sha256(seed.encode()).hexdigest()
        self.assertEqual(identifiers.get_identity_hash(), expected)

    def test_hash_image_bytes_matches_existing_sha256_contract(self):
        payload = bytes.fromhex("89504e470d0a1a0a00112233445566778899aabbccddeeff")
        expected = hashlib.sha256(payload).hexdigest()
        self.assertEqual(hash_image_bytes(payload), expected)

    def test_hash_image_file_matches_existing_sha256_contract(self):
        payload = bytes.fromhex("ffd8ffe000104a46494600010100000100010000")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.jpg"
            path.write_bytes(payload)

            expected = hashlib.sha256(payload).hexdigest()
            self.assertEqual(hash_image_file(str(path)), expected)

    def test_simulated_dial_hash_matches_existing_sha256_contract(self):
        builder = PhysicalFingerprintBuilder()
        builder.set_identifiers(
            serial_number="PP5711-2024-00042",
            case_number="4892761",
            caliber_reference="26-330 S C",
            brand="Patek Philippe",
            model="Nautilus",
            reference_number="5711/1A-010",
            year_of_production=2024,
            movement_type="automatic",
            complications=["date", "sweep_seconds"],
        )
        builder.set_physical_measurements(
            weight_grams=135.5,
            diameter_mm=40.0,
            thickness_mm=8.3,
            water_resistance_atm=12,
            power_reserve_hours=45,
        )
        builder.set_capture_metadata(
            location="Geneva, Switzerland",
            operator="Expert Horloger",
            notes="Exemplaire neuf, sortie manufacture",
        )

        expected = hashlib.sha256(b"simulated_dial_microscopy_data").hexdigest()
        builder._dial_capture = VisualCapture(
            image_hash=hash_image_bytes(b"simulated_dial_microscopy_data"),
            image_path=None,
            capture_type="microscopy",
            magnification=100,
            resolution="1920x1080",
            capture_device="Andonstar AD208",
            capture_date="2026-04-03T12:00:00+00:00",
            notes="Capture du guilloche central",
        )

        fingerprint = builder.build()
        self.assertEqual(fingerprint.dial_capture.image_hash, expected)

    def test_builder_object_id_matches_existing_sha256_contract(self):
        builder = PhysicalFingerprintBuilder()
        builder.set_identifiers(
            serial_number="PP5711-2024-00042",
            case_number="4892761",
            caliber_reference="26-330 S C",
            brand="Patek Philippe",
            model="Nautilus",
            reference_number="5711/1A-010",
            year_of_production=2024,
            movement_type="automatic",
            complications=["date", "sweep_seconds"],
        )
        builder.set_physical_measurements(
            weight_grams=135.5,
            diameter_mm=40.0,
            thickness_mm=8.3,
            water_resistance_atm=12,
            power_reserve_hours=45,
        )
        builder.set_capture_metadata(
            location="Geneva, Switzerland",
            operator="Expert Horloger",
            notes="Exemplaire neuf, sortie manufacture",
        )

        fixed_now = datetime(2026, 4, 3, 12, 0, 0)
        with patch("src.core.physical_fingerprint.datetime") as mocked_datetime:
            mocked_datetime.now.return_value = fixed_now
            builder._dial_capture = VisualCapture(
                image_hash=hash_image_bytes(b"simulated_dial_microscopy_data"),
                image_path=None,
                capture_type="microscopy",
                magnification=100,
                resolution="1920x1080",
                capture_device="Andonstar AD208",
                capture_date="2026-04-03T12:00:00+00:00",
                notes="Capture du guilloche central",
            )
            fingerprint = builder.build()

        expected_seed = "PP5711-2024-00042:2026-04-03T12:00:00"
        expected = hashlib.sha256(expected_seed.encode()).hexdigest()[:16]
        self.assertEqual(fingerprint.object_id, expected)


if __name__ == "__main__":
    unittest.main()
