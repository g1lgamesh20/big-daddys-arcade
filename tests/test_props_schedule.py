import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from dry_run_props_schedule import eligible_time, already_sent
from preview_props_digest import target_window


class PropsScheduleTests(unittest.TestCase):
    def test_est_gate(self):
        self.assertFalse(eligible_time(datetime(2026, 1, 5, 14, 29, tzinfo=timezone.utc)))
        self.assertTrue(eligible_time(datetime(2026, 1, 5, 14, 30, tzinfo=timezone.utc)))
        self.assertFalse(eligible_time(datetime(2026, 1, 5, 16, 0, tzinfo=timezone.utc)))

    def test_edt_gate(self):
        self.assertFalse(eligible_time(datetime(2026, 7, 5, 13, 29, tzinfo=timezone.utc)))
        self.assertTrue(eligible_time(datetime(2026, 7, 5, 13, 30, tzinfo=timezone.utc)))
        self.assertFalse(eligible_time(datetime(2026, 7, 5, 15, 0, tzinfo=timezone.utc)))

    def test_eastern_day_boundaries(self):
        self.assertEqual(target_window(datetime(2026, 11, 23, 15, tzinfo=timezone.utc))[0], "2026-11-22")
        self.assertEqual(target_window(datetime(2026, 7, 5, 14, tzinfo=timezone.utc))[0], "2026-07-04")

    def test_no_state_not_sent(self):
        with TemporaryDirectory() as temp:
            self.assertFalse(already_sent("2026-11-22", Path(temp) / "missing.json"))


if __name__ == "__main__":
    unittest.main()
