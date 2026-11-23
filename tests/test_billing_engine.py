import unittest

from billing_engine import (
    DEMO_RATE_CARD,
    correct_mismatch,
    generate_billing_attempts,
    price_for_volume,
    release_invoice,
    unresolved_attempts,
    verify_billing_attempts,
    void_duplicate,
    volume_cm3,
)
from warehouse_simulator import create_warehouse_run, rescan_missing_parcels


class BillingEngineTests(unittest.TestCase):
    def setUp(self):
        self.run = create_warehouse_run("TEST-RUN", "Operations User", seed=20261123)

    def test_volume_bands(self):
        self.assertEqual(volume_cm3(20, 10, 10), 2000)
        self.assertEqual(price_for_volume(4999)[0], "Small")
        self.assertEqual(price_for_volume(5000)[0], "Medium")
        self.assertEqual(price_for_volume(14999)[0], "Medium")
        self.assertEqual(price_for_volume(15000)[0], "Large")

    def test_seeded_simulation_counts(self):
        self.assertEqual(len(self.run["parcels"]), 100)
        self.assertEqual(len(self.run["scans"]), 95)
        self.assertEqual(generate_billing_attempts(self.run), 102)
        counts = verify_billing_attempts(self.run)
        self.assertEqual(counts, {
            "matched": 87,
            "mismatch": 8,
            "missing_scan": 5,
            "duplicate": 2,
        })

    def test_release_is_blocked_until_exceptions_are_resolved(self):
        generate_billing_attempts(self.run)
        verify_billing_attempts(self.run)
        with self.assertRaises(ValueError):
            release_invoice(self.run, "Finance Approver")

    def test_rescan_then_resolve_and_release(self):
        generate_billing_attempts(self.run)
        verify_billing_attempts(self.run)
        self.assertEqual(rescan_missing_parcels(self.run), 5)
        verify_billing_attempts(self.run)
        self.assertEqual(sum(s["status"] == "missing_scan" for s in self.run["billing_attempts"]), 0)

        for attempt in list(self.run["billing_attempts"]):
            if attempt["status"] == "mismatch":
                correct_mismatch(self.run, attempt["event_id"], "Finance Reviewer")
            elif attempt["status"] == "duplicate":
                void_duplicate(self.run, attempt["event_id"], "Finance Reviewer")

        self.assertEqual(len(unresolved_attempts(self.run)), 0)
        release_invoice(self.run, "Finance Approver")
        self.assertTrue(self.run["released"])

    def test_exception_reviewer_cannot_be_final_approver(self):
        generate_billing_attempts(self.run)
        verify_billing_attempts(self.run)
        rescan_missing_parcels(self.run)
        verify_billing_attempts(self.run)
        for attempt in list(self.run["billing_attempts"]):
            if attempt["status"] == "mismatch":
                correct_mismatch(self.run, attempt["event_id"], "Finance Reviewer")
            elif attempt["status"] == "duplicate":
                void_duplicate(self.run, attempt["event_id"], "Finance Reviewer")
        with self.assertRaises(ValueError):
            release_invoice(self.run, "Finance Reviewer")

    def test_creator_cannot_release_own_run(self):
        generate_billing_attempts(self.run)
        verify_billing_attempts(self.run)
        rescan_missing_parcels(self.run)
        verify_billing_attempts(self.run)
        for attempt in list(self.run["billing_attempts"]):
            if attempt["status"] == "mismatch":
                correct_mismatch(self.run, attempt["event_id"], "Finance Reviewer")
            elif attempt["status"] == "duplicate":
                void_duplicate(self.run, attempt["event_id"], "Finance Reviewer")
        with self.assertRaises(ValueError):
            release_invoice(self.run, "Operations User")


if __name__ == "__main__":
    unittest.main()
