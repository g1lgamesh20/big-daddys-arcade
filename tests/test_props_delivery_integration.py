import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from props_delivery_integration import plan_delivery, simulate_outcome


DAY = "2026-11-22"
ENTRY = [("DON", "VJG", "Ikari Warriors", "joystick")]


class IntegrationTests(unittest.TestCase):
    def test_available_with_props_only_prepares_payload(self):
        decision, payload = plan_delivery(DAY, ENTRY, 0, [])
        self.assertIn("NOT AUTHORIZED", decision)
        self.assertEqual(payload["included_segments"], ["All"])

    def test_no_props_skips_without_reserving(self):
        decision, payload = plan_delivery(DAY, [], 0, [])
        self.assertIn("SKIP", decision)
        self.assertIsNone(payload)

    def test_conflicts_fail_closed(self):
        decision, payload = plan_delivery(DAY, ENTRY, 1, [])
        self.assertIn("BLOCKED", decision)
        self.assertIsNone(payload)

    def test_existing_reservation_and_terminal_states_block(self):
        for status in ("reserved", "sent", "unknown"):
            rows = [{"status": status, "idempotency_key":
                     "big-daddys-arcade:give-props:" + DAY}]
            decision, payload = plan_delivery(DAY, ENTRY, 0, rows)
            self.assertIn("BLOCKED", decision)
            self.assertIsNone(payload)

    def test_simulated_outcomes_never_retry(self):
        self.assertEqual(simulate_outcome("confirmed"), "sent")
        for scenario in ("timeout", "network_error", "ambiguous_response", "provider_error"):
            self.assertEqual(simulate_outcome(scenario), "unknown")


if __name__ == "__main__":
    unittest.main()
