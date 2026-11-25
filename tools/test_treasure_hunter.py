import copy,unittest
from datetime import datetime,timezone,timedelta
from treasure_hunter_state import evaluate
from treasure_hunter_preview import preview
from treasure_hunter_activate import activate
T0=datetime(2026,11,25,12,tzinfo=timezone.utc)
def catalog():return {'games':{'A':'Robotron','B':'Galaga','C':'Test Game'}}
def rows():return [{'id':'10','name':'DON','game':'A','gameName':'Robotron','score':1000}]
def journal(date='2026-11-25T13:00:00+00:00'):
 return {'schema_version':1,'policy':'post_2026_11_19_approved_iscored_scores','scores':{'10':{'score_id':'10','name':'DON','game':'A','score':1000,'date':date,'first_observed_at':'2026-11-25T14:00:00+00:00'}}}
def ledger():return {'schema_version':1,'awards':[],'verified_plays':[]}
def seeded():
 empty=evaluate([],catalog(),None,T0)
 return evaluate(rows(),catalog(),empty,T0+timedelta(hours=2))
class TreasureTests(unittest.TestCase):
 def test_initial_empty(self):
  x=evaluate([],catalog(),None,T0);self.assertEqual(set(x['empty_games']),{'A','B'})
 def test_initial_scored_never_first(self):
  x=evaluate(rows(),catalog(),None,T0);self.assertEqual(x['first_gold'],[])
 def test_first_gold(self):self.assertEqual(len(seeded()['first_gold']),1)
 def test_preview(self):self.assertEqual(len(preview(journal(),seeded())['candidates']),1)
 def test_award(self):
  _,added=activate(journal(),seeded(),ledger(),T0+timedelta(hours=3),enabled=True)
  self.assertEqual(len(added),1)
 def test_idempotent(self):
  result,_=activate(journal(),seeded(),ledger(),T0+timedelta(hours=3),enabled=True)
  same,added=activate(journal(),seeded(),result,T0+timedelta(hours=3),enabled=True)
  self.assertEqual(added,[]);self.assertEqual(same,result)
 def test_before_empty_no_award(self):self.assertEqual(preview(journal('2026-11-25T11:00:00+00:00'),seeded())['candidates'],[])
 def test_missing_approved_no_award(self):
  j=journal();j['scores']={}
  self.assertEqual(preview(j,seeded())['candidates'],[])
 def test_no_backfill(self):
  x=evaluate(rows(),catalog(),None,T0)
  self.assertEqual(preview(journal(),x)['candidates'],[])
 def test_same_game_not_repeated(self):
  x=seeded();y=evaluate(rows(),catalog(),x,T0+timedelta(hours=3))
  self.assertEqual(len(y['first_gold']),1)
 def test_no_test_game(self):self.assertNotIn('C',evaluate([],catalog(),None,T0)['empty_games'])
 def test_disabled(self):self.assertEqual(activate(journal(),seeded(),ledger(),T0),(ledger(),[]))
 def test_bad_ledger(self):
  with self.assertRaises(ValueError):activate(journal(),seeded(),{},T0,enabled=True)
 def test_duplicate_ledger(self):
  l=ledger();l['awards']=[{'id':'x'},{'id':'x'}]
  with self.assertRaises(ValueError):activate(journal(),seeded(),l,T0,enabled=True)
 def test_no_mutation(self):
  j=journal();s=seeded();l=ledger();before=copy.deepcopy((j,s,l))
  activate(j,s,l,T0,enabled=True);self.assertEqual((j,s,l),before)
 def test_naive(self):
  with self.assertRaises(ValueError):activate(journal(),seeded(),ledger(),datetime(2026,11,25),enabled=True)
if __name__=='__main__':unittest.main()
