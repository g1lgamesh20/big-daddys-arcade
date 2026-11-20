#!/usr/bin/env python3
"""No-network regression for provider-confirmed submission time participation."""
import copy
import unittest
from datetime import datetime
from zoneinfo import ZoneInfo
from submission_time_participation import scan, CUTOVER

NY=ZoneInfo('America/New_York')
def now(value='2026-11-22T10:00:00-05:00'):
    return datetime.fromisoformat(value)
def row(sid,player,game,score,when):
    return {'id':sid,'name':player,'game':game,'gameName':'A game','score':score,'date':when}
def empty():return {'schema_version':1,'awards':[],'verified_plays':[]}
def daily(day='2026-11-20',gid='D'):
    return {'days':[{'date':day,'game_id':gid,'game':'Daily game'}]}
def thursday(day='2026-11-26',gid='T'):
    return {'weeks':{day:{'game_id':gid,'game':'Thursday game'}}}

class SubmissionTimeTests(unittest.TestCase):
    def scan(self,rows,archive=None,live=None,thurs=None,ledger=None,enabled=True,at=None):
        return scan(rows,archive if archive is not None else daily(),
            live if live is not None else {'days':[]},
            thurs if thurs is not None else {'weeks':{}},
            ledger if ledger is not None else empty(),
            at or now(),enabled=enabled)
    def test_cutover_and_central_midnight(self):
        self.assertEqual(CUTOVER.isoformat(),'2026-11-20T00:00:00-05:00')
        rows=[row('before','DON','D',111,'2026-11-19 22:59:59'),
              row('after','DON','D',222,'2026-11-19 23:00:00')]
        output,report,_=self.scan(rows)
        self.assertEqual([p['score_id'] for p in output['verified_plays']],['after'])
        self.assertEqual(report['counters']['pre_cutover_ignored'],1)
    def test_before_midnight_approved_after_eligible(self):
        # Public feed is modeled as appearing *only after* delayed approval.
        earlier,report,_=self.scan([],at=now('2026-11-21T00:10:00-05:00'))
        self.assertEqual(earlier,empty())
        approved=[row('new','FO','D',1000,'2026-11-20 21:55:00')]
        output,report,_=self.scan(approved,at=now('2026-11-22T09:00:00-05:00'))
        self.assertEqual(len(output['verified_plays']),1)
        self.assertEqual(output['verified_plays'][0]['original_submitted_at_et'],'2026-11-20T22:55:00-05:00')
        self.assertEqual(output['verified_plays'][0]['verification_method'],'iscored_developer_confirmed_original_submission_timestamp_post_fix')
    def test_after_midnight_no_previous_day_credit(self):
        rows=[row('late','DON','D',999,'2026-11-20 23:00:00')]
        output,report,_=self.scan(rows)
        self.assertEqual(output,empty())
        self.assertEqual(report['new_daily_credits'],0)
    def test_daily_and_thursday_only_same_game_and_day(self):
        rows=[row('daily','DON','D',20,'2026-11-20 13:00:00'),
              row('thu','DON','T',30,'2026-11-26 12:00:00'),
              row('wrong','RDG','WRONG',99,'2026-11-20 12:00:00')]
        output,report,_=self.scan(rows,thurs=thursday(),at=now('2026-11-27T12:00:00-05:00'))
        self.assertEqual({p['kind'] for p in output['verified_plays']},{'daily','thursday'})
        self.assertEqual(report['new_daily_credits'],1)
        self.assertEqual(report['new_thursday_credits'],1)
        self.assertEqual(output['awards'],[])
    def test_best_score_per_player_once_per_event(self):
        rows=[row('1','DON','D',10,'2026-11-20 11:00:00'),
              row('2','DON','D',40,'2026-11-20 16:00:00'),
              row('3','DON','D',40,'2026-11-20 17:00:00'),
              row('4','RDG','D',20,'2026-11-20 10:00:00')]
        output,report,_=self.scan(rows)
        self.assertEqual(len(output['verified_plays']),2)
        self.assertEqual(next(p for p in output['verified_plays'] if p['player']=='DON')['score_id'],'2')
        again,re_report,changed=self.scan(rows,ledger=output)
        self.assertFalse(changed)
        self.assertEqual(re_report['new_participation_credits'],0)
        self.assertEqual(again,output)
    def test_preserves_real_legacy_don_ghosts_goblins_credit(self):
        prior=empty()
        old={'kind':'daily','date':'2026-11-19','player':'DON','game_id':'50042',
             'game':"Ghosts 'n Goblins",'score':31600,'score_id':'387940',
             'event_key':'daily:2026-11-19:50042:DON',
             'verification_method':'approved_iscored_score_with_24h_generous_grace'}
        prior['verified_plays'].append(old)
        original=copy.deepcopy(prior)
        # Score may still be in public feed, but pre-cutover entries are not reissued.
        output,report,changed=self.scan([row('387940','DON','50042',31600,'2026-11-19 18:13:07')],
            archive=daily('2026-11-19','50042'),ledger=prior)
        self.assertFalse(changed)
        self.assertEqual(output,original)
        self.assertEqual(report['new_participation_credits'],0)
    def test_existing_credit_same_event_no_duplicate(self):
        prior=empty()
        prior['verified_plays'].append({'kind':'daily','date':'2026-11-20','player':'DON',
              'event_key':'daily:2026-11-20:D:DON'})
        out,report,changed=self.scan([row('NEW','DON','D',1000,'2026-11-20 10:00:00')],ledger=prior)
        self.assertFalse(changed)
        self.assertEqual(out,prior)
    def test_existing_champion_implies_attendance(self):
        prior=empty()
        prior['awards'].append({'type':'daily_champion','date':'2026-11-20','player':'DON',
                               'id':'daily_champion:2026-11-20:DON'})
        out,_,changed=self.scan([row('NEW','DON','D',9000,'2026-11-20 12:00:00')],ledger=prior)
        self.assertFalse(changed)
        self.assertEqual(out,prior)
    def test_future_and_bad_dates_ignored(self):
        rows=[row('future','DON','D',5,'2026-11-20 23:01:00'),
              row('bad','RDG','D',5,'not-a-date')]
        out,report,_=self.scan(rows,at=now('2026-11-20T12:00:00-05:00'))
        self.assertEqual(out,empty())
        self.assertEqual(report['counters']['future_timestamps_ignored'],1)
        self.assertEqual(report['counters']['missing_or_bad_timestamps'],1)
    def test_preview_does_not_modify_ledger(self):
        state=empty();snapshot=copy.deepcopy(state)
        out,report,changed=self.scan([row('a','DON','D',12,'2026-11-20 12:00:00')],
                                     ledger=state,enabled=False)
        self.assertFalse(changed)
        self.assertEqual(out,snapshot)
        self.assertEqual(state,snapshot)
        self.assertEqual(report['new_daily_credits'],1)
    def test_milestone_at_five_distinct_days(self):
        state=empty()
        days=['2026-11-20','2026-11-21','2026-11-22','2026-11-23','2026-11-24']
        rows=[row(str(i),'DON','D',i+10,day+' 12:00:00') for i,day in enumerate(days)]
        archive={'days':[{'date':day,'game_id':'D','game':'Daily game'} for day in days]}
        out,report,_=self.scan(rows,archive=archive,at=now('2026-11-25T12:00:00-05:00'))
        self.assertEqual(report['new_daily_credits'],5)
        self.assertEqual(len(out['verified_plays']),5)
        self.assertEqual(len([a for a in out['awards'] if a.get('type')=='daily_participation_milestone']),1)
    def test_no_monthly_credit_or_winner(self):
        out,report,_=self.scan([row('x','DON','M',999,'2026-12-10 11:00:00')],
            archive={'days':[]},at=now('2026-12-11T10:00:00-05:00'))
        self.assertEqual(out,empty())
        self.assertTrue(report['no_championship_or_monthly_awards'])
    def test_naive_now_rejected(self):
        with self.assertRaisesRegex(ValueError,'timezone'):
            self.scan([],at=datetime(2026,11,20))
if __name__=='__main__':unittest.main()
