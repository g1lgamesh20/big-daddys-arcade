#!/usr/bin/env python3
"""Backstop decision tests; no network, medal changes or real dispatch."""
import unittest
from datetime import datetime,timezone,timedelta
from refresh_backstop import should_dispatch

NOW=datetime(2026,11,20,16,0,tzinfo=timezone.utc)
def health(minutes):
    return {'schema_version':1,'last_success_at':(NOW-timedelta(minutes=minutes)).isoformat()}

class RefreshBackstopTests(unittest.TestCase):
    def test_fresh_30min_stays_idle(self):
        self.assertEqual(should_dispatch(health(30),NOW),(False,'fresh'))
    def test_42min_boundary_stays_idle(self):
        self.assertEqual(should_dispatch(health(42),NOW),(False,'fresh'))
    def test_43min_stale_dispatches(self):
        self.assertEqual(should_dispatch(health(43),NOW),(True,'stale'))
    def test_four_hour_gap_dispatches(self):
        self.assertEqual(should_dispatch(health(289),NOW),(True,'stale'))
    def test_missing_heartbeat_dispatches(self):
        self.assertEqual(should_dispatch(None,NOW),(True,'missing_or_invalid_heartbeat'))
    def test_corrupt_stamp_dispatches(self):
        self.assertEqual(should_dispatch({'schema_version':1,'last_success_at':'bad'},NOW),
            (True,'missing_or_invalid_timestamp'))
    def test_future_stamp_is_not_blindly_trusted(self):
        self.assertEqual(should_dispatch(health(-20),NOW),(True,'untrusted_future_heartbeat'))
    def test_utc_z_supported(self):
        a=health(40);a['last_success_at']=a['last_success_at'].replace('+00:00','Z')
        self.assertEqual(should_dispatch(a,NOW),(False,'fresh'))
    def test_reject_naive_now(self):
        with self.assertRaisesRegex(ValueError,'timezone-aware'):
            should_dispatch(health(30),datetime(2026,11,20,16))
    def test_invalid_threshold(self):
        with self.assertRaisesRegex(ValueError,'positive'):
            should_dispatch(health(30),NOW,0)
if __name__=='__main__':unittest.main()
