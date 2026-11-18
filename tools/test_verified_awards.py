#!/usr/bin/env python3
"""Safety tests: trophy awards only after matching finalized event + operator review."""
import unittest
from datetime import datetime,timezone
from verify_challenge_award import approve
NOW=datetime(2026,11,17,tzinfo=timezone.utc)
PENDING={'candidates':[
 {'kind':'thursday','date':'2026-11-12','player':'RDG','game_id':'112913','game':'Bosconian','score_id':'777','best_score':63450,'verification':'pending_iscored_approval_and_timezone_review','awarded':False},
 {'kind':'daily','date':'2026-11-17','player':'DON','game_id':'50010','game':'1942','score_id':'888','best_score':150000,'verification':'pending_iscored_approval_and_timezone_review','awarded':False}
]}
WINNERS={'weeks':[{'week':'2026-11-12','game_id':'112913','status':'final','winner':{'player':'RDG','score':63450}}]}
def empty():return {'schema_version':1,'awards':[],'verified_plays':[]}
class AwardsTest(unittest.TestCase):
 def call(self,ledger,kind='thursday_champion',date='2026-11-12',player='RDG',sid='777',confirmed=True,winners=WINNERS):
  return approve(PENDING,winners,ledger,kind=kind,event_date=date,player=player,score_id=sid,confirmed=confirmed,now=NOW)
 def test_thursday_trophy(self):
  ledger,changed=self.call(empty())
  self.assertTrue(changed)
  self.assertEqual(len(ledger['awards']),1)
  self.assertEqual(ledger['awards'][0]['type'],'thursday_champion')
 def test_idempotent(self):
  ledger,_=self.call(empty())
  ledger,changed=self.call(ledger)
  self.assertFalse(changed)
  self.assertEqual(len(ledger['awards']),1)
 def test_unconfirmed_rejected(self):
  with self.assertRaises(ValueError):self.call(empty(),confirmed=False)
 def test_wrong_score_id_rejected(self):
  with self.assertRaises(ValueError):self.call(empty(),sid='WRONG')
 def test_unfinalized_rejected(self):
  with self.assertRaises(ValueError):self.call(empty(),winners={'weeks':[]})
 def test_thursday_verified_participation_without_champion(self):
  ledger,changed=self.call(empty(),kind='thursday_verified_play')
  self.assertTrue(changed)
  self.assertEqual(len(ledger['awards']),0)
  self.assertEqual(len(ledger['verified_plays']),1)
  self.assertEqual(ledger['verified_plays'][0]['kind'],'thursday')
  ledger,changed=self.call(ledger,kind='thursday_verified_play')
  self.assertFalse(changed)
  self.assertEqual(len(ledger['verified_plays']),1)
 def test_daily_is_not_trophy(self):
  ledger,changed=self.call(empty(),kind='daily_verified_play',date='2026-11-17',player='DON',sid='888')
  self.assertTrue(changed)
  self.assertEqual(len(ledger['awards']),0)
  self.assertEqual(len(ledger['verified_plays']),1)
  self.assertFalse(ledger['verified_plays'][0]['trophy_issued'])

 def test_daily_participation_five_day_milestone_and_no_duplicates(self):
  ledger=empty()
  for n in range(1,6):
   day=f'2026-11-{n:02d}'
   sid=f'90{n}'
   candidate={'kind':'daily','date':day,'player':'DON','game_id':'50010',
       'game':'1942','score_id':sid,'best_score':1000+n,
       'verification':'pending_iscored_approval_and_timezone_review','awarded':False}
   pending={'candidates':[candidate]}
   ledger,changed=approve(pending,WINNERS,ledger,kind='daily_verified_play',
      event_date=day,player='DON',score_id=sid,confirmed=True,now=NOW)
   self.assertTrue(changed)
   self.assertEqual(len(ledger['awards']),1 if n==5 else 0)
  self.assertEqual(ledger['awards'][0]['id'],'daily_participation:DON:5')
  self.assertEqual(ledger['awards'][0]['type'],'daily_participation_milestone')
  ledger,changed=approve(pending,WINNERS,ledger,kind='daily_verified_play',
     event_date='2026-11-05',player='DON',score_id='905',confirmed=True,now=NOW)
  self.assertFalse(changed)
  self.assertEqual(len(ledger['awards']),1)

 def test_daily_milestones_require_distinct_dates_and_player(self):
  from verify_challenge_award import issue_daily_milestones
  ledger=empty()
  for i in range(7):
   ledger['verified_plays'].append({'kind':'daily','player':'VJG','date':'2026-11-01',
       'event_key':f'daily:2026-11-01:50010:VJG:{i}'})
  for i in range(4):
   ledger['verified_plays'].append({'kind':'daily','player':'DON','date':f'2026-11-{i+1:02d}',
       'event_key':f'daily:2026-11-{i+1:02d}:50010:DON'})
  issue_daily_milestones(ledger,'VJG',NOW)
  issue_daily_milestones(ledger,'DON',NOW)
  self.assertEqual(ledger['awards'],[])

 def test_all_four_daily_milestones_from_verified_plays(self):
  from verify_challenge_award import issue_daily_milestones
  from datetime import timedelta
  ledger=empty()
  for i in range(50):
   date=(datetime(2026,1,1,tzinfo=timezone.utc)+timedelta(days=i)).date().isoformat()
   ledger['verified_plays'].append({'kind':'daily','player':'RDG','date':date,
       'event_key':f'daily:{date}:50010:RDG'})
  issue_daily_milestones(ledger,'RDG',NOW)
  issue_daily_milestones(ledger,'RDG',NOW)
  self.assertEqual([a['milestone'] for a in ledger['awards']],[5,10,25,50])
  self.assertEqual(len(set(a['id'] for a in ledger['awards'])),4)
if __name__=='__main__':unittest.main()
