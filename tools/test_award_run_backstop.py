#!/usr/bin/env python3
import unittest
from datetime import datetime, timedelta, timezone
from award_run_backstop import need_recovery

NOW=datetime(2026,11,21,3,tzinfo=timezone.utc)
def success(age):
    return {"status":"completed","conclusion":"success","createdAt":(NOW-timedelta(minutes=age)).isoformat()}

class Tests(unittest.TestCase):
    def test_recent_success_does_not_dispatch(self):
        self.assertEqual(need_recovery([success(60)],NOW),(False,"recent_success"))
    def test_threshold_is_inclusive(self):
        self.assertEqual(need_recovery([success(75)],NOW),(False,"recent_success"))
    def test_missing_success_recovers(self):
        self.assertEqual(need_recovery([],NOW),(True,"no_recent_success"))
    def test_old_success_recovers(self):
        self.assertEqual(need_recovery([success(130)],NOW),(True,"stale"))
    def test_failure_does_not_count_as_success(self):
        self.assertEqual(need_recovery([{"status":"completed","conclusion":"failure","createdAt":NOW.isoformat()}],NOW),
            (True,"no_recent_success"))
    def test_any_queued_work_prevents_double_dispatch(self):
        r=[success(130),{"status":"queued","conclusion":None,"createdAt":NOW.isoformat()}]
        self.assertEqual(need_recovery(r,NOW),(False,"award_run_already_pending"))
    def test_last_success_not_first_run(self):
        self.assertEqual(need_recovery([success(200),success(10)],NOW),(False,"recent_success"))
    def test_future_success_is_untrusted(self):
        self.assertEqual(need_recovery([success(-30)],NOW),(True,"future_success_timestamp"))
    def test_invalid_run_list_fail_closed(self):
        with self.assertRaises(ValueError):need_recovery({},NOW)

if __name__=="__main__":
    unittest.main()
