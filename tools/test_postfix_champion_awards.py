#!/usr/bin/env python3
"""Pure offline championship tests: original timestamps, grace, locks, idempotency."""
import copy
import unittest
from datetime import datetime
from postfix_champion_awards import finalize

def date(s):return datetime.fromisoformat(s)
def row(sid,player,score,game,dt):
 return {'id':sid,'name':player,'score':score,'game':game,'date':dt}
def empty():return {'schema_version':1,'awards':[],'verified_plays':[]}
def daily(day='2026-11-20',gid='D'):
 return {'days':[{'date':day,'game_id':gid,'game':'Daily featured'}]}
def thursday(day='2026-11-26',gid='T'):
 return {'weeks':{day:{'game_id':gid,'game':'Thursday featured'}}}
def lock(day='2026-11-20',gid='D',baseline=1000):
 return {day:{'game_id':gid,'starting_champion_score':baseline,
     'observed_at':(date(day+'T00:00:00-05:00').replace(day=int(day[-2:])-1)).isoformat(),
     'evidence':'pre_start_approved_iscored_score_snapshot'}}
def locks(day='2026-11-20',gid='D',baseline=1000):
 from datetime import timedelta
 start=date(day+'T00:00:00-05:00')
 return {day:{'game_id':gid,'starting_champion_score':baseline,
     'observed_at':(start-timedelta(minutes=10)).isoformat(),
     'evidence':'pre_start_approved_iscored_score_snapshot'}}
class ChampionshipTests(unittest.TestCase):
 def scan(self,rows,days=None,thu=None,baseline=None,ledger=None,now=None,enabled=True):
  return finalize(rows,days if days is not None else daily(),{'days':[]},
   thu if thu is not None else {'weeks':{}}, baseline if baseline is not None else locks(),
   ledger if ledger is not None else empty(),now or date('2026-11-22T04:00:00-05:00'),enabled=enabled)
 def test_daily_two_players_get_gold_and_tie_is_allowed(self):
  rows=[row('1','DON',1200,'D','2026-11-20 12:00:00'),
        row('2','RDG',1200,'D','2026-11-20 13:00:00'),
        row('3','DAY',1000,'D','2026-11-20 14:00:00')]
  result,report,_=self.scan(rows)
  self.assertEqual({a['player'] for a in result['awards']},{'DON','RDG'})
  self.assertEqual(report['new_daily_champions'],2)
  self.assertTrue(all(a['gold_level'] for a in result['awards']))
 def test_daily_waits_until_9am_next_morning(self):
  rows=[row('1','DON',1200,'D','2026-11-20 18:00:00')]
  before,report,_=self.scan(rows,now=date('2026-11-21T08:59:59-05:00'))
  self.assertEqual(before['awards'],[])
  self.assertGreater(report['events_waiting_for_9am'],0)
  after,_,_=self.scan(rows,now=date('2026-11-21T09:00:00-05:00'))
  self.assertEqual(len(after['awards']),1)
 def test_daily_missing_or_late_baseline_blocks(self):
  rows=[row('1','DON',1200,'D','2026-11-20 18:00:00')]
  for b in ({},{'2026-11-20':{**locks()['2026-11-20'],'observed_at':'2026-11-20T00:30:00-05:00'}},
            {'2026-11-20':{**locks()['2026-11-20'],'evidence':'made_up'}}):
   result,report,_=self.scan(rows,baseline=b)
   self.assertEqual(result['awards'],[])
   self.assertEqual(report['events_missing_baseline'],1)
 def test_pre_cutover_november_19_unmodified(self):
  original=empty()
  original['awards'].append({'id':'thursday_champion:2026-11-12','type':'thursday_champion',
                              'date':'2026-11-12','player':'RDG'})
  snapshot=copy.deepcopy(original)
  r,report,changed=self.scan([row('old','DON',9999,'OLD','2026-11-19 19:00:00')],
   days=daily('2026-11-19','OLD'),thu=thursday('2026-11-19','OLD'),
   baseline=locks('2026-11-19','OLD',1),ledger=original)
  self.assertFalse(changed)
  self.assertEqual(r,snapshot)
 def test_thursday_waits_and_selects_highest(self):
  rows=[row('1','DON',3000,'T','2026-11-26 16:00:00'),
        row('2','RDG',4000,'T','2026-11-26 18:00:00')]
  before,report,_=self.scan(rows,days={'days':[]},thu=thursday(),
    now=date('2026-11-27T08:59:59-05:00'))
  self.assertEqual(before['awards'],[])
  after,report,_=self.scan(rows,days={'days':[]},thu=thursday(),
    now=date('2026-11-27T09:00:00-05:00'))
  self.assertEqual(report['new_thursday_champions'],1)
  self.assertEqual(after['awards'][0]['player'],'RDG')
  self.assertEqual(after['awards'][0]['approval_cutoff_et'],'2026-11-27T09:00:00-05:00')
 def test_late_approval_after_midnight_keeps_original_event(self):
  # Row appears on a later fetch, but original score time remains Nov 26.
  rows=[row('1','DON',3000,'T','2026-11-26 21:00:00')]
  early,_,_=self.scan([],days={'days':[]},thu=thursday(),now=date('2026-11-27T08:59:00-05:00'))
  self.assertEqual(early['awards'],[])
  later,_,_=self.scan(rows,days={'days':[]},thu=thursday(),now=date('2026-11-27T09:05:00-05:00'))
  self.assertEqual(later['awards'][0]['player'],'DON')
 def test_after_midnight_central_is_next_eastern_day(self):
  rows=[row('before','DON',1200,'D','2026-11-20 22:59:59'),
        row('after','RDG',5000,'D','2026-11-20 23:00:00')]
  result,_,_=self.scan(rows)
  self.assertEqual([a['player'] for a in result['awards']],['DON'])
 def test_duplicate_scan_and_existing_award_preserved(self):
  rows=[row('1','DON',2000,'D','2026-11-20 12:00:00')]
  first,_,_=self.scan(rows)
  again,report,changed=self.scan(rows,ledger=first)
  self.assertFalse(changed)
  self.assertEqual(report['new_daily_champions'],0)
  self.assertEqual(again,first)
 def test_thursday_conflict_does_not_rewrite(self):
  rows=[row('1','DON',3000,'T','2026-11-26 16:00:00')]
  first,_,_=self.scan(rows,days={'days':[]},thu=thursday(),
                           now=date('2026-11-28T01:00:00-05:00'))
  later=rows+[row('2','RDG',6000,'T','2026-11-26 17:00:00')]
  second,report,changed=self.scan(later,days={'days':[]},thu=thursday(),ledger=first,
                             now=date('2026-11-27T11:00:00-05:00'))
  self.assertFalse(changed)
  self.assertEqual(report['thursday_result_conflicts'],1)
  self.assertEqual(second,first)
 def test_unparseable_same_game_timestamp_blocks(self):
  rows=[row('1','DON',3000,'T','2026-11-26 16:00:00'),
        row('2','RDG',9999,'T','unparseable')]
  result,report,_=self.scan(rows,days={'days':[]},thu=thursday(),
                             now=date('2026-11-27T09:01:00-05:00'))
  self.assertEqual(result['awards'],[])
  self.assertEqual(report['events_held_bad_dates'],1)
 def test_preview_never_modifies_permanent_ledger(self):
  state=empty();saved=copy.deepcopy(state)
  result,report,changed=self.scan([row('1','DON',1200,'D','2026-11-20 12:00:00')],
                                     ledger=state,enabled=False)
  self.assertFalse(changed);self.assertEqual(result,saved);self.assertEqual(state,saved)
  self.assertEqual(report['new_daily_champions'],1)
 def test_no_monthly_trophies_even_with_monthly_score(self):
  r,report,_=self.scan([row('1','DON',9000,'M','2026-12-10 12:00:00')],days={'days':[]})
  self.assertEqual(r,empty());self.assertTrue(report['no_monthly_trophies_or_push'])
 def test_requires_aware_now(self):
  with self.assertRaisesRegex(ValueError,'timezone-aware'):
   self.scan([],now=datetime(2026,11,22))
if __name__=='__main__':unittest.main()
