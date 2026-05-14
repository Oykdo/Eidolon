import tempfile
import unittest
from pathlib import Path

from src.holo.runes_vesting import ClaimStatus, RunesVestingManager


class PSNXClaimLedgerTests(unittest.TestCase):
    def test_create_claim_request_records_unlock_refs_without_settling(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager = RunesVestingManager(storage_path=Path(tmp))
            schedule = manager.create_vesting_schedule("vault-123", 7, btc_address="bc1ptest")

            created, claim, message = manager.create_claim_request("vault-123")
            self.assertTrue(created, message)
            self.assertIsNotNone(claim)
            self.assertEqual(claim.status, ClaimStatus.PENDING_OFFCHAIN.value)
            self.assertEqual(claim.destination_btc_address, "bc1ptest")
            self.assertEqual(claim.amount_requested, schedule.immediate_amount)
            self.assertEqual(claim.unlock_refs, [0])
            self.assertEqual(schedule.total_claimed, 0)

            reloaded = RunesVestingManager(storage_path=Path(tmp))
            saved = reloaded.get_claim(claim.claim_id)
            self.assertIsNotNone(saved)
            self.assertEqual(saved.status, ClaimStatus.PENDING_OFFCHAIN.value)

    def test_record_offchain_claim_settles_pending_request_and_marks_unlocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager = RunesVestingManager(storage_path=Path(tmp))
            schedule = manager.create_vesting_schedule("vault-123", 7)

            created, claim, _ = manager.create_claim_request("vault-123")
            self.assertTrue(created)

            settled, amount, message = manager.record_offchain_claim(claim.claim_id, txid="offchain-001")
            self.assertTrue(settled, message)
            self.assertEqual(amount, schedule.immediate_amount)

            refreshed = manager.get_schedule("vault-123")
            self.assertEqual(refreshed.total_claimed, schedule.immediate_amount)
            self.assertEqual(refreshed.unlocks[0].claim_id, claim.claim_id)
            self.assertEqual(refreshed.unlocks[0].claim_txid, "offchain-001")

            saved_claim = manager.get_claim(claim.claim_id)
            self.assertEqual(saved_claim.status, ClaimStatus.RECORDED_OFFCHAIN.value)
            self.assertEqual(saved_claim.amount_confirmed, schedule.immediate_amount)
            self.assertEqual(saved_claim.txid, "offchain-001")

    def test_legacy_claim_available_now_routes_through_claim_ledger(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager = RunesVestingManager(storage_path=Path(tmp))
            schedule = manager.create_vesting_schedule("vault-legacy", 50)

            success, amount, message = manager.claim_available("vault-legacy")
            self.assertTrue(success, message)
            self.assertEqual(amount, schedule.immediate_amount)

            claims = manager.list_claims("vault-legacy")
            self.assertEqual(len(claims), 1)
            self.assertEqual(claims[0].status, ClaimStatus.RECORDED_OFFCHAIN.value)
            self.assertEqual(claims[0].amount_confirmed, schedule.immediate_amount)

            summary = manager.get_claim_summary("vault-legacy")
            self.assertEqual(summary["claim_count"], 1)
            self.assertEqual(summary["recorded_offchain_amount"], schedule.immediate_amount)


if __name__ == "__main__":
    unittest.main()
