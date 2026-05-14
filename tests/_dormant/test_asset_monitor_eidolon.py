import json
import tempfile
import unittest
import os
from pathlib import Path

from src.holo.asset_monitor import UnifiedAssetMonitor
from src.holo.genesis_incubator import IncubationManager
from src.identity.vault_identity import VaultIdentityManager


class AssetMonitorEidolonTests(unittest.TestCase):
    def setUp(self):
        self.original_test_mode = os.environ.get("EIDOLON_TEST_MODE")
        os.environ["EIDOLON_TEST_MODE"] = "1"

    def tearDown(self):
        if self.original_test_mode is None:
            os.environ.pop("EIDOLON_TEST_MODE", None)
        else:
            os.environ["EIDOLON_TEST_MODE"] = self.original_test_mode

    def test_asset_monitor_includes_eidolon_and_incubation_projection(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            genesis_dir = tmp_path / "genesis_eggs"
            eggs_dir = genesis_dir / "eggs"
            eggs_dir.mkdir(parents=True)
            incubation_dir = tmp_path / "vault_incubation"
            distribution_dir = tmp_path / "genesis_distribution"
            identities_dir = tmp_path / "identities"
            incubation_dir.mkdir()
            distribution_dir.mkdir()
            identities_dir.mkdir()

            psnx_path = tmp_path / "vault.psnx"
            blend_path = tmp_path / "vault.blend_data"
            psnx_path.write_bytes(b"psnx")
            blend_path.write_bytes(b"blend")

            identity_mgr = VaultIdentityManager(storage_dir=str(identities_dir))
            registered, identity, _ = identity_mgr.register_vault(
                vault_name="AssetVault",
                psnx_path=str(psnx_path),
                blend_path=str(blend_path),
                vault_key=b"vault-key-test",
            )
            self.assertTrue(registered)

            egg_payload = {
                "eggId": "GENESIS_000",
                "egg_id": "GENESIS_000",
                "name": "Genesis of Void",
                "rank": "GENESIS",
                "theme": "void",
                "baseRewardRatio": 2.0,
                "incubationCycles": 20,
            }
            with open(eggs_dir / "GENESIS_000.json", "w", encoding="utf-8") as f:
                json.dump(egg_payload, f, indent=2)

            with open(genesis_dir / "distribution.json", "w", encoding="utf-8") as f:
                json.dump({"genesisAssignments": {"1": ["GENESIS_000"]}}, f, indent=2)

            manager = IncubationManager(
                vault_id=identity.vault_number,
                genesis_eggs_dir=str(genesis_dir),
                distribution_dir=str(distribution_dir),
                incubation_dir=str(incubation_dir),
                identity_storage_dir=str(identities_dir),
            )
            success, message = manager.start_incubation("GENESIS_000")
            self.assertTrue(success, message)

            for _ in range(10):
                result = manager.update_incubation("GENESIS_000")
                self.assertTrue(result["success"])

            monitor = UnifiedAssetMonitor(
                identity_storage_dir=str(identities_dir),
                genesis_eggs_dir=str(genesis_dir),
                distribution_dir=str(distribution_dir),
                incubation_dir=str(incubation_dir),
            )
            summary = monitor.get_vault_summary(identity.vault_number)

            self.assertEqual(summary.eggs_genesis, 1)
            self.assertEqual(summary.eggs_total, 1)
            self.assertEqual(summary.incubating_eggs, 1)
            self.assertEqual(summary.hatched_eggs, 0)
            self.assertEqual(summary.dormant_eggs, 0)
            self.assertEqual(summary.incubation_slots_available, 4)
            self.assertAlmostEqual(summary.pending_eidolon_rewards, 0.5, places=4)
            self.assertAlmostEqual(summary.eidolon_balance, 0.5, places=4)
            self.assertEqual(summary.holographic_depth_level, 0)
            self.assertEqual(summary.holographic_depth_stage_name, "Origin Key")
            self.assertEqual(summary.holographic_depth_next_stage_name, "Inner Ring")
            self.assertAlmostEqual(summary.next_holographic_depth_cost, 15.0, places=4)
            self.assertAlmostEqual(summary.incubation_average_progress, 50.0, places=3)

            display = monitor.display_vault_summary(identity.vault_number)
            self.assertIn("Pending Rewards:   0.5000 EIDOLON", display)
            self.assertIn("Holo Depth:        0 (Origin Key)", display)
            self.assertIn("Next Depth Unlock: Inner Ring", display)
            self.assertIn("Next Depth Cost:   15.0000 EIDOLON", display)
            self.assertIn("INCUBATION STATUS", display)
            self.assertIn("Incubating:        1", display)


if __name__ == "__main__":
    unittest.main()
