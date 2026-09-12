"""Code court (XXXX-XXXX) sur le serveur Connect autonome.

``deploy/connect-api/eidolon_connect_server.py`` est volontairement
independant du reste du code Eidolon : on le charge depuis son chemin, avec
le minimum d'environnement qu'il exige a l'import (repertoire de donnees,
signatures HMAC desactivees, secret admin pour approuver l'app de test).
"""

import importlib.util
import os
import re
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path

try:
    from fastapi.testclient import TestClient

    TESTCLIENT_AVAILABLE = True
except ImportError:  # pragma: no cover
    TESTCLIENT_AVAILABLE = False

REPO_ROOT = Path(__file__).resolve().parents[1]
SERVER_PATH = REPO_ROOT / "deploy" / "connect-api" / "eidolon_connect_server.py"
ADMIN_SECRET = "standalone-admin-secret-for-tests"
USER_CODE_RE = re.compile(r"^[ABCDEFGHJKMNPQRSTVWXYZ0-9]{4}-[ABCDEFGHJKMNPQRSTVWXYZ0-9]{4}$")


def _load_server_module(data_dir: str):
    # Everything below is read at import time by the module.
    os.environ["EIDOLON_CONNECT_DATA_DIR"] = data_dir
    os.environ["EIDOLON_CONNECT_ENFORCE_SIG"] = "0"
    os.environ["EIDOLON_CONNECT_ADMIN_SECRET"] = ADMIN_SECRET
    spec = importlib.util.spec_from_file_location("eidolon_connect_server_under_test", SERVER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    # dataclasses resolves string annotations (PEP 563) through sys.modules,
    # so the module must be registered before it executes.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@unittest.skipUnless(TESTCLIENT_AVAILABLE and SERVER_PATH.exists(), "FastAPI TestClient or standalone server unavailable")
class StandaloneConnectUserCodeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data_dir = tempfile.mkdtemp(prefix="eidolon-connect-standalone-")
        cls.saved_env = {
            name: os.environ.get(name)
            for name in ("EIDOLON_CONNECT_DATA_DIR", "EIDOLON_CONNECT_ENFORCE_SIG", "EIDOLON_CONNECT_ADMIN_SECRET")
        }
        cls.server = _load_server_module(cls.data_dir)

    @classmethod
    def tearDownClass(cls):
        for name, value in cls.saved_env.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        shutil.rmtree(cls.data_dir, ignore_errors=True)

    def setUp(self):
        server = self.server
        server.user_codes.clear()
        server.code_resolve_limiter.reset()
        server.nonces._entries.clear()
        for path in (server.APPS_FILE, server.SESSIONS_FILE):
            if path.exists():
                path.unlink()
        self.http = TestClient(server.app)
        self.http.post(
            "/connect/apps/register",
            json={"app_id": "cipher.desktop", "app_name": "Cipher Desktop", "scopes": ["auth"]},
        )
        approved = self.http.post(
            "/connect/apps/cipher.desktop/approve",
            json={"granted_scopes": ["auth"]},
            headers={"X-Admin-Secret": ADMIN_SECRET},
        )
        self.assertEqual(approved.status_code, 200, approved.text)

    def tearDown(self):
        self.http.close()

    # -- helpers ---------------------------------------------------------

    def _create_session(self) -> dict:
        response = self.http.post(
            "/connect/sessions",
            json={
                "app_id": "cipher.desktop",
                "vault_id": "0123456789abcdef0123456789abcdef",
                "vault_number": 7,
                "vault_name": "Vault Seven",
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["data"]

    def _resolve(self, code: str, **kwargs):
        return self.http.post("/connect/code/resolve", json={"user_code": code}, **kwargs)

    # -- sessions ----------------------------------------------------------

    def test_session_create_returns_user_code_without_persisting_it(self):
        data = self._create_session()
        self.assertRegex(data["user_code"], USER_CODE_RE)
        self.assertEqual(data["user_code_expires_at"], data["expires_at"])
        # The code lives in memory only: the on-disk session record must not carry it.
        stored = self.server._load_json(self.server.SESSIONS_FILE)[data["session_id"]]
        self.assertNotIn("user_code", stored)

    def test_resolve_session_code_happy_path_is_non_consuming(self):
        data = self._create_session()
        for _ in range(2):
            response = self._resolve(data["user_code"])
            self.assertEqual(response.status_code, 200, response.text)
            payload = response.json()["data"]
            self.assertEqual(payload["kind"], "session")
            self.assertEqual(payload["session_id"], data["session_id"])
            self.assertIsNone(payload["challenge_id"])
            self.assertEqual(payload["expires_at"], data["expires_at"])

        exchanged = self.http.post(
            "/connect/sessions/exchange",
            json={"app_id": "cipher.desktop", "session_id": data["session_id"]},
        )
        self.assertEqual(exchanged.status_code, 200, exchanged.text)

    def test_resolve_normalises_case_separators_and_o_for_zero(self):
        data = self._create_session()
        raw = data["user_code"].replace("-", "")
        lenient = raw.lower().replace("0", "o").replace("1", "i")
        typed = f" {lenient[:4]} - {lenient[4:]} "
        response = self._resolve(typed)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["data"]["session_id"], data["session_id"])

    def test_resolve_unknown_code_is_a_generic_404(self):
        self._create_session()
        response = self._resolve("ZZZZ-9999")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "unknown or expired code")

    def test_resolve_after_exchange_is_404(self):
        data = self._create_session()
        self.http.post(
            "/connect/sessions/exchange",
            json={"app_id": "cipher.desktop", "session_id": data["session_id"]},
        )
        self.assertEqual(self._resolve(data["user_code"]).status_code, 404)

    def test_resolve_expired_code_is_404(self):
        data = self._create_session()
        raw = data["user_code"].replace("-", "")
        # Expire the index entry: GC on access must drop it.
        self.server.user_codes._entries[raw].expires_at = time.time() - 1
        self.assertEqual(self._resolve(data["user_code"]).status_code, 404)

        # Expire the session itself while the index entry is still fresh: the
        # resolver checks the underlying object and drops the dangling code.
        data = self._create_session()
        sessions = self.server._load_json(self.server.SESSIONS_FILE)
        sessions[data["session_id"]]["expires_at"] = time.time() - 1
        self.server._save_json(self.server.SESSIONS_FILE, sessions)
        self.assertEqual(self._resolve(data["user_code"]).status_code, 404)
        self.assertNotIn(data["user_code"].replace("-", ""), self.server.user_codes._entries)

    def test_resolve_is_rate_limited_per_client_ip(self):
        for _ in range(self.server.CODE_RESOLVE_MAX_PER_MINUTE):
            self.assertEqual(self._resolve("AAAA-AAAA").status_code, 404)
        self.assertEqual(self._resolve("AAAA-AAAA").status_code, 429)
        # Another client (first hop of X-Forwarded-For, trusted from loopback) is unaffected.
        other = self._resolve("AAAA-AAAA", headers={"X-Forwarded-For": "203.0.113.9"})
        self.assertEqual(other.status_code, 404)

    # -- challenges --------------------------------------------------------

    def test_challenge_returns_user_code_and_resolves_until_consumed(self):
        response = self.http.post(
            "/connect/challenge",
            json={"app_id": "cipher.desktop", "origin": "https://example.test"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["data"]
        self.assertRegex(data["user_code"], USER_CODE_RE)
        self.assertEqual(data["user_code_expires_at"], data["expires_at"])

        resolved = self._resolve(data["user_code"])
        self.assertEqual(resolved.status_code, 200, resolved.text)
        payload = resolved.json()["data"]
        self.assertEqual(payload["kind"], "local_proof")
        self.assertEqual(payload["challenge_id"], data["challenge_id"])
        self.assertIsNone(payload["session_id"])

        # Consuming the challenge (as /connect/verify does) invalidates the code.
        self.assertTrue(self.server.nonces.consume(data["challenge_id"], user_id="u", vault_age_eons=None))
        self.server.user_codes.invalidate(challenge_id=data["challenge_id"])
        self.assertEqual(self._resolve(data["user_code"]).status_code, 404)


if __name__ == "__main__":
    unittest.main()
