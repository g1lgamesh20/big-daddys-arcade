#!/usr/bin/env python3
"""Offline tests: no network, no OneSignal sends, no changes to the live arcade."""
import json
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
sys.path.insert(0,str(Path(__file__).resolve().parent))
from send_monthly_notification import build, run, safe_result

NY=ZoneInfo('America/New_York')
def at(date):return datetime.fromisoformat(date).replace(tzinfo=NY)
def put(root,name,value):
    (root/name).write_text(json.dumps(value),encoding='utf-8')
def live(month='2026-12',game='ROBOTRON'):
    return {'schema_version':1,'month':month,'game':game,'game_id':'50167',
            'status':'provisional','starting_record':1000,'benchmark':750,
            'reveal_at':month+'-01T09:00:00-05:00'}
def verified():
    return {'schema_version':1,'months':{'2026-12':{
        'status':'final_verified',
        'eligibility_source':'original_submission_timestamps_verified',
        'all_pending_resolved':True,'game_id':'50167',
        'finalized_at':'2027-01-02T08:00:00-05:00',
        'podium':[{'player':'DON','rank':1,'score':1000},
                  {'player':'RDG','rank':1,'score':1000},
                  {'player':'DAY','rank':3,'score':700}]}}}
class MonthlyPushTests(unittest.TestCase):
 def setUp(self):
    self.tmp=tempfile.TemporaryDirectory()
    self.addCleanup(self.tmp.cleanup)
    self.root=Path(self.tmp.name)
 def test_no_premature_or_no_preexisting_reveal(self):
    put(self.root,'monthly-challenge-live.json',live())
    for date in ['2026-11-30T09:00:00','2026-12-01T08:59:00',
                 '2026-12-02T09:00:00']:
        self.assertIsNone(build('reveal',at(date),self.root,lambda:live()))
    self.assertIsNone(build('reveal',at('2026-12-01T09:15:00'),self.root,lambda:{}))
 def test_december_push_once_and_after_pages_publish(self):
    put(self.root,'monthly-challenge-live.json',live())
    calls=[]
    send=lambda p:(calls.append(p) or {'id':'onesignal-id'})
    now=at('2026-12-01T09:20:00')
    self.assertEqual(run('reveal',now,self.root,send,lambda:live()),'sent')
    self.assertEqual(run('reveal',now,self.root,send,lambda:live()),'already_sent')
    self.assertEqual(len(calls),1)
    self.assertIn('ROBOTRON',calls[0]['contents']['en'])
    self.assertNotIn('TOMORROW',calls[0]['contents']['en'])
    self.assertEqual(calls[0]['included_segments'],['All'])
    self.assertTrue(calls[0]['idempotency_key'])
 def test_january_reminder_in_same_push(self):
    published=live('2027-01',game='PAC-MAN')
    published['reveal_at']='2027-01-01T09:00:00-05:00'
    put(self.root,'monthly-challenge-live.json',published)
    item=build('reveal',at('2027-01-01T09:10:00'),self.root,lambda:published)
    self.assertIn('TOMORROW',item[2])
    self.assertIn('December 2026',item[2])
    self.assertIn('9 AM Eastern',item[2])
 def test_no_fake_results_or_preview_or_wrong_month(self):
    put(self.root,'published-monthly-challenge-history.json',
        {'schema_version':1,'months':{'2026-12':{'game_id':'50167'}}})
    now=at('2027-01-02T09:15:00')
    self.assertIsNone(build('results',now,self.root))
    obj=verified();obj['months']['2026-12']['status']='provisional'
    put(self.root,'monthly-final-results.json',obj)
    self.assertIsNone(build('results',now,self.root))
    obj['months']['2026-12']['status']='final_verified'
    obj['months']['2026-12']['eligibility_source']='approved_score_with_24h_generous_grace'
    put(self.root,'monthly-final-results.json',obj)
    self.assertIsNone(build('results',now,self.root))
 def test_results_require_close_approval_and_ties(self):
    put(self.root,'published-monthly-challenge-history.json',
        {'schema_version':1,'months':{'2026-12':{'game_id':'50167'}}})
    put(self.root,'monthly-final-results.json',verified())
    self.assertIsNone(build('results',at('2027-01-02T08:59:00'),self.root))
    result=build('results',at('2027-01-02T09:10:00'),self.root)
    self.assertIn('DON, RDG',result[2])
    self.assertNotIn('DAY',result[2])
    sends=[]
    send=lambda x:(sends.append(x) or {'id':'push2'})
    self.assertEqual(run('results',at('2027-01-02T09:10:00'),self.root,send),'sent')
    self.assertEqual(run('results',at('2027-01-02T09:20:00'),self.root,send),'already_sent')
    self.assertEqual(len(sends),1)
 def test_pending_or_wrong_game_or_early_finalization_blocked(self):
    base=verified()
    archive={'schema_version':1,'months':{'2026-12':{'game_id':'50167'}}}
    for key,val in [('all_pending_resolved',False),('game_id','abc'),('finalized_at','2027-01-01T23:59:00-05:00')]:
      item=verified();item['months']['2026-12'][key]=val
      self.assertIsNone(safe_result(item,'2026-12',at('2027-01-02T09:00:00'),archive))
 def test_no_entrants_and_invalid_tie(self):
    archive={'schema_version':1,'months':{'2026-12':{'game_id':'50167'}}}
    item=verified()
    item['months']['2026-12'].update({'podium':[],'no_verified_entrants':True})
    self.assertEqual(safe_result(item,'2026-12',at('2027-01-02T09:00:00'),archive),'no_entrants')
    item['months']['2026-12'].update({'podium':[{'player':'DON','rank':2,'score':12}],'no_verified_entrants':False})
    self.assertIsNone(safe_result(item,'2026-12',at('2027-01-02T09:00:00'),archive))
 def test_one_signal_error_does_not_mark_sent(self):
    put(self.root,'monthly-challenge-live.json',live())
    with self.assertRaises(RuntimeError):
      run('reveal',at('2026-12-01T09:20:00'),self.root,
          sender=lambda _: {'errors':['failed']},public_fetch=lambda:live())
    self.assertFalse((self.root/'monthly-notification-state.json').exists())
 def test_dst_correctness(self):
    march=live('2027-03',game='GALAGA')
    march['reveal_at']='2027-03-01T09:00:00-05:00'
    put(self.root,'monthly-challenge-live.json',march)
    self.assertIsNotNone(build('reveal',at('2027-03-01T09:10:00'),self.root,lambda:march))
if __name__=='__main__':unittest.main()
