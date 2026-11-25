#!/usr/bin/env python3
"""Offline social trophy sync validation."""
import unittest
from social_trophy_sync import merge

class SocialTrophyTests(unittest.TestCase):
    def setUp(self):
        self.ledger={"schema_version":1,"awards":[{"id":"easter_egg:DON"}],"verified_plays":[]}
    def test_merge_idempotent_and_preserves_existing(self):
        payload={"schema_version":1,"prospective_only":True,"awards":[
            {"id":"social_trash_talk:DON:1","type":"social_trash_talk","name":"Trash Talk Rookie","player":"DON","date":"2026-11-25","milestone":1},
            {"id":"secret_props_machine:DON","type":"secret_props_machine","name":"PROPS MACHINE!","player":"DON","date":"2026-11-25"}]}
        first,new=merge(self.ledger,payload)
        self.assertEqual(len(new),2)
        self.assertEqual(len(self.ledger["awards"]),1)
        again,duplicates=merge(first,payload)
        self.assertEqual(len(duplicates),0)
        self.assertEqual(again["verified_plays"],[])
    def test_refuse_browser_forged_or_invalid(self):
        examples=[
            {"id":"social_trash_talk:DON:2","type":"social_trash_talk","name":"Trash Talk Rookie","player":"DON","date":"2026-11-25","milestone":2},
            {"id":"social_give_props:DON:1","type":"social_give_props","name":"Props Giver","player":"HAX","date":"2026-11-25","milestone":1},
            {"id":"secret_props_machine:DON","type":"secret_props_machine","name":"WRONG","player":"DON","date":"2026-11-25"},
            {"id":"social_trash_talk:DON:1","type":"social_trash_talk","name":"Trash Talk Rookie","player":"DON","date":"bad","milestone":1},
        ]
        for entry in examples:
            with self.subTest(entry=entry),self.assertRaises(ValueError):
                merge(self.ledger,{"schema_version":1,"prospective_only":True,"awards":[entry]})
    def test_feed_requires_prospective_flag(self):
        with self.assertRaises(ValueError):
            merge(self.ledger,{"schema_version":1,"awards":[]})

if __name__=="__main__": unittest.main()
