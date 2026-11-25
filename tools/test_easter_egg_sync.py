#!/usr/bin/env python3
"""Offline validation for anonymous Easter Egg ledger sync."""
import unittest
from easter_egg_sync import merge

class EasterEggTests(unittest.TestCase):
    def test_one_award_per_player_and_preserves_existing(self):
        original = {"schema_version":1,"awards":[{"id":"other:ABC","player":"ABC"}],"verified_plays":[{"kind":"daily"}]}
        claims = {"schema_version":1,"claims":[{"player_initials":"ABC","claimed_at":"2026-11-25T20:00:00Z"},{"player_initials":"XYZ","claimed_at":"2026-11-25T20:00:01Z"}]}
        result,new = merge(original,claims)
        self.assertEqual(len(new),2)
        self.assertEqual(result["verified_plays"],original["verified_plays"])
        self.assertEqual(len(original["awards"]),1)
        result2,new2 = merge(result,claims)
        self.assertEqual(new2,[])
        self.assertEqual(len(result2["awards"]),3)
    def test_rejects_invalid_players(self):
        for player in ["","____","abcdef","éé","A'"]:
            with self.subTest(player=player),self.assertRaises(ValueError):
                merge({"schema_version":1,"awards":[]},{"schema_version":1,"claims":[{"player_initials":player,"claimed_at":"2026-11-25T20:00:00Z"}]})
    def test_rejects_malformed_feed(self):
        with self.assertRaises(ValueError):
            merge({"schema_version":1,"awards":[]},{"claims":[]})
    def test_rejects_timestamp(self):
        with self.assertRaises(ValueError):
            merge({"schema_version":1,"awards":[]},{"schema_version":1,"claims":[{"player_initials":"ABC","claimed_at":"bad"}]})
if __name__=="__main__": unittest.main()
