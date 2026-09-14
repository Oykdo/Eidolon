"""
Connect escrow primitives — seal/open and EIDOLON holds.

What an application running a postal escrow on Eidolon (CardSwap) relies
on: an approved app can seal a record it cannot open by itself, and can
lock EIDOLON on a vault that only it can release or forfeit. Nothing here
needs a user JWT; the Connect secret and the app registration are the
whole authentication.
"""

import base64
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.api import server as api_server  # noqa: E402
from src.api.connect_registry import ConnectAppRegistry  # noqa: E402
from src.identity.vault_identity import VaultIdentity, VaultIdentityManager  # noqa: E402

try:
    from fastapi.testclient import TestClient

    TESTCLIENT_AVAILABLE = True
except ImportError:
    TESTCLIENT_AVAILABLE = False

SECRET = {"X-Eidolon-Connect-Secret": "connect-secret-for-tests"}


def _vault(vault_id: str, number: int, balance: float) -> VaultIdentity:
    return VaultIdentity(
        vault_id=vault_id,
        vault_number=number,
        vault_name=f"Vault {number}",
        psnx_path=f"C:/vaults/{vault_id}.psnx",
        blend_path=f"C:/vaults/{vault_id}.blend",
        psnx_hash="hash_psnx",
        blend_hash="hash_blend",
        vault_key_hash="hash_key",
        eidolon_balance=balance,
    )


@unittest.skipUnless(api_server.FASTAPI_AVAILABLE and TESTCLIENT_AVAILABLE, "FastAPI TestClient unavailable")
class ConnectEscrowContractTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_registry = api_server.connect_app_registry
        self.original_identity_manager = api_server.vault_identity_manager
        self.original_connect_secret = api_server.runtime_config.connect_session_secret
        self.original_allow_local = api_server.runtime_config.allow_local_connect_session

        registry = ConnectAppRegistry(storage_dir=Path(self.temp_dir.name))
        api_server.connect_app_registry = registry
        manager = VaultIdentityManager(storage_dir=Path(self.temp_dir.name) / "vaults")
        manager.vaults["vault-alice"] = _vault("vault-alice", 7, 100.0)
        manager.vaults["vault-bob"] = _vault("vault-bob", 8, 20.0)
        manager._save_registry()
        api_server.vault_identity_manager = manager

        # Everything below authenticates with the secret, never with loopback.
        api_server.runtime_config.connect_session_secret = SECRET["X-Eidolon-Connect-Secret"]
        api_server.runtime_config.allow_local_connect_session = False
        self.http = TestClient(api_server.app)

        self.http.post("/connect/apps/register", json={
            "app_id": "cardswap.web", "app_name": "CardSwap", "scopes": ["auth"],
        })
        registry.approve_app("cardswap.web")
        self.http.post("/connect/apps/register", json={
            "app_id": "pending.app", "app_name": "Pending", "scopes": ["auth"],
        })

    def tearDown(self):
        self.http.close()
        api_server.connect_app_registry = self.original_registry
        api_server.vault_identity_manager = self.original_identity_manager
        api_server.runtime_config.connect_session_secret = self.original_connect_secret
        api_server.runtime_config.allow_local_connect_session = self.original_allow_local
        self.temp_dir.cleanup()

    # --- seal / open ------------------------------------------------------

    def _seal(self, data: bytes, subject="user-1", app_id="cardswap.web", headers=SECRET):
        return self.http.post("/connect/vault/seal", headers=headers, json={
            "app_id": app_id, "subject": subject, "data": base64.b64encode(data).decode(),
        })

    def _open(self, sealed: str, subject="user-1", app_id="cardswap.web"):
        return self.http.post("/connect/vault/open", headers=SECRET, json={
            "app_id": app_id, "subject": subject, "sealed": sealed,
        })

    def test_seal_round_trip_and_fresh_nonce(self):
        first = self._seal(b'{"line1":"12 rue de la Paix"}')
        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(first.json()["key_id"], "connect-seal-v1")
        second = self._seal(b'{"line1":"12 rue de la Paix"}')
        self.assertNotEqual(first.json()["sealed"], second.json()["sealed"])
        self.assertNotIn("Paix", first.json()["sealed"])

        opened = self._open(first.json()["sealed"])
        self.assertEqual(opened.status_code, 200, opened.text)
        self.assertEqual(base64.b64decode(opened.json()["data"]), b'{"line1":"12 rue de la Paix"}')
        self.assertEqual(opened.json()["size"], 29)

    def test_a_blob_is_bound_to_its_app_and_subject(self):
        sealed = self._seal(b"secret").json()["sealed"]
        self.assertEqual(self._open(sealed, subject="user-2").status_code, 400)
        tampered = base64.b64encode(base64.b64decode(sealed)[:-1] + b"\x00").decode()
        self.assertEqual(self._open(tampered).status_code, 400)

    def test_seal_needs_the_secret_and_an_approved_app(self):
        self.assertEqual(self._seal(b"x", headers={}).status_code, 403)
        self.assertEqual(self._seal(b"x", headers={"X-Eidolon-Connect-Secret": "nope"}).status_code, 403)
        self.assertEqual(self._seal(b"x", app_id="pending.app").status_code, 403)
        self.assertEqual(self._seal(b"x", app_id="unknown.app").status_code, 404)

    def test_seal_size_cap(self):
        self.assertEqual(self._seal(b"a" * (16 * 1024 + 1)).status_code, 413)
        self.assertEqual(self._seal(b"a" * (16 * 1024)).status_code, 200)

    def test_the_demo_encrypt_stays_hidden(self):
        self.assertEqual(self.http.post("/vault/encrypt", json={"data": "eA=="}).status_code, 401)

    # --- holds ------------------------------------------------------------

    def _hold(self, vault_id="vault-alice", amount=60.0, reference="exchange-1", app_id="cardswap.web"):
        return self.http.post("/connect/vault/economy/holds", headers=SECRET, json={
            "app_id": app_id, "vault_id": vault_id, "amount": amount, "reference": reference,
        })

    def _economy(self, vault_id):
        return self.http.get(f"/connect/vault/economy/{vault_id}", headers=SECRET).json()

    def test_hold_leaves_the_balance_and_release_returns_it(self):
        res = self._hold()
        self.assertEqual(res.status_code, 201, res.text)
        hold = res.json()["hold"]
        self.assertEqual(hold["status"], "active")
        self.assertEqual(hold["amount"], 60.0)
        economy = self._economy("vault-alice")
        self.assertEqual(economy["eidolon_balance"], 40.0)
        self.assertEqual(economy["eidolon_held"], 60.0)
        self.assertEqual(economy["lifetime_eidolon_spent"], 0.0)  # a hold is not a purchase

        released = self.http.post(f"/connect/vault/economy/holds/{hold['hold_id']}/release",
                                  headers=SECRET, json={"app_id": "cardswap.web"})
        self.assertEqual(released.status_code, 200, released.text)
        self.assertEqual(released.json()["hold"]["status"], "released")
        economy = self._economy("vault-alice")
        self.assertEqual(economy["eidolon_balance"], 100.0)
        self.assertEqual(economy["eidolon_held"], 0.0)

    def test_hold_is_idempotent_on_reference(self):
        first = self._hold().json()["hold"]
        again = self._hold()
        self.assertEqual(again.status_code, 201)
        self.assertEqual(again.json()["hold"]["hold_id"], first["hold_id"])
        self.assertEqual(self._economy("vault-alice")["eidolon_balance"], 40.0)

    def test_insufficient_balance_is_refused(self):
        res = self._hold(vault_id="vault-bob", amount=60.0)
        self.assertEqual(res.status_code, 409)
        self.assertIn("Insufficient", res.json()["detail"])
        self.assertEqual(self._economy("vault-bob")["eidolon_balance"], 20.0)
        self.assertEqual(self._hold(vault_id="vault-nobody").status_code, 404)
        self.assertEqual(self._hold(amount=0).status_code, 400)

    def test_forfeit_moves_the_amount_to_the_counterparty(self):
        hold = self._hold().json()["hold"]
        res = self.http.post(f"/connect/vault/economy/holds/{hold['hold_id']}/forfeit",
                             headers=SECRET, json={"app_id": "cardswap.web", "to_vault_id": "vault-bob"})
        self.assertEqual(res.status_code, 200, res.text)
        self.assertEqual(res.json()["hold"]["status"], "forfeited")
        alice, bob = self._economy("vault-alice"), self._economy("vault-bob")
        self.assertEqual(alice["eidolon_balance"], 40.0)
        self.assertEqual(alice["lifetime_eidolon_spent"], 60.0)
        self.assertEqual(alice["eidolon_held"], 0.0)
        self.assertEqual(bob["eidolon_balance"], 80.0)
        self.assertEqual(bob["lifetime_eidolon_earned"], 60.0)

        trail = api_server.vault_identity_manager.list_economic_operations("vault-bob")
        self.assertEqual(trail[-1]["operation_type"], "hold_forfeit_credit")

    def test_forfeit_without_recipient_burns(self):
        hold = self._hold().json()["hold"]
        res = self.http.post(f"/connect/vault/economy/holds/{hold['hold_id']}/forfeit",
                             headers=SECRET, json={"app_id": "cardswap.web"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(self._economy("vault-alice")["eidolon_balance"], 40.0)
        self.assertEqual(self._economy("vault-bob")["eidolon_balance"], 20.0)

    def test_a_hold_is_resolved_once_and_only_by_its_app(self):
        hold = self._hold().json()["hold"]
        url = f"/connect/vault/economy/holds/{hold['hold_id']}"
        # Another approved app cannot touch it — same answer as unknown.
        self.http.post("/connect/apps/register", json={"app_id": "other.app", "app_name": "O", "scopes": ["auth"]})
        api_server.connect_app_registry.approve_app("other.app")
        self.assertEqual(self.http.post(f"{url}/release", headers=SECRET, json={"app_id": "other.app"}).status_code, 404)
        self.assertEqual(self.http.get(url, headers=SECRET, params={"app_id": "other.app"}).status_code, 404)

        self.assertEqual(self.http.post(f"{url}/release", headers=SECRET, json={"app_id": "cardswap.web"}).status_code, 200)
        again = self.http.post(f"{url}/forfeit", headers=SECRET, json={"app_id": "cardswap.web"})
        self.assertEqual(again.status_code, 409)
        self.assertIn("already released", again.json()["detail"])
        self.assertEqual(self.http.get(url, headers=SECRET, params={"app_id": "cardswap.web"}).json()["hold"]["status"], "released")


if __name__ == "__main__":
    unittest.main()
