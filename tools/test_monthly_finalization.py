#!/usr/bin/env python3
"""Offline monthly 9 AM finalized podium, participation, benchmark tests."""
import unittest
from datetime import datetime
from monthly_finalization import finalize
from send_monthly_notification import safe_result
def at(s):return datetime.fromisoformat(s)
def ledger():return {'schema_version':1,'verified_plays':[],'awards':[]}
def final():return {'schema_version':1,'months':{}}
def archive():return {'schema_version':1,'months':{'2026-12':{
 'game_id':'99','game':'Robotron','starting_record':1000,'benchmark':750}}}
def row(player,score,date,id='s'):
 return {'name':player,'game':'99','score':score,'date':date,'id':id}
def run(rows,now='2027-01-02T09:00:00-05:00',published=None,awards=None,existing=None,enabled=True):
 return finalize(rows,published if published is not None else archive(),
   awards if awards is not None else ledger(),
   existing if existing is not None else final(),at(now),enabled)
class Tests(unittest.TestCase):
 def test_859_blocks_no_mutation(self):
  original=ledger()
  l,f,r,changed=run([row('DON',900,'2026-12-31 22:59:59')],now='2027-01-02T08:59:59-05:00',awards=original)
  self.assertFalse(changed);self.assertEqual(l,original);self.assertEqual(f,final())
 def test_midnight_eastern_and_late_approval(self):
  # 22:59:59 Central = 23:59:59 Eastern on Dec 31.
  # 23:00 Central = Jan 1 Eastern and must NOT count.
  rows=[row('DON',900,'2026-12-31 22:59:59','a'),
        row('RDG',9999,'2026-12-31 23:00:00','b')]
  l,f,r,changed=run(rows)
  self.assertTrue(changed);self.assertEqual(r['entrant_count'],1)
  self.assertEqual(f['months']['2026-12']['podium'],[{'player':'DON','score':900,'rank':1}])
  self.assertEqual(f['months']['2026-12']['submission_cutoff_et'],'2027-01-01T00:00:00-05:00')
  self.assertEqual(l['verified_plays'][0]['score_id'],'a')
 def test_ties_113_and_beat_average_strict(self):
  rows=[row('DON',1000,'2026-12-30 12:00:00','a'),
        row('RDG',1000,'2026-12-30 13:00:00','b'),
        row('DAY',750,'2026-12-30 14:00:00','c')]
  l,f,r,_=run(rows)
  self.assertEqual([(p['player'],p['rank']) for p in f['months']['2026-12']['podium']],
                   [('DON',1),('RDG',1),('DAY',3)])
  self.assertEqual({a['player'] for a in l['awards'] if a['type']=='gotm_champion'},{'DON','RDG'})
  self.assertEqual({a['player'] for a in l['awards'] if a['type']=='gotm_beat_average'},{'DON','RDG'})
  self.assertEqual(len(l['verified_plays']),3)
  self.assertIsNotNone(safe_result(f,'2026-12',at('2027-01-02T09:00:00-05:00'),archive()))
 def test_player_mean_separate_from_locked_benchmark(self):
  # Three distinct players, one best score each: mean = 700.
  # DON beats both; RDG beats the mean only; DAY beats neither.
  rows=[row('DON',1000,'2026-12-20 10:00:00','a'),
        row('RDG',800,'2026-12-20 11:00:00','b'),
        row('DAY',300,'2026-12-20 12:00:00','c')]
  l,f,r,_=run(rows)
  self.assertEqual({a['player'] for a in l['awards'] if a['type']=='gotm_beat_average'},{'DON','RDG'})
  self.assertEqual({a['player'] for a in l['awards'] if a['type']=='gotm_beat_player_average'},{'DON','RDG'})
  m=f['months']['2026-12']
  self.assertTrue(m['player_average_eligible'])
  self.assertEqual((m['player_average_score_sum'],m['player_average_score_count']),(2100,3))
 def test_player_mean_requires_three_unique_players(self):
  rows=[row('DON',1000,'2026-12-20 10:00:00','a'),
        row('DON',1100,'2026-12-21 10:00:00','b'),
        row('RDG',200,'2026-12-20 11:00:00','c')]
  l,f,r,_=run(rows)
  self.assertFalse(f['months']['2026-12']['player_average_eligible'])
  self.assertFalse(any(a['type']=='gotm_beat_player_average' for a in l['awards']))
 def test_player_mean_strict_tie_and_fractional_precision(self):
  # 100, 101, 102 => mean 101; exactly 101 does not win.
  rows=[row('DON',100,'2026-12-20 10:00:00','a'),
        row('RDG',101,'2026-12-20 11:00:00','b'),
        row('DAY',102,'2026-12-20 12:00:00','c')]
  l,f,r,_=run(rows)
  self.assertEqual({a['player'] for a in l['awards'] if a['type']=='gotm_beat_player_average'},{'DAY'})
  self.assertEqual(f['months']['2026-12']['player_average_score_sum'],303)
 def test_dedup_immutable_after_later_approval(self):
  old=[row('DON',900,'2026-12-20 10:00:00','a')]
  l,f,r,_=run(old)
  l2,f2,report,changed=run(old+[row('RDG',9999,'2026-12-21 10:00:00','b')],
                              awards=l,existing=f,now='2027-01-02T14:00:00-05:00')
  self.assertFalse(changed);self.assertEqual(report['status'],'already_final')
  self.assertEqual(l2,l);self.assertEqual(f2,f)
 def test_missing_reveal_or_benchmark_blocks(self):
  for published in ({'schema_version':1,'months':{}},
     {'schema_version':1,'months':{'2026-12':{'game_id':'99','game':'Robotron'}}}):
   l,f,r,c=run([row('DON',900,'2026-12-20 10:00:00')],published=published)
   self.assertFalse(c);self.assertEqual(l,ledger());self.assertEqual(f,final())
 def test_bad_date_blocks(self):
  l,f,r,c=run([row('DON',900,'garbage')])
  self.assertFalse(c);self.assertEqual(r['status'],'unparseable_dates_hold')
 def test_no_entrants_final_archive(self):
  l,f,r,c=run([])
  self.assertTrue(c);self.assertEqual(f['months']['2026-12']['podium'],[])
  self.assertTrue(f['months']['2026-12']['no_verified_entrants'])
  self.assertEqual(safe_result(f,'2026-12',at('2027-01-02T09:10:00-05:00'),archive()),'no_entrants')
 def test_preview_no_mutation(self):
  l,f,r,c=run([row('DON',900,'2026-12-20 10:00:00')],enabled=False)
  self.assertFalse(c);self.assertEqual(l,ledger());self.assertEqual(f,final())
 def test_not_first_month_or_wrong_day(self):
  for d in ('2026-12-02T10:00:00-05:00','2027-01-03T10:00:00-05:00'):
   l,f,r,c=run([],now=d)
   self.assertFalse(c);self.assertEqual(f,final())
 def test_player_best_only_one_monthly_credit(self):
  rows=[row('DON',100,'2026-12-20 10:00:00','a'),
        row('DON',950,'2026-12-22 10:00:00','b')]
  l,f,r,_=run(rows)
  self.assertEqual(len(l['verified_plays']),1)
  self.assertEqual(l['verified_plays'][0]['score'],950)
 def test_existing_monthly_credit_preserved(self):
  prior=ledger()
  prior['verified_plays'].append({'kind':'monthly','date':'2026-12-01','player':'DON','event_key':'monthly:2026-12-01:99:DON'})
  l,f,r,_=run([row('DON',900,'2026-12-22 10:00:00')],awards=prior)
  self.assertEqual(len(l['verified_plays']),1)
 def test_no_hidden_premature_game(self):
  l,f,r,c=run([row('DON',900,'2026-12-22 10:00:00')],
              published={'schema_version':1,'months':{}})
  self.assertEqual(r['status'],'missing_revealed_month')
  self.assertFalse(c)
if __name__=='__main__':unittest.main()
