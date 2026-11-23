import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from props_activation_preflight import schedule_decision
from preview_props_digest import target_window


class PreflightTests(unittest.TestCase):
    def test_edt_0930(self):
        self.assertIn("PREVIEW ONLY", schedule_decision(datetime(2026, 7, 15, 13, 30, tzinfo=timezone.utc)))

    def test_est_0930(self):
        self.assertIn("PREVIEW ONLY", schedule_decision(datetime(2026, 11, 23, 14, 30, tzinfo=timezone.utc)))

    def test_no_early_send(self):
        for instant in (datetime(2026, 7, 15, 13, 29, tzinfo=timezone.utc),
                        datetime(2026, 11, 23, 14, 29, tzinfo=timezone.utc)):
            self.assertIn("SKIP", schedule_decision(instant))

    def test_delayed_60_minutes_allowed_as_preview_only(self):
        self.assertIn("PREVIEW ONLY", schedule_decision(datetime(2026, 11, 23, 15, 30, tzinfo=timezone.utc)))

    def test_delayed_beyond_window_skips(self):
        self.assertIn("SKIP", schedule_decision(datetime(2026, 11, 23, 16, 1, tzinfo=timezone.utc)))

    def test_duplicate_simulation(self):
        now = datetime(2026, 11, 23, 14, 30, tzinfo=timezone.utc)
        self.assertIn("SKIP", schedule_decision(now, already_claimed=True))

    def test_target_previous_eastern_day(self):
        day, _, _ = target_window(datetime(2026, 11, 23, 14, 30, tzinfo=timezone.utc))
        self.assertEqual(day, "2026-11-22")


if __name__ == "__main__":
    unittest.main()
