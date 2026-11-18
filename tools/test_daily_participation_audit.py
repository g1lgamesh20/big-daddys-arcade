#!/usr/bin/env python3
"""Safety regression checks for read-only Daily candidate discovery."""
import copy
import unittest
from datetime import datetime,timezone
from audit_daily_participation import audit, selections

NOW=datetime(2026,11,18,tzinfo=timezone.utc)
SELECTED={'2026-11-17':{'game_id':'86751','game':'Wolverine'},
          '2026-11-18':{'game_id':'101601','game':'Food Fight'}}
LEDGER={'schema_version':1,'awards':[],'verified_plays':[]}

def score(id,player,game,raw,points=1234):
    return {'id':id,'name':player,'game':game,'date':raw,'score':points}

class AuditSafetyTest(unittest.TestCase):
    def test_one_potential_match_never_grants_credits(self):
        original=copy.deepcopy(LEDGER)
        r=audit([score('500','DON','101601','2026-11-18 15:30:00')],
                SELECTED,LEDGER,NOW)
        self.assertEqual(r['possible_matches'],1)
        self.assertEqual(r['candidates'][0]['status'],'NEEDS_ORIGINAL_SUBMISSION_TIME')
        self.assertFalse(r['candidates'][0]['verified'])
        self.assertFalse(r['candidates'][0]['eligible_for_trophy'])
        self.assertEqual(r['automatic_verified_plays_added'],0)
        self.assertEqual(r['trophies_issued'],0)
        self.assertEqual(LEDGER,original)
    def test_late_approval_is_only_potential_not_automatically_credited(self):
        r=audit([score('501','VJG','86751','2026-11-18 11:30:46')],
                SELECTED,LEDGER,NOW)
        self.assertEqual(r['possible_matches'],1)
        self.assertEqual(r['candidates'][0]['date'],'2026-11-17')
        self.assertFalse(r['candidates'][0]['verified'])
    def test_existing_daily_credit_not_double_counted(self):
        ledger={'schema_version':1,'awards':[],'verified_plays':[
            {'kind':'daily','player':'DON','date':'2026-11-18',
            'event_key':'daily:2026-11-18:101601:DON'}]}
        r=audit([score('500','DON','101601','2026-11-18 15:30:00')],
                SELECTED,ledger,NOW)
        self.assertEqual(r['possible_matches'],0)
    def test_wrong_game_and_old_approvals_are_excluded(self):
        rows=[score('1','DON','999','2026-11-18 15:00:00'),
              score('2','DON','101601','2026-11-01 15:00:00')]
        self.assertEqual(audit(rows,SELECTED,LEDGER,NOW)['possible_matches'],0)
    def test_repeated_score_id_no_duplicate_candidate(self):
        entry=score('123','DON','101601','2026-11-18 15:30:00')
        self.assertEqual(audit([entry,entry],SELECTED,LEDGER,NOW)['possible_matches'],1)
    def test_conflicting_daily_selections_fail_closed(self):
        with self.assertRaises(ValueError):
            selections({'days':[{'date':'2026-11-18','game_id':'1'}]},
                       {'days':[{'date':'2026-11-18','game_id':'2'}]})

if __name__=='__main__':unittest.main()
