import json
import tempfile
import unittest
import os
from pathlib import Path

from src.api.server import (
    apply_vault_entropy_purge,
    apply_vault_resonance_maintenance,
    build_vault_dashboard_snapshot,
    build_vault_assets_summary,
    build_vault_economy_snapshot,
    build_vault_economic_operations_snapshot,
    build_vault_incubation_snapshot,
    unlock_vault_holographic_depth,
)
from src.api.client import VaultAPIClient
from src.holo.genesis_incubator import IncubationManager
from src.identity.vault_identity import VaultIdentityManager


class APIVaultEconomyTests(unittest.TestCase):
    def setUp(self):
        self.original_test_mode = os.environ.get("EIDOLON_TEST_MODE")
        os.environ["EIDOLON_TEST_MODE"] = "1"

    def tearDown(self):
        if self.original_test_mode is None:
            os.environ.pop("EIDOLON_TEST_MODE", None)
        else:
            os.environ["EIDOLON_TEST_MODE"] = self.original_test_mode

    def test_build_vault_economy_snapshot_exposes_eidolon_and_depth_progression(self):
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
                vault_name="ApiVault",
                psnx_path=str(psnx_path),
                blend_path=str(blend_path),
                vault_key=b"api-vault-key",
            )
            self.assertTrue(registered)

            credited, message = identity_mgr.credit_eidolon(identity.vault_id, 20.0, reason="seed")
            self.assertTrue(credited, message)
            unlocked, message, _ = identity_mgr.apply_holographic_depth_unlock(identity.vault_id)
            self.assertTrue(unlocked, message)

            egg_payload = {
                "eggId": "GENESIS_001",
                "egg_id": "GENESIS_001",
                "name": "Genesis of Echoes",
                "rank": "GENESIS",
                "theme": "harmonic",
                "baseRewardRatio": 2.0,
                "incubationCycles": 20,
            }
            with open(eggs_dir / "GENESIS_001.json", "w", encoding="utf-8") as f:
                json.dump(egg_payload, f, indent=2)

            with open(genesis_dir / "distribution.json", "w", encoding="utf-8") as f:
                json.dump({"genesisAssignments": {"1": ["GENESIS_001"]}}, f, indent=2)

            incubator = IncubationManager(
                vault_id=identity.vault_number,
                genesis_eggs_dir=str(genesis_dir),
                distribution_dir=str(distribution_dir),
                incubation_dir=str(incubation_dir),
                identity_storage_dir=str(identities_dir),
            )
            success, message = incubator.start_incubation("GENESIS_001")
            self.assertTrue(success, message)
            for _ in range(10):
                result = incubator.update_incubation("GENESIS_001")
                self.assertTrue(result["success"])

            from src.api import server as api_server

            original_monitor = api_server.UnifiedAssetMonitor
            try:
                api_server.UnifiedAssetMonitor = lambda: original_monitor(
                    identity_storage_dir=str(identities_dir),
                    genesis_eggs_dir=str(genesis_dir),
                    distribution_dir=str(distribution_dir),
                    incubation_dir=str(incubation_dir),
                )
                snapshot = build_vault_economy_snapshot(identity.vault_number)
            finally:
                api_server.UnifiedAssetMonitor = original_monitor

            self.assertEqual(snapshot["schema_version"], "v1")
            self.assertEqual(snapshot["vault_number"], 1)
            self.assertEqual(snapshot["vault_name"], "ApiVault")
            self.assertEqual(snapshot["holographic_depth_level"], 1)
            self.assertEqual(snapshot["holographic_depth_stage_name"], "Inner Ring")
            self.assertEqual(snapshot["holographic_depth_next_stage_name"], "Depth Axes")
            self.assertAlmostEqual(snapshot["next_holographic_depth_cost"], 27.5, places=4)
            self.assertAlmostEqual(snapshot["pending_eidolon_rewards"], 0.45, places=4)
            self.assertEqual(snapshot["incubating_eggs"], 1)

    def test_build_vault_assets_summary_groups_core_domains(self):
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
                vault_name="AssetsApiVault",
                psnx_path=str(psnx_path),
                blend_path=str(blend_path),
                vault_key=b"assets-api-vault-key",
            )
            self.assertTrue(registered)

            credited, message = identity_mgr.credit_eidolon(identity.vault_id, 20.0, reason="seed")
            self.assertTrue(credited, message)

            egg_payload = {
                "eggId": "GENESIS_003",
                "egg_id": "GENESIS_003",
                "name": "Genesis of Tides",
                "rank": "GENESIS",
                "theme": "aqua",
                "baseRewardRatio": 2.0,
                "incubationCycles": 20,
            }
            with open(eggs_dir / "GENESIS_003.json", "w", encoding="utf-8") as f:
                json.dump(egg_payload, f, indent=2)

            with open(genesis_dir / "distribution.json", "w", encoding="utf-8") as f:
                json.dump({"genesisAssignments": {"1": ["GENESIS_003"]}}, f, indent=2)

            incubator = IncubationManager(
                vault_id=identity.vault_number,
                genesis_eggs_dir=str(genesis_dir),
                distribution_dir=str(distribution_dir),
                incubation_dir=str(incubation_dir),
                identity_storage_dir=str(identities_dir),
            )
            success, message = incubator.start_incubation("GENESIS_003")
            self.assertTrue(success, message)

            from src.api import server as api_server

            original_monitor = api_server.UnifiedAssetMonitor
            try:
                api_server.UnifiedAssetMonitor = lambda: original_monitor(
                    identity_storage_dir=str(identities_dir),
                    genesis_eggs_dir=str(genesis_dir),
                    distribution_dir=str(distribution_dir),
                    incubation_dir=str(incubation_dir),
                )
                snapshot = build_vault_assets_summary(identity.vault_number)
            finally:
                api_server.UnifiedAssetMonitor = original_monitor

            self.assertEqual(snapshot["schema_version"], "v1")
            self.assertEqual(snapshot["vault_number"], 1)
            self.assertEqual(snapshot["overview"]["vault_name"], "AssetsApiVault")
            self.assertEqual(snapshot["overview"]["pioneer_tier"], identity.pioneer_tier)
            self.assertEqual(snapshot["economy"]["eidolon_balance"], 20.0)
            self.assertEqual(snapshot["eggs"]["total"], 1)
            self.assertEqual(snapshot["eggs"]["incubating"], 1)
            self.assertFalse(snapshot["avatar"]["has_avatar"])
            self.assertFalse(snapshot["genesis"]["has_genesis_block"])
            self.assertGreater(snapshot["psnx"]["total"], 0)
            self.assertGreaterEqual(snapshot["psnx"]["locked"], 0)

    def test_build_vault_incubation_snapshot_exposes_egg_level_progress(self):
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
                vault_name="IncubationApiVault",
                psnx_path=str(psnx_path),
                blend_path=str(blend_path),
                vault_key=b"incubation-api-vault-key",
            )
            self.assertTrue(registered)

            egg_payload = {
                "eggId": "GENESIS_002",
                "egg_id": "GENESIS_002",
                "name": "Genesis of Ember",
                "rank": "GENESIS",
                "theme": "void",
                "baseRewardRatio": 2.0,
                "incubationCycles": 20,
            }
            with open(eggs_dir / "GENESIS_002.json", "w", encoding="utf-8") as f:
                json.dump(egg_payload, f, indent=2)

            with open(genesis_dir / "distribution.json", "w", encoding="utf-8") as f:
                json.dump({"genesisAssignments": {"1": ["GENESIS_002"]}}, f, indent=2)

            incubator = IncubationManager(
                vault_id=identity.vault_number,
                genesis_eggs_dir=str(genesis_dir),
                distribution_dir=str(distribution_dir),
                incubation_dir=str(incubation_dir),
                identity_storage_dir=str(identities_dir),
            )
            success, message = incubator.start_incubation("GENESIS_002")
            self.assertTrue(success, message)
            for _ in range(10):
                result = incubator.update_incubation("GENESIS_002")
                self.assertTrue(result["success"])

            from src.api import server as api_server

            original_incubator = api_server.IncubationManager
            try:
                api_server.IncubationManager = lambda vault_id: original_incubator(
                    vault_id=vault_id,
                    genesis_eggs_dir=str(genesis_dir),
                    distribution_dir=str(distribution_dir),
                    incubation_dir=str(incubation_dir),
                    identity_storage_dir=str(identities_dir),
                )
                snapshot = build_vault_incubation_snapshot(identity.vault_number)
            finally:
                api_server.IncubationManager = original_incubator

            self.assertEqual(snapshot["schema_version"], "v1")
            self.assertEqual(snapshot["vault_number"], 1)
            self.assertEqual(snapshot["summary"]["incubating"], 1)
            self.assertEqual(len(snapshot["eggs"]), 1)
            egg_entry = snapshot["eggs"][0]
            self.assertEqual(egg_entry["egg_id"], "GENESIS_002")
            self.assertEqual(egg_entry["current_stage"], "PRIMORDIAL")
            self.assertAlmostEqual(egg_entry["paid_units"], 0.5, places=4)
            self.assertAlmostEqual(egg_entry["remaining_units"], 0.5, places=4)
            self.assertEqual(egg_entry["next_payout_in_cycles"], 10)

    def test_unlock_vault_holographic_depth_returns_refreshed_economy_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            identities_dir = tmp_path / "identities"
            identities_dir.mkdir()

            psnx_path = tmp_path / "vault.psnx"
            blend_path = tmp_path / "vault.blend_data"
            psnx_path.write_bytes(b"psnx")
            blend_path.write_bytes(b"blend")

            identity_mgr = VaultIdentityManager(storage_dir=str(identities_dir))
            registered, identity, _ = identity_mgr.register_vault(
                vault_name="UnlockApiVault",
                psnx_path=str(psnx_path),
                blend_path=str(blend_path),
                vault_key=b"unlock-api-vault-key",
            )
            self.assertTrue(registered)

            credited, message = identity_mgr.credit_eidolon(identity.vault_id, 100.0, reason="seed")
            self.assertTrue(credited, message)

            from src.api import server as api_server

            original_identity_mgr = api_server.VaultIdentityManager
            original_monitor = api_server.UnifiedAssetMonitor
            try:
                api_server.VaultIdentityManager = lambda: original_identity_mgr(storage_dir=str(identities_dir))
                api_server.UnifiedAssetMonitor = lambda: original_monitor(
                    identity_storage_dir=str(identities_dir),
                )
                result = unlock_vault_holographic_depth(identity.vault_number)
            finally:
                api_server.VaultIdentityManager = original_identity_mgr
                api_server.UnifiedAssetMonitor = original_monitor

            self.assertEqual(result["schema_version"], "v1")
            self.assertEqual(result["vault_number"], 1)
            self.assertEqual(result["message"], "Holographic depth unlocked")
            self.assertEqual(result["unlock_result"]["target_level"], 1)
            self.assertAlmostEqual(result["unlock_result"]["cost"], 15.0, places=4)
            self.assertEqual(result["economy"]["holographic_depth_level"], 1)
            self.assertEqual(result["economy"]["holographic_depth_stage_name"], "Inner Ring")
            self.assertAlmostEqual(result["economy"]["next_holographic_depth_cost"], 27.5, places=4)

    def test_api_client_unlock_holographic_depth_uses_expected_endpoint(self):
        client = VaultAPIClient.__new__(VaultAPIClient)
        client._request = lambda method, endpoint, json=None, auth=True: {
            "method": method,
            "endpoint": endpoint,
            "json": json,
            "auth": auth,
        }

        response = client.unlock_holographic_depth(vault_number=7)

        self.assertEqual(response["method"], "POST")
        self.assertEqual(response["endpoint"], "/vault/holographic-depth/unlock?vault_number=7")
        self.assertIsNone(response["json"])
        self.assertTrue(response["auth"])

    def test_api_client_get_vault_assets_summary_uses_expected_endpoint(self):
        client = VaultAPIClient.__new__(VaultAPIClient)
        client._request = lambda method, endpoint, json=None, auth=True: {
            "method": method,
            "endpoint": endpoint,
            "json": json,
            "auth": auth,
        }

        response = client.get_vault_assets_summary(vault_number=4)

        self.assertEqual(response["method"], "GET")
        self.assertEqual(response["endpoint"], "/vault/assets/summary?vault_number=4")
        self.assertIsNone(response["json"])
        self.assertTrue(response["auth"])

    def test_api_client_get_vault_dashboard_uses_expected_endpoint(self):
        client = VaultAPIClient.__new__(VaultAPIClient)
        client._request = lambda method, endpoint, json=None, auth=True: {
            "method": method,
            "endpoint": endpoint,
            "json": json,
            "auth": auth,
        }

        response = client.get_vault_dashboard(vault_number=9)

        self.assertEqual(response["method"], "GET")
        self.assertEqual(response["endpoint"], "/vault/dashboard?vault_number=9")
        self.assertIsNone(response["json"])
        self.assertTrue(response["auth"])

    def test_build_vault_dashboard_snapshot_aggregates_all_dashboard_domains(self):
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
                vault_name="DashboardApiVault",
                psnx_path=str(psnx_path),
                blend_path=str(blend_path),
                vault_key=b"dashboard-api-vault-key",
            )
            self.assertTrue(registered)

            credited, message = identity_mgr.credit_eidolon(identity.vault_id, 30.0, reason="seed")
            self.assertTrue(credited, message)

            egg_payload = {
                "eggId": "GENESIS_004",
                "egg_id": "GENESIS_004",
                "name": "Genesis of Signals",
                "rank": "GENESIS",
                "theme": "signal",
                "baseRewardRatio": 2.0,
                "incubationCycles": 20,
            }
            with open(eggs_dir / "GENESIS_004.json", "w", encoding="utf-8") as f:
                json.dump(egg_payload, f, indent=2)

            with open(genesis_dir / "distribution.json", "w", encoding="utf-8") as f:
                json.dump({"genesisAssignments": {"1": ["GENESIS_004"]}}, f, indent=2)

            from src.api import server as api_server

            original_identity_mgr = api_server.VaultIdentityManager
            original_monitor = api_server.UnifiedAssetMonitor
            original_incubator = api_server.IncubationManager
            try:
                api_server.VaultIdentityManager = lambda: original_identity_mgr(storage_dir=str(identities_dir))
                api_server.UnifiedAssetMonitor = lambda: original_monitor(
                    identity_storage_dir=str(identities_dir),
                    genesis_eggs_dir=str(genesis_dir),
                    distribution_dir=str(distribution_dir),
                    incubation_dir=str(incubation_dir),
                )
                api_server.IncubationManager = lambda vault_id: original_incubator(
                    vault_id=vault_id,
                    genesis_eggs_dir=str(genesis_dir),
                    distribution_dir=str(distribution_dir),
                    incubation_dir=str(incubation_dir),
                    identity_storage_dir=str(identities_dir),
                )
                snapshot = build_vault_dashboard_snapshot(identity.vault_number)
            finally:
                api_server.VaultIdentityManager = original_identity_mgr
                api_server.UnifiedAssetMonitor = original_monitor
                api_server.IncubationManager = original_incubator

            self.assertEqual(snapshot["schema_version"], "v1")
            self.assertEqual(snapshot["vault_number"], 1)
            self.assertIn("assets", snapshot)
            self.assertIn("economy", snapshot)
            self.assertIn("incubation", snapshot)
            self.assertIn("operations", snapshot)
            self.assertEqual(snapshot["assets"]["overview"]["vault_name"], "DashboardApiVault")
            self.assertEqual(snapshot["economy"]["vault_name"], "DashboardApiVault")
            self.assertEqual(snapshot["operations"]["vault_number"], 1)

    def test_apply_vault_resonance_maintenance_returns_refreshed_economy_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            identities_dir = tmp_path / "identities"
            identities_dir.mkdir()

            psnx_path = tmp_path / "vault.psnx"
            blend_path = tmp_path / "vault.blend_data"
            psnx_path.write_bytes(b"psnx")
            blend_path.write_bytes(b"blend")

            identity_mgr = VaultIdentityManager(storage_dir=str(identities_dir))
            registered, identity, _ = identity_mgr.register_vault(
                vault_name="ResonanceApiVault",
                psnx_path=str(psnx_path),
                blend_path=str(blend_path),
                vault_key=b"resonance-api-vault-key",
            )
            self.assertTrue(registered)

            updated, message = identity_mgr.update_resonance(identity.vault_id, 40.0)
            self.assertTrue(updated, message)
            credited, message = identity_mgr.credit_eidolon(identity.vault_id, 25.0, reason="seed")
            self.assertTrue(credited, message)

            from src.api import server as api_server

            original_identity_mgr = api_server.VaultIdentityManager
            original_monitor = api_server.UnifiedAssetMonitor
            try:
                api_server.VaultIdentityManager = lambda: original_identity_mgr(storage_dir=str(identities_dir))
                api_server.UnifiedAssetMonitor = lambda: original_monitor(
                    identity_storage_dir=str(identities_dir),
                )
                result = apply_vault_resonance_maintenance(identity.vault_number, requested_gain=10.0)
            finally:
                api_server.VaultIdentityManager = original_identity_mgr
                api_server.UnifiedAssetMonitor = original_monitor

            self.assertEqual(result["schema_version"], "v1")
            self.assertEqual(result["vault_number"], 1)
            self.assertEqual(result["message"], "Resonance maintenance applied")
            self.assertAlmostEqual(result["maintenance_result"]["applied_gain"], 10.0, places=4)
            self.assertAlmostEqual(result["maintenance_result"]["cost"], 8.0, places=4)
            self.assertAlmostEqual(result["economy"]["resonance_score"], 100.0, places=4)
            self.assertAlmostEqual(result["economy"]["eidolon_balance"], 17.0, places=4)

    def test_apply_vault_entropy_purge_returns_refreshed_economy_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            identities_dir = tmp_path / "identities"
            identities_dir.mkdir()

            psnx_path = tmp_path / "vault.psnx"
            blend_path = tmp_path / "vault.blend_data"
            psnx_path.write_bytes(b"psnx")
            blend_path.write_bytes(b"blend")

            identity_mgr = VaultIdentityManager(storage_dir=str(identities_dir))
            registered, identity, _ = identity_mgr.register_vault(
                vault_name="EntropyApiVault",
                psnx_path=str(psnx_path),
                blend_path=str(blend_path),
                vault_key=b"entropy-api-vault-key",
            )
            self.assertTrue(registered)

            updated, message = identity_mgr.update_operational_entropy(identity.vault_id, 20.0)
            self.assertTrue(updated, message)
            credited, message = identity_mgr.credit_eidolon(identity.vault_id, 25.0, reason="seed")
            self.assertTrue(credited, message)

            from src.api import server as api_server

            original_identity_mgr = api_server.VaultIdentityManager
            original_monitor = api_server.UnifiedAssetMonitor
            try:
                api_server.VaultIdentityManager = lambda: original_identity_mgr(storage_dir=str(identities_dir))
                api_server.UnifiedAssetMonitor = lambda: original_monitor(
                    identity_storage_dir=str(identities_dir),
                )
                result = apply_vault_entropy_purge(identity.vault_number, requested_reduction=5.0)
            finally:
                api_server.VaultIdentityManager = original_identity_mgr
                api_server.UnifiedAssetMonitor = original_monitor

            self.assertEqual(result["schema_version"], "v1")
            self.assertEqual(result["vault_number"], 1)
            self.assertEqual(result["message"], "Operational entropy purged")
            self.assertAlmostEqual(result["purge_result"]["applied_reduction"], 5.0, places=4)
            self.assertAlmostEqual(result["purge_result"]["cost"], 3.6, places=4)
            self.assertAlmostEqual(result["economy"]["operational_entropy"], 15.0, places=4)
            self.assertAlmostEqual(result["economy"]["eidolon_balance"], 21.4, places=4)

    def test_api_client_resonance_and_entropy_actions_use_expected_endpoints(self):
        client = VaultAPIClient.__new__(VaultAPIClient)
        client._request = lambda method, endpoint, json=None, auth=True: {
            "method": method,
            "endpoint": endpoint,
            "json": json,
            "auth": auth,
        }

        resonance_response = client.maintain_resonance(12.5, vault_number=3)
        entropy_response = client.purge_entropy(4.0, vault_number=5)

        self.assertEqual(resonance_response["method"], "POST")
        self.assertEqual(resonance_response["endpoint"], "/vault/resonance/maintain?vault_number=3")
        self.assertEqual(resonance_response["json"], {"requested_gain": 12.5})
        self.assertTrue(resonance_response["auth"])

        self.assertEqual(entropy_response["method"], "POST")
        self.assertEqual(entropy_response["endpoint"], "/vault/entropy/purge?vault_number=5")
        self.assertEqual(entropy_response["json"], {"requested_reduction": 4.0})
        self.assertTrue(entropy_response["auth"])


if __name__ == "__main__":
    unittest.main()
