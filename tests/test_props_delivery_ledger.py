import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from verify_props_delivery_ledger import classify


class LedgerTests(unittest.TestCase):
    day = "2026-11-22"
    key = "big-daddys-arcade:give-props:2026-11-22"

    def row(self, status):
        return {"idempotency_key": self.key, "status": status}

    def test_available(self):
        self.assertIn("AVAILABLE", classify([], self.day))

    def test_sent(self):
        self.assertIn("ALREADY SENT", classify([self.row("sent")], self.day))

    def test_reserved_fail_closed(self):
        self.assertIn("do not send", classify([self.row("reserved")], self.day))

    def test_unknown_fail_closed(self):
        self.assertIn("do not send", classify([self.row("unknown")], self.day))

    def test_bad_key_fails(self):
        with self.assertRaises(RuntimeError):
            classify([{"status": "sent", "idempotency_key": "bad"}], self.day)

    def test_bad_status_fails(self):
        with self.assertRaises(RuntimeError):
            classify([self.row("other")], self.day)

    def test_duplicate_fails(self):
        with self.assertRaises(RuntimeError):
            classify([self.row("sent"), self.row("sent")], self.day)


if __name__ == "__main__":
    unittest.main()
