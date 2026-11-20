#!/usr/bin/env python3
"""Offline regression checks for delayed Friday champion notifications."""
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo
import send_friday_champion_notification as mod

NY=ZoneInfo('America/New_York')
FRIDAY=datetime(2026,11,20,9,0,tzinfo=NY)
FEED={'week':'2026-11-19','status':'final','game':'After Burner Climax',
      'winner':{'player':'DON','score':161470},'unparseable_game_dates':0}
class TestFriday(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory()
  self.addCleanup(self.temp.cleanup)
  folder=Path(self.temp.name)
  self.feed=folder/'thursday-challenge.json'
  self.state=folder/'friday-champion-notification-state.json'
  self.feed.write_text(json.dumps(FEED),encoding='utf-8')
  self.patch_feed=patch.object(mod,'FEED',self.feed)
  self.patch_state=patch.object(mod,'STATE',self.state)
  self.patch_feed.start();self.patch_state.start()
  self.addCleanup(self.patch_feed.stop);self.addCleanup(self.patch_state.stop)
  self.sent=[]
  def sender(payload):
   self.sent.append(payload)
   return {'id':'synthetic-confirmation'}
  self.sender=sender
 def test_no_send_before_9(self):
  self.assertEqual(mod.run(FRIDAY.replace(hour=8,minute=59),self.sender),'outside_window')
  self.assertEqual(self.sent,[])
 def test_sends_at_9(self):
  self.assertEqual(mod.run(FRIDAY,self.sender),'sent')
  self.assertEqual(len(self.sent),1)
 def test_missed_schedule_catches_up_later_friday(self):
  self.assertEqual(mod.run(FRIDAY.replace(hour=11,minute=37),self.sender),'sent')
  self.assertIn('2026-11-19',json.loads(self.state.read_text())['announced_weeks'])
  self.assertEqual(mod.run(FRIDAY.replace(hour=15),self.sender),'already_sent')
  self.assertEqual(len(self.sent),1)
 def test_never_sends_saturday(self):
  self.assertEqual(mod.run(FRIDAY.replace(day=21,hour=10),self.sender),'outside_window')
 def test_unfinalized_data_holds(self):
  self.feed.write_text(json.dumps({**FEED,'status':'live'}))
  self.assertEqual(mod.run(FRIDAY.replace(hour=12),self.sender),'not_final')
  self.assertFalse(self.sent)
 def test_no_unverified_dates(self):
  self.feed.write_text(json.dumps({**FEED,'unparseable_game_dates':1}))
  self.assertEqual(mod.run(FRIDAY.replace(hour=12),self.sender),'unverified_dates')
 def test_no_new_push_after_already_sent_week(self):
  self.state.write_text(json.dumps({'announced_weeks':['2026-11-19']}))
  self.assertEqual(mod.run(FRIDAY.replace(hour=10),self.sender),'already_sent')
  self.assertEqual(self.sent,[])
if __name__=='__main__':unittest.main()
