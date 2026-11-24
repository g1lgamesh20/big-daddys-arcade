#!/usr/bin/env python3
import unittest
from datetime import datetime, timezone
from secret_evidence_journal import empty, merge, preview

NOW=datetime(2026,11,24,12,tzinfo=timezone.utc)
def score(i,game='A',date='2026-11-23T02:00:00-05:00'):
    return {'id':str(i),'name':'DON','game':game,'gameName':'Robotron','score':100,'date':date}

class JournalTests(unittest.TestCase):
    def test_add_and_idempotent(self):
        state,n=merge(empty(),[score(1)],NOW)
        self.assertEqual(n,1)
        state2,n=merge(state,[score(1)],NOW)
        self.assertEqual(n,0)
        self.assertEqual(state,state2)
    def test_retains_disappeared_scores(self):
        state,_=merge(empty(),[score(1)],NOW)
        next_state,n=merge(state,[],NOW)
        self.assertEqual(n,0)
        self.assertEqual(len(next_state['scores']),1)
    def test_conflicting_player_rejected(self):
        state,_=merge(empty(),[score(1)],NOW)
        changed=score(1);changed['name']='OTHER'
        with self.assertRaises(ValueError):merge(state,[changed],NOW)
    def test_conflicting_timestamp_rejected(self):
        state,_=merge(empty(),[score(1)],NOW)
        with self.assertRaises(ValueError):merge(state,[score(1,date='2026-11-23T03:00:00-05:00')],NOW)
    def test_conflicting_score_rejected(self):
        state,_=merge(empty(),[score(1)],NOW)
        changed=score(1);changed['score']=101
        with self.assertRaises(ValueError):merge(state,[changed],NOW)
    def test_no_pre_fix_entries(self):
        state,n=merge(empty(),[score(1,date='2026-11-18T01:00:00-05:00')],NOW)
        self.assertEqual(n,0)
        self.assertFalse(state['scores'])
    def test_night_owl_preview_does_not_modify_ledger(self):
        state,_=merge(empty(),[score(1)],NOW)
        ledger={'schema_version':1,'awards':[],'verified_plays':[]}
        report=preview(state,ledger,NOW)
        self.assertEqual(report['mode'],'preview_only')
        self.assertEqual(report['proposed'][0]['id'],'secret_night_owl:DON')
        self.assertEqual(ledger['awards'],[])
    def test_invalid_journal_fails_closed(self):
        with self.assertRaises(ValueError):merge({},[score(1)],NOW)

if __name__=='__main__':unittest.main()
