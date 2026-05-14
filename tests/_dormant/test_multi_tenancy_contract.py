import sys
import tempfile
import unittest
import hashlib
import hmac
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.core.multi_tenancy import AuditAction, ImmutableAuditLogger, Role, TenantIsolationManager


class MultiTenancyContractTests(unittest.TestCase):
    def test_org_key_derivation_is_stable(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager = TenantIsolationManager(b"\x88" * 32, data_dir=tmp)
            key1 = manager._derive_org_key("org-alpha")
            key2 = manager._derive_org_key("org-alpha")
            self.assertEqual(key1, key2)
            self.assertEqual(len(key1), 32)

    def test_tenant_encrypt_decrypt_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager = TenantIsolationManager(b"\x99" * 32, data_dir=tmp)
            encrypted = manager._encrypt_data("org-alpha", b"tenant-payload")
            self.assertGreater(len(encrypted), 12)
            self.assertEqual(
                manager._decrypt_data("org-alpha", encrypted),
                b"tenant-payload",
            )

    def test_create_and_load_organization_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager = TenantIsolationManager(b"\xaa" * 32, data_dir=tmp)
            org = manager.create_organization("Alpha Org", "owner-1")
            loaded = manager.load_organization(org.org_id)
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.org_id, org.org_id)
            self.assertEqual(loaded.name, "Alpha Org")

            member = manager.get_member(org.org_id, "owner-1")
            self.assertIsNotNone(member)
            self.assertEqual(member.role, Role.OWNER)

    def test_audit_signature_matches_existing_hmac_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            tenant_manager = TenantIsolationManager(b"\xbb" * 32, data_dir=tmp)
            logger = ImmutableAuditLogger(tenant_manager, b"\xcc" * 32)
            signature = logger._sign_log("ab" * 32)

        expected = hmac.new(
            b"\xcc" * 32,
            ("ab" * 32).encode(),
            hashlib.sha256,
        ).hexdigest()
        self.assertEqual(signature, expected)

    def test_audit_chain_round_trip_remains_valid(self):
        with tempfile.TemporaryDirectory() as tmp:
            tenant_manager = TenantIsolationManager(b"\xdd" * 32, data_dir=tmp)
            logger = ImmutableAuditLogger(tenant_manager, b"\xee" * 32)
            logger.log(
                org_id="org-alpha",
                user_id="user-1",
                action=AuditAction.ORG_CREATE,
                resource_type="org",
                resource_id="org-alpha",
                details={"name": "Alpha Org"},
            )
            logger.log(
                org_id="org-alpha",
                user_id="user-1",
                action=AuditAction.VAULT_CREATE,
                resource_type="vault",
                resource_id="vault-1",
                details={"name": "Primary"},
            )

            self.assertTrue(logger.verify_chain("org-alpha"))


if __name__ == "__main__":
    unittest.main()
