#!/usr/bin/env python3
"""Milestones only from operator-verified permanent attendance and champions."""
import copy
import unittest
from datetime import datetime,timezone,timedelta
from unified_milestone_awards import awards_due,issue,activity

NOW=datetime(2027,7,18,tzinfo=timezone.utc)
def empty():return {'schema_version':1,'awards':[],'verified_plays':[]}

def add_day(ledger,kind,day,player='DON',game='101601'):
    ledger['verified_plays'].append({
        'event_key':f'{kind}:{day}:{game}:{player}','kind':kind,'date':day,
        'player':player,'game_id':game,'score_id':str(len(ledger['verified_plays'])+1)})

class MilestoneTest(unittest.TestCase):
 def test_existing_rdg_champion_implies_one_thursday_play_no_new_trophy(self):
  ledger=empty()
  ledger['awards'].append({'id':'thursday_champion:2026-11-12',
      'event_key':'thursday:2026-11-12:112913:RDG','type':'thursday_champion',
      'date':'2026-11-12','player':'RDG'})
  self.assertEqual(len(activity(ledger)[('RDG','thursday')]),1)
  self.assertEqual(awards_due(ledger,NOW),[])
 def test_thursday_milestones_dedup_and_existing_champion(self):
  ledger=empty()
  for n in range(5):
   day=(datetime(2026,11,12,tzinfo=timezone.utc)+timedelta(days=n*7)).date().isoformat()
   add_day(ledger,'thursday',day)
  original=copy.deepcopy(ledger)
  due=awards_due(ledger,NOW)
  self.assertEqual([(a['type'],a['milestone']) for a in due],
       [('thursday_participation_milestone',3),('thursday_participation_milestone',5)])
  self.assertEqual(ledger,original)
  self.assertEqual(issue(ledger,NOW),2)
  self.assertEqual(issue(ledger,NOW),0)
 def test_thursday_streak_breaks_at_skipped_week(self):
  ledger=empty()
  for day in ('2026-11-12','2026-11-19','2026-12-03','2026-12-10','2026-12-17'):
   add_day(ledger,'thursday',day)
  due=awards_due(ledger,NOW)
  self.assertEqual([a['milestone'] for a in due if a['type']=='thursday_streak'],[3])
 def test_daily_streak_not_based_on_approval_date(self):
  ledger=empty()
  for day in ('2026-11-16','2026-11-17','2026-11-18'):
   add_day(ledger,'daily',day)
  due=awards_due(ledger,NOW)
  self.assertEqual([(a['type'],a['milestone']) for a in due],[('daily_streak',3)])
 def test_duplicated_daily_event_never_advances(self):
  ledger=empty()
  for n in range(10):add_day(ledger,'daily','2026-11-16')
  self.assertEqual(awards_due(ledger,NOW),[])
 def test_monthly_milestones_and_streak(self):
  ledger=empty()
  for month in (12,1,2,3,4,5):
   year=2026 if month==12 else 2027
   add_day(ledger,'monthly',f'{year}-{month:02d}-01')
  due=awards_due(ledger,NOW)
  self.assertEqual([a['milestone'] for a in due if a['type']=='monthly_participation_milestone'],[3,6])
  self.assertEqual([a['milestone'] for a in due if a['type']=='monthly_streak'],[3,6])
 def test_monthly_champion_requires_explicit_event_month(self):
  ledger=empty()
  ledger['awards'].append({'id':'gotm_champion:2026-12:RDG',
      'event_key':'monthly:2026-12:RDG','type':'gotm_champion',
      'date':'2027-01-02','player':'RDG'})
  self.assertNotIn(('RDG','monthly'),activity(ledger))
  ledger['awards'][0]['event_month']='2026-12'
  self.assertEqual({d.isoformat() for d in activity(ledger)[('RDG','monthly')]},{'2026-12-01'})
 def test_future_dated_verified_entry_cannot_unlock_early(self):
  ledger=empty()
  for day in ('2026-11-16','2026-11-17','2026-11-18'):
   add_day(ledger,'daily',day)
  self.assertEqual(awards_due(ledger,datetime(2026,11,17,tzinfo=timezone.utc)),[])

 def test_candidate_scores_cannot_issue_rewards(self):
  ledger=empty();ledger['candidates']=[{'kind':'thursday','player':'DON','date':'2026-11-12'}]
  self.assertEqual(awards_due(ledger,NOW),[])

if __name__=='__main__':unittest.main()
