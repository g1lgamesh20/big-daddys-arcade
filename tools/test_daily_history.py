#!/usr/bin/env python3
"""Daily historical selections must survive calendar rollover and delayed score imports."""
import unittest
from datetime import datetime,timezone
from challenge_award_candidates import collect

HISTORY={('daily','2026-11-16','50354'):'World Class Bowling',
         ('daily','2026-11-17','86751'):'Wolverine'}
class DailyHistoryTests(unittest.TestCase):
 def test_late_discovered_daily_score(self):
  rows=[{'game':'50354','name':'DON','score':1000,'id':123,
         'date':'2026-11-16T18:00:00'}]
  r=collect(rows,HISTORY,datetime(2026,11,20,tzinfo=timezone.utc))
  self.assertEqual(len(r['candidates']),1)
  self.assertEqual(r['candidates'][0]['kind'],'daily')
  self.assertFalse(r['candidates'][0]['awarded'])
 def test_no_double_credit_for_same_player(self):
  rows=[{'game':'50354','name':'DON','score':1000,'id':123,'date':'2026-11-16T18:00:00'},
        {'game':'50354','name':'DON','score':2000,'id':124,'date':'2026-11-16T19:00:00'}]
  r=collect(rows,HISTORY,datetime(2026,11,20,tzinfo=timezone.utc))
  self.assertEqual(len(r['candidates']),1)
  self.assertEqual(r['candidates'][0]['best_score'],2000)
 def test_unfeatured_game_not_counted(self):
  rows=[{'game':'50010','name':'DON','score':1000,'id':123,'date':'2026-11-16T18:00:00'}]
  r=collect(rows,HISTORY,datetime(2026,11,20,tzinfo=timezone.utc))
  self.assertEqual(len(r['candidates']),0)
if __name__=='__main__':unittest.main()
