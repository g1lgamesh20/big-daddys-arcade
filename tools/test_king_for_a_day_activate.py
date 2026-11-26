import copy,unittest
from datetime import datetime,timedelta,timezone
from king_for_a_day_activate import activate
from test_gold_history_secret_preview import history,advance,row,T0
def ledger():return {'schema_version':1,'awards':[],'verified_plays':[]}
class KingForADayTests(unittest.TestCase):
    def test_default_off(self):self.assertEqual(activate(history(),ledger(),T0+timedelta(days=2)),(ledger(),[]))
    def test_23_hours_not_eligible(self):self.assertEqual(activate(history(),ledger(),T0+timedelta(hours=23),enabled=True)[1],[])
    def test_24_hours_eligible(self):
        h=history();h=advance(h,[row(1,'DON',100),row(2,'RDG',90)],[1,2],1440)
        result,added=activate(h,ledger(),T0+timedelta(hours=24),enabled=True)
        self.assertEqual(len(added),1);self.assertEqual(added[0]['id'],'secret_king_for_a_day:DON')
    def test_idempotent(self):
        h=history();h=advance(h,[row(1,'DON',100),row(2,'RDG',90)],[1,2],1440);now=T0+timedelta(days=2)
        first,_=activate(h,ledger(),now,enabled=True)
        second,added=activate(h,first,now,enabled=True)
        self.assertEqual(added,[]);self.assertEqual(first,second)
    def test_lost_gold_disqualifies(self):
        h=history();h=advance(h,[row(1,'DON',100),row(2,'RDG',90),row(3,'RDG',150)],[1,2],60)
        h=advance(h,[row(1,'DON',100),row(2,'RDG',90),row(3,'RDG',150)],[1,2,3],1500)
        self.assertEqual(activate(h,ledger(),T0+timedelta(days=2),enabled=True)[1][0]['player'],'RDG')
    def test_elapsed_time_without_second_snapshot_not_enough(self):
        self.assertEqual(activate(history(),ledger(),T0+timedelta(days=2),enabled=True)[1],[])
    def test_invalid_ledger(self):
        with self.assertRaises(ValueError):activate(history(),{'awards':[]},T0+timedelta(days=2),enabled=True)
    def test_duplicate_award(self):
        l=ledger();l['awards']=[{'id':'dup'},{'id':'dup'}]
        with self.assertRaises(ValueError):activate(history(),l,T0+timedelta(days=2),enabled=True)
    def test_no_mutation(self):
        h=history();l=ledger();before=copy.deepcopy((h,l))
        activate(h,l,T0+timedelta(days=2),enabled=True);self.assertEqual((h,l),before)
    def test_naive_time(self):
        with self.assertRaises(ValueError):activate(history(),ledger(),datetime(2026,11,26),enabled=True)
    def test_test_game_excluded(self):
        h=history();h['holders_by_game']['A']['game']='Test Game'
        self.assertEqual(activate(h,ledger(),T0+timedelta(days=2),enabled=True)[1],[])
if __name__=='__main__':unittest.main()
