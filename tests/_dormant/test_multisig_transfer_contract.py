import hashlib
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.core.multisig_transfer import (
    MultiSigTransferManager,
    MultiSigTransferProposal,
    Signer,
    TransferStatus,
    MULTISIG_VERSION,
)


class _FakePrivateKey:
    def sign(self, message: bytes) -> bytes:
        return b"\xAA" * 64


class _FakeSigningKeys:
    def __init__(self):
        self.private_key = _FakePrivateKey()


class MultiSigTransferContractTests(unittest.TestCase):
    def test_approval_message_hash_matches_existing_sha256_contract(self):
        manager = object.__new__(MultiSigTransferManager)
        manager.signing_keys = _FakeSigningKeys()
        manager.get_fingerprint = lambda: "fingerprint-approver-01"
        manager._save_proposal = lambda proposal: None

        proposal = MultiSigTransferProposal(
            proposal_id="proposal-001",
            version=MULTISIG_VERSION,
            threshold=2,
            signers=[
                Signer(fingerprint="fingerprint-approver-01", pubkey="11" * 32, role="owner"),
                Signer(fingerprint="fingerprint-approver-02", pubkey="22" * 32, role="guardian"),
            ],
            avatar_id="avatar-123",
            from_vault_fingerprint="vault-from",
            to_vault_fingerprint="vault-to",
            to_vault_pubkey="33" * 32,
            timelock_hours=24,
            status=TransferStatus.PENDING.value,
            created_at="2026-04-03T12:00:00+00:00",
            expires_at="2026-04-10T12:00:00+00:00",
            approvals=[],
        )

        manager.approve_proposal(proposal)

        approval = proposal.approvals[0]
        expected_payload = {
            "proposal_id": proposal.proposal_id,
            "avatar_id": proposal.avatar_id,
            "to_vault": proposal.to_vault_fingerprint,
            "approver": "fingerprint-approver-01",
            "approved_at": approval.signed_at,
        }
        expected = hashlib.sha256(json.dumps(expected_payload, sort_keys=True).encode()).hexdigest()
        self.assertEqual(approval.message_hash, expected)


if __name__ == "__main__":
    unittest.main()
