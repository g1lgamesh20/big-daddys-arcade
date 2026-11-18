#!/usr/bin/env python3
"""No awards without live data, finalized history, one clear winner, and release gate."""
import unittest
from datetime import datetime
from zoneinfo import ZoneInfo
from auto_verified_challenge_awards import build

NY=ZoneInfo('America/New_York')
def when(day,hour=12):return datetime(2026,11,day,hour,tzinfo=NY)
def score(player,value,sid,day='2026-11-12',gid='112913'):
    return {'game':gid,'name':player,'score':value,'id':sid,'date':day+' 21:01:29'}
def ledger():return {'schema_version':1,'awards':[],'verified_plays':[]}
C={'kind':'thursday','date':'2026-11-12','game_id':'112913','game':'Bosconian','player':'RDG','score_id':'384380','best_score':63450,'awarded':False}
W={'week':'2026-11-12','game_id':'112913','game':'Bosconian','status':'final','winner':{'player':'RDG','score':63450}}
class Tests(unittest.TestCase):
 def scan(self, rows=None, pending=None, winners=None, stored=None, enabled=False, now=None):
    return build(rows if rows is not None else [score('RDG',63450,'384380'),score('DON',45110,'384377')],
      {'candidates':pending if pending is not None else [C]},
      {'weeks':winners if winners is not None else [W]},
      stored if stored is not None else ledger(),
      now or when(17),enabled=enabled)
 def test_preview_does_not_award_even_when_candidate_matches(self):
    out,p,changed=self.scan()
    self.assertFalse(changed)
    self.assertEqual(out,ledger())
    self.assertEqual(p['mode'],'preview_only')
    self.assertEqual(p['eligible_new_thursday_trophies'],0)
    self.assertEqual(p['potential_thursday_matches_without_submission_proof'],1)
    self.assertIn('No independent original submission timestamp',p['release_blocker'])
 def test_enabled_refuses_to_award_even_with_perfect_match(self):
    with self.assertRaisesRegex(ValueError,'Automatic challenge awards BLOCKED'):
      self.scan(enabled=True)
 def test_enabled_refuses_to_record_daily_verified_play(self):
    d={'kind':'daily','date':'2026-11-17','game_id':'50010','game':'1942',
       'player':'DON','score_id':'888','best_score':150000}
    rows=[score('DON',150000,'888','2026-11-17','50010')]
    with self.assertRaisesRegex(ValueError,'original submission time'):
      self.scan(rows=rows,pending=[d],winners=[],enabled=True)
 def test_stale_deleted_score_stays_unawarded(self):
    out,p,changed=self.scan(rows=[score('DON',45110,'384377')])
    self.assertFalse(changed)
    self.assertEqual(p['potential_thursday_matches_without_submission_proof'],0)
 def test_tie_stays_unawarded(self):
    out,p,changed=self.scan(rows=[score('RDG',63450,'384380'),score('DON',63450,'384377')])
    self.assertFalse(changed)
    self.assertEqual(p['blocked_thursday_events'],['2026-11-12:tie_requires_rule_review'])
 def test_late_grace_does_not_make_match_eligible(self):
    out,p,changed=self.scan(now=when(13))
    self.assertFalse(changed)
    self.assertEqual(p['potential_thursday_matches_without_submission_proof'],0)
 def test_daily_matches_only_diagnostic_not_credited(self):
    d={'kind':'daily','date':'2026-11-17','game_id':'50010','game':'1942',
       'player':'DON','score_id':'888','best_score':150000}
    rows=[score('DON',150000,'888','2026-11-17','50010')]
    out,p,changed=self.scan(rows=rows,pending=[d],winners=[])
    self.assertFalse(changed)
    self.assertEqual(out['verified_plays'],[])
    self.assertEqual(p['potential_daily_matches_without_submission_proof'],1)
if __name__=='__main__':unittest.main()
