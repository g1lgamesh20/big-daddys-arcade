import copy,unittest
from datetime import datetime,timezone
from just_in_time_preview import preview
from just_in_time_activate import activate
def journal(date='2026-11-25T23:55:00-05:00',score=101):
 return {'schema_version':1,'policy':'post_2026_11_19_approved_iscored_scores','scores':{'10':{'score_id':'10','name':'DON','game':'A','score':score,'date':date,'first_observed_at':'2026-11-26T17:00:00+00:00'}}}
def history():return {'schema_version':1,'timezone':'America/New_York','days':[{'date':'2026-11-25','game_id':'A','game':'Robotron'}]}
def baselines():return {'2026-11-25':{'game_id':'A','starting_champion_score':100,'observed_at':'2026-11-25T04:00:00+00:00'}}
def ledger():return {'schema_version':1,'awards':[],'verified_plays':[]}
NOW=datetime(2026,11,27,tzinfo=timezone.utc)
class JustInTimeTests(unittest.TestCase):
 def test_at_1155(self):self.assertEqual(len(preview(journal(),history(),baselines())['candidates']),1)
 def test_at_115959(self):self.assertEqual(len(preview(journal('2026-11-25T23:59:59-05:00'),history(),baselines())['candidates']),1)
 def test_before_window(self):self.assertEqual(preview(journal('2026-11-25T23:54:59-05:00'),history(),baselines())['candidates'],[])
 def test_midnight_next_day(self):self.assertEqual(preview(journal('2026-11-26T00:00:00-05:00'),history(),baselines())['candidates'],[])
 def test_tie_no_win(self):self.assertEqual(preview(journal(score=100),history(),baselines())['candidates'],[])
 def test_lower_no_win(self):self.assertEqual(preview(journal(score=99),history(),baselines())['candidates'],[])
 def test_wrong_game(self):
  j=journal();j['scores']['10']['game']='B'
  self.assertEqual(preview(j,history(),baselines())['candidates'],[])
 def test_missing_baseline(self):self.assertEqual(preview(journal(),history(),{})['candidates'],[])
 def test_baseline_after_start(self):
  b=baselines();b['2026-11-25']['observed_at']='2026-11-25T12:00:00+00:00'
  self.assertEqual(preview(journal(),history(),b)['candidates'],[])
 def test_bad_journal(self):
  with self.assertRaises(ValueError):preview({},history(),baselines())
 def test_award(self):
  _,added=activate(journal(),history(),baselines(),ledger(),NOW,enabled=True)
  self.assertEqual(len(added),1);self.assertEqual(added[0]['type'],'secret_just_in_time')
 def test_idempotent(self):
  updated,_=activate(journal(),history(),baselines(),ledger(),NOW,enabled=True)
  same,added=activate(journal(),history(),baselines(),updated,NOW,enabled=True)
  self.assertEqual(same,updated);self.assertEqual(added,[])
 def test_off(self):self.assertEqual(activate(journal(),history(),baselines(),ledger(),NOW),(ledger(),[]))
 def test_bad_ledger(self):
  with self.assertRaises(ValueError):activate(journal(),history(),baselines(),{},NOW,enabled=True)
 def test_duplicate_awards(self):
  l=ledger();l['awards']=[{'id':'x'},{'id':'x'}]
  with self.assertRaises(ValueError):activate(journal(),history(),baselines(),l,NOW,enabled=True)
 def test_no_mutation(self):
  j=journal();h=history();b=baselines();l=ledger();before=copy.deepcopy((j,h,b,l))
  activate(j,h,b,l,NOW,enabled=True);self.assertEqual((j,h,b,l),before)
 def test_naive_now(self):
  with self.assertRaises(ValueError):activate(journal(),history(),baselines(),ledger(),datetime(2026,11,27),enabled=True)
if __name__=='__main__':unittest.main()
