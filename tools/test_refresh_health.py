#!/usr/bin/env python3
import unittest
from datetime import datetime, timezone, timedelta
from refresh_health import record, parse_utc

NOW=datetime(2026,11,20,13,00,tzinfo=timezone.utc)
class Tests(unittest.TestCase):
 def test_initial(self):
  r=record({'schema_version':1},NOW,'workflow_dispatch')
  self.assertEqual(r['target_interval_minutes'],30)
  self.assertIsNone(r['previous_success_gap_minutes'])
  self.assertIsNone(r['last_scheduled_success_at'])
 def test_scheduled_updates_both(self):
  r=record({'schema_version':1},NOW,'schedule')
  self.assertEqual(r['last_success_at'],r['last_scheduled_success_at'])
 def test_manual_preserves_last_scheduled(self):
  then=(NOW-timedelta(minutes=90)).isoformat()
  r=record({'schema_version':1,'last_success_at':then,'last_scheduled_success_at':then},NOW,'workflow_dispatch')
  self.assertEqual(r['last_scheduled_success_at'],then)
  self.assertEqual(r['previous_success_gap_minutes'],90)
  self.assertEqual(r['estimated_missed_intervals_since_previous_success'],2)
 def test_half_hour_on_time(self):
  r=record({'last_success_at':(NOW-timedelta(minutes=30)).isoformat()},NOW,'schedule')
  self.assertEqual(r['estimated_missed_intervals_since_previous_success'],0)
 def test_invalid_trigger(self):
  with self.assertRaises(ValueError):record({},NOW,'push')
 def test_bad_timestamp_is_ignored(self):
  self.assertIsNone(parse_utc('nonsense'))
if __name__=='__main__':unittest.main()
