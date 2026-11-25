import copy,unittest
from datetime import datetime,timezone
from photo_finish_preview import preview
from photo_finish_activate import activate
def journal(score=99000,date='2026-11-25T12:00:00-05:00'):
 return {'schema_version':1,'policy':'post_2026_11_19_approved_iscored_scores','scores':{'10':{'score_id':'10','name':'DON','game':'A','score':score,'date':date,'first_observed_at':'2026-11-25T18:00:00+00:00'}}}
def history(record=100000,observed='2026-11-25T16:00:00+00:00'):
 return {'schema_version':1,'policy':'observed_approved_snapshots_only','holders_by_game':{'A':{'score':record,'holders':['RDG'],'winning_scores':[{'player':'RDG','score_id':'1','score':record}],'game':'Robotron','observed_at':observed}},'transitions':[]}
def ledger():return {'schema_version':1,'awards':[],'verified_plays':[]}
NOW=datetime(2026,11,26,tzinfo=timezone.utc)
class PhotoFinishTests(unittest.TestCase):
 def test_exact_one_percent(self):self.assertEqual(len(preview(journal(),history())['candidates']),1)
 def test_within_one_percent(self):self.assertEqual(len(preview(journal(99999),history())['candidates']),1)
 def test_below_threshold(self):self.assertEqual(preview(journal(98999),history())['candidates'],[])
 def test_tie(self):self.assertEqual(preview(journal(100000),history())['candidates'],[])
 def test_above_gold(self):self.assertEqual(preview(journal(100001),history())['candidates'],[])
 def test_before_observation(self):self.assertEqual(preview(journal(date='2026-11-25T10:00:00-05:00'),history())['candidates'],[])
 def test_same_observation(self):self.assertEqual(preview(journal(date='2026-11-25T11:00:00-05:00'),history())['candidates'],[])
 def test_no_baseline(self):
  h=history();h['holders_by_game']={}
  self.assertEqual(preview(journal(),h)['candidates'],[])
 def test_current_gold_holder(self):
  h=history();h['holders_by_game']['A']['holders']=['DON']
  self.assertEqual(preview(journal(),h)['candidates'],[])
 def test_test_game(self):
  h=history();h['holders_by_game']['A']['game']='Test Game'
  self.assertEqual(preview(journal(),h)['candidates'],[])
 def test_invalid_journal(self):
  with self.assertRaises(ValueError):preview({},history())
 def test_award(self):
  result,added=activate(journal(),history(),ledger(),NOW,enabled=True)
  self.assertEqual(len(added),1);self.assertEqual(added[0]['type'],'secret_photo_finish')
 def test_idempotent(self):
  result,_=activate(journal(),history(),ledger(),NOW,enabled=True)
  same,added=activate(journal(),history(),result,NOW,enabled=True)
  self.assertEqual(added,[]);self.assertEqual(same,result)
 def test_off(self):self.assertEqual(activate(journal(),history(),ledger(),NOW),(ledger(),[]))
 def test_bad_ledger(self):
  with self.assertRaises(ValueError):activate(journal(),history(),{},NOW,enabled=True)
 def test_duplicate_ledger(self):
  l=ledger();l['awards']=[{'id':'x'},{'id':'x'}]
  with self.assertRaises(ValueError):activate(journal(),history(),l,NOW,enabled=True)
 def test_no_mutation(self):
  j=journal();h=history();l=ledger();old=copy.deepcopy((j,h,l))
  activate(j,h,l,NOW,enabled=True);self.assertEqual((j,h,l),old)
 def test_naive_time(self):
  with self.assertRaises(ValueError):activate(journal(),history(),ledger(),datetime(2026,11,26),enabled=True)
 def test_integer_precision(self):self.assertEqual(preview(journal(99),history(100))['candidates'],[])
if __name__=='__main__':unittest.main()
