import copy,unittest
from datetime import datetime,timezone
from back_from_the_dead_activate import activate
from test_back_from_the_dead_preview import journal,history
NOW=datetime(2026,12,2,tzinfo=timezone.utc)
def ledger():return {'schema_version':1,'awards':[{'id':'existing:award','date':'2026-11-20'}],'verified_plays':[]}
class ActivationTests(unittest.TestCase):
    def test_default_off(self):
        l=ledger();self.assertEqual(activate(journal(),history(),l,NOW),(l,[]))
    def test_verified_award(self):
        after,added=activate(journal(),history(),ledger(),NOW,enabled=True)
        self.assertEqual(len(added),1);self.assertEqual(added[0]['id'],'secret_back_from_the_dead:DON');self.assertEqual(len(after['awards']),2)
    def test_idempotent(self):
        after,_=activate(journal(),history(),ledger(),NOW,enabled=True)
        again,added=activate(journal(),history(),after,NOW,enabled=True)
        self.assertEqual(added,[]);self.assertEqual(after,again)
    def test_no_candidate(self):
        h=history();h['transitions']=h['transitions'][:1]
        self.assertEqual(activate(journal(),h,ledger(),NOW,enabled=True)[1],[])
    def test_invalid_journal(self):
        with self.assertRaises(ValueError):activate({},history(),ledger(),NOW,enabled=True)
    def test_invalid_ledger(self):
        with self.assertRaises(ValueError):activate(journal(),history(),{'schema_version':1,'awards':[]},NOW,enabled=True)
    def test_duplicate_award(self):
        l=ledger();l['awards'].append(copy.deepcopy(l['awards'][0]))
        with self.assertRaises(ValueError):activate(journal(),history(),l,NOW,enabled=True)
    def test_existing_lifetime_award(self):
        l=ledger();l['awards'].append({'id':'secret_back_from_the_dead:DON','type':'secret_back_from_the_dead','player':'DON'})
        self.assertEqual(activate(journal(),history(),l,NOW,enabled=True)[1],[])
    def test_no_mutation(self):
        j=journal();h=history();l=ledger();before=copy.deepcopy((j,h,l))
        activate(j,h,l,NOW,enabled=True);self.assertEqual((j,h,l),before)
    def test_naive_time(self):
        with self.assertRaises(ValueError):activate(journal(),history(),ledger(),datetime(2026,12,2),enabled=True)
if __name__=='__main__':unittest.main()
