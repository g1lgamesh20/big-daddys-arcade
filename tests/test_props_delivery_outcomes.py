import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from props_delivery_outcomes import after_reservation, record_result


class OutcomeTests(unittest.TestCase):
    def test_reserved_never_automatically_retries(self):
        self.assertFalse(after_reservation("reserved").can_attempt_send)

    def test_terminal_states_never_retry(self):
        for state in ("sent", "unknown"):
            self.assertFalse(after_reservation(state).can_attempt_send)
            with self.assertRaises(ValueError):
                record_result(state, "confirmed", "provider-id")

    def test_confirmed_requires_notification_id(self):
        with self.assertRaises(ValueError):
            record_result("reserved", "confirmed", None)
        with self.assertRaises(ValueError):
            record_result("reserved", "confirmed", " ")
        self.assertEqual(record_result("reserved", "confirmed", "provider-id"), "sent")

    def test_ambiguous_results_block_retries(self):
        for outcome in ("timeout", "network_error", "ambiguous_response", "provider_error"):
            self.assertEqual(record_result("reserved", outcome), "unknown")

    def test_unrecognized_outcome_fails_closed(self):
        with self.assertRaises(ValueError):
            record_result("reserved", "retry")
        with self.assertRaises(ValueError):
            after_reservation("available")


if __name__ == "__main__":
    unittest.main()
