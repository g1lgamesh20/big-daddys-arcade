"""Offline contract tests for the Stage 4 preview adapter."""
import unittest
from datetime import datetime
from zoneinfo import ZoneInfo
from secret_achievements import evaluate

NOW=datetime(2026,11,24,12,tzinfo=ZoneInfo('America/New_York'))
LEDGER={'schema_version':1,'awards':[],'verified_plays':[]}
def row(i,game,when,player='DON'):
    return {'id':str(i),'name':player,'game':str(game),'gameName':'Game '+str(game),'score':100,'date':when}
class IntegrationContract(unittest.TestCase):
    def test_no_trusted_attestation_refuses(self):
        with self.assertRaises(ValueError): evaluate([],LEDGER,NOW)
    def test_repeat_does_not_reaward(self):
        rows=[row(i,i,'2026-11-22T13:00:00-05:00') for i in range(10)]
        a,first=evaluate(rows,LEDGER,NOW,trusted_approved_feed=True)
        b,second=evaluate(rows,a,NOW,trusted_approved_feed=True)
        self.assertEqual(len(first),2)
        self.assertEqual(second,[])
        self.assertEqual(a,b)
    def test_existing_awards_untouched(self):
        original={'schema_version':1,'awards':[{'id':'daily_participation:DON:5','type':'daily_participation_milestone','date':'2026-11-23'}],'verified_plays':[]}
        a,_=evaluate([row(1,1,'2026-11-22T01:00:00-05:00')],original,NOW,trusted_approved_feed=True)
        self.assertEqual(original['awards'],[{'id':'daily_participation:DON:5','type':'daily_participation_milestone','date':'2026-11-23'}])
        self.assertEqual(len(a['awards']),2)
    def test_conflicting_score_id_refuses_all_awards(self):
        rows=[row(1,1,'2026-11-22T01:00:00-05:00'),row(1,2,'2026-11-22T01:00:00-05:00')]
        with self.assertRaisesRegex(ValueError,'Conflicting approved rows'):
            evaluate(rows,LEDGER,NOW,trusted_approved_feed=True)
    def test_identical_duplicate_score_id_is_safe(self):
        item=row(1,1,'2026-11-22T01:00:00-05:00')
        _,awards=evaluate([item,item],LEDGER,NOW,trusted_approved_feed=True)
        self.assertEqual(len(awards),1)
    def test_pre_cutover_is_not_backfilled(self):
        a,awards=evaluate([row(1,1,'2026-11-19T01:00:00-05:00')],LEDGER,NOW,trusted_approved_feed=True)
        self.assertEqual(awards,[])
if __name__=='__main__': unittest.main()
