#!/usr/bin/env python3
"""Offline Central->Eastern iScored date regression tests; no network calls."""
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

from iscored_timestamp import parse_iscored_time
import thursday_challenge as thursday

NY=ZoneInfo('America/New_York')
class TimeTests(unittest.TestCase):
 def test_naive_central_winter_midnight(self):
  before=parse_iscored_time('2026-11-19 22:59:59')
  after=parse_iscored_time('2026-11-19 23:00:00')
  self.assertEqual(before.isoformat(),'2026-11-19T23:59:59-05:00')
  self.assertEqual(after.isoformat(),'2026-11-20T00:00:00-05:00')
 def test_naive_central_summer_midnight(self):
  before=parse_iscored_time('2026-07-09 22:59:59')
  after=parse_iscored_time('2026-07-09 23:00:00')
  self.assertEqual(before.isoformat(),'2026-07-09T23:59:59-04:00')
  self.assertEqual(after.isoformat(),'2026-07-10T00:00:00-04:00')
 def test_explicit_offset_preserved(self):
  self.assertEqual(parse_iscored_time('2026-11-20T04:00:00Z').isoformat(),'2026-11-19T23:00:00-05:00')
  self.assertEqual(parse_iscored_time('2026-11-19T22:30:00-06:00').isoformat(),'2026-11-19T23:30:00-05:00')
 def test_spring_dst_transition(self):
  self.assertEqual(parse_iscored_time('2026-03-08 03:30:00').isoformat(),'2026-03-08T04:30:00-04:00')
 def test_fall_dst_transition(self):
  self.assertEqual(parse_iscored_time('2026-11-01 03:30:00').isoformat(),'2026-11-01T04:30:00-05:00')
 def test_legacy_formats(self):
  self.assertEqual(parse_iscored_time('11/19/2026 10:59:59 PM').date().isoformat(),'2026-11-19')
  self.assertEqual(parse_iscored_time('11/19/2026 11:00 PM').date().isoformat(),'2026-11-20')
 def test_bad_input_safe(self):
  for value in ('',None,'not a time','2026-99-19'):
   self.assertIsNone(parse_iscored_time(value))
 def test_thursday_boundary_from_realistic_rows(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp)
   state=root/'state.json';output=root/'challenge.json';winners=root/'winners.json'
   state.write_text(json.dumps({'weeks':{'2026-11-19':{'game_id':'73126','game':'After Burner Climax'}}}))
   rows=[
    {'game':'73126','gameName':'After Burner Climax','id':'a','name':'BEFORE','score':100,'date':'2026-11-19 22:59:59'},
    {'game':'73126','gameName':'After Burner Climax','id':'b','name':'AFTER','score':999,'date':'2026-11-19 23:00:00'},
   ]
   with patch.object(thursday,'STATE',state),patch.object(thursday,'OUT',output),patch.object(thursday,'WINNERS',winners):
    result=thursday.build(now=datetime(2026,11,20,14,0,tzinfo=timezone.utc),rows=rows)
   self.assertEqual(result['status'],'final')
   self.assertEqual(result['winner']['player'],'BEFORE')
   self.assertEqual(result['eligible_scores'],1)
 def test_monthly_prelaunch_boundary(self):
  from monthly_benchmark import analyze
  rows=[
    {'game':'test','name':'OLD','score':100,'date':'2026-11-30 22:59:59'},
    {'game':'test','name':'NEW','score':200,'date':'2026-11-30 23:00:00'},
  ]
  result=analyze(rows,'test','2026-12')
  self.assertEqual(result['starting_record_candidate'],100)
  self.assertEqual(result['monthly_player_count'],1)
if __name__=='__main__':unittest.main()
