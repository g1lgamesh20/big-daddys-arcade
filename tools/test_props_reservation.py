#!/usr/bin/env python3
"""Offline reservation contract checks. Never connects to Supabase or OneSignal."""
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Lock


class FakeLedger:
    """Model the database's unique-date insert / ON CONFLICT DO NOTHING."""
    def __init__(self):
        self.claims = set()
        self.lock = Lock()

    def reserve(self, day):
        with self.lock:
            if day in self.claims:
                return False
            self.claims.add(day)
            return True


class ReservationTests(unittest.TestCase):
    def test_one_claim_only_under_contention(self):
        ledger = FakeLedger()
        with ThreadPoolExecutor(max_workers=12) as pool:
            results = list(pool.map(ledger.reserve, ["2026-11-22"] * 100))
        self.assertEqual(sum(results), 1)

    def test_different_days_independent(self):
        ledger = FakeLedger()
        self.assertTrue(ledger.reserve("2026-11-22"))
        self.assertTrue(ledger.reserve("2026-11-23"))
        self.assertFalse(ledger.reserve("2026-11-22"))

    def test_no_retries_after_claim(self):
        ledger = FakeLedger()
        self.assertTrue(ledger.reserve("2026-11-22"))
        for _ in range(10):
            self.assertFalse(ledger.reserve("2026-11-22"))


if __name__ == "__main__":
    unittest.main()
