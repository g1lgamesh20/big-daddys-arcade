#!/usr/bin/env python3
"""Offline April 1 tease and April 2 reveal (NO awards)."""
import unittest
from datetime import datetime, timezone
from april_fools_bulletin import event_at,payload,JOKE

class AprilFoolsTests(unittest.TestCase):
    def test_two_april_events_at_nine_eastern(self):
        self.assertIsNone(event_at(datetime(2027,4,1,12,59,tzinfo=timezone.utc)))
        one=event_at(datetime(2027,4,1,13,0,tzinfo=timezone.utc))
        two=event_at(datetime(2027,4,2,13,0,tzinfo=timezone.utc))
        self.assertEqual(one[0],"april-fools:2027:01")
        self.assertEqual(two[0],"april-fools:2027:02")
        self.assertEqual(two[2],JOKE)
        self.assertIsNone(event_at(datetime(2027,4,3,13,tzinfo=timezone.utc)))

    def test_stable_push_idempotency_and_no_award_fields(self):
        key,title,message=event_at(datetime(2027,4,1,13,tzinfo=timezone.utc))
        p=payload(key,title,message)
        self.assertEqual(p["idempotency_key"],payload(key,title,message)["idempotency_key"])
        self.assertNotIn("award",p)
        self.assertNotIn("trophy",p["data"])

if __name__=="__main__":unittest.main()
