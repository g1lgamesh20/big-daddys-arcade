import copy
import unittest
from datetime import datetime, timezone
from personal_best_activate import activate
from test_personal_best_preview import journal, row

NOW=datetime(2026,12,15,tzinfo=timezone.utc)

def evidence():
    first=row(1,100,'2026-11-21T12:00:00-05:00')
    second=row(2,200,'2026-11-22T12:00:00-05:00')
    return journal([first,second])

def ledger():
    return {'schema_version':1,'awards':[{'id':'existing:award','date':'2026-11-20'}],
            'verified_plays':[]}

class ActivationTests(unittest.TestCase):
    def test_default_off(self):
        before=ledger()
        after, awards=activate(evidence(),before,NOW)
        self.assertEqual(after,before)
        self.assertEqual(awards,[])
    def test_first_milestone_only(self):
        after,awards=activate(evidence(),ledger(),NOW,enabled=True)
        self.assertEqual(len(awards),1)
        self.assertEqual(awards[0]['id'],'personal_best_milestone:DON:1')
        self.assertEqual(awards[0]['score_id'],'2')
        self.assertEqual(len(after['awards']),2)
    def test_idempotence(self):
        after,awards=activate(evidence(),ledger(),NOW,enabled=True)
        twice,second=activate(evidence(),after,NOW,enabled=True)
        self.assertEqual(second,[])
        self.assertEqual(after,twice)
    def test_no_mutation(self):
        old=ledger(); original=copy.deepcopy(old)
        activate(evidence(),old,NOW,enabled=True)
        self.assertEqual(old,original)
    def test_bad_ledger_fails_closed(self):
        with self.assertRaises(ValueError):
            activate(evidence(),{'schema_version':1,'awards':[]},NOW,enabled=True)
    def test_duplicate_existing_ids_fail_closed(self):
        old=ledger();old['awards'].append(copy.deepcopy(old['awards'][0]))
        with self.assertRaises(ValueError):
            activate(evidence(),old,NOW,enabled=True)
    def test_invalid_journal_fails_closed(self):
        with self.assertRaises(ValueError):
            activate({},ledger(),NOW,enabled=True)
    def test_no_future_or_pre_cutover_awards(self):
        bad=journal([row(1,100,'2026-11-19T12:00:00-05:00')])
        with self.assertRaises(ValueError):
            activate(bad,ledger(),NOW,enabled=True)

if __name__=='__main__':
    unittest.main()
