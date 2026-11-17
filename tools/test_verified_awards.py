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
 def test_daily_is_not_trophy(self):
  ledger,changed=self.call(empty(),kind='daily_verified_play',date='2026-11-17',player='DON',sid='888')
  self.assertTrue(changed)
  self.assertEqual(len(ledger['awards']),0)
  self.assertEqual(len(ledger['verified_plays']),1)
  self.assertFalse(ledger['verified_plays'][0]['trophy_issued'])
if __name__=='__main__':unittest.main()
