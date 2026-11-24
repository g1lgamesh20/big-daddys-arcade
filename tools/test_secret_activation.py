"""Offline tests: controlled Stage 4 activation remains opt-in."""
import unittest
from datetime import datetime, timezone
from secret_activate import activate
from secret_evidence_journal import empty, merge

NOW=datetime(2026,11,24,18,tzinfo=timezone.utc)
LEDGER={'schema_version':1,'awards':[{'id':'existing:1','type':'daily_champion','date':'2026-11-21'}],'verified_plays':[]}
def row(i,game):
    return {'id':str(i),'name':'DON','game':str(game),'gameName':'Game '+str(game),
            'score':100,'date':'2026-11-22T13:00:00-05:00'}

class ActivationTests(unittest.TestCase):
    def test_disabled_is_noop(self):
        journal,_=merge(empty(),[row(i,i) for i in range(10)],NOW)
        out,awards=activate(journal,LEDGER,NOW)
        self.assertIs(out,LEDGER)
        self.assertEqual(awards,[])
    def test_enabled_adds_only_new_awards(self):
        journal,_=merge(empty(),[row(i,i) for i in range(10)],NOW)
        out,awards=activate(journal,LEDGER,NOW,enabled=True)
        self.assertEqual(len(awards),2)
        self.assertEqual(out['awards'][0]['id'],'existing:1')
        again,second=activate(journal,out,NOW,enabled=True)
        self.assertEqual(second,[])
        self.assertEqual(out,again)
    def test_corrupt_journal_refuses(self):
        with self.assertRaises(ValueError):
            activate({'schema_version':1,'scores':{'1':{'score_id':'2'}}},LEDGER,NOW,enabled=True)

if __name__=='__main__':unittest.main()
