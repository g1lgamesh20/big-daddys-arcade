"""Offline tests for inclusive positive/negative arcade reaction digest."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from preview_props_reconciliation import EMOJI, reconcile
from preview_props_message import format_digest
from preview_props_onesignal_payload import build_payload, validate_payload
from props_delivery_integration import plan_delivery

DAY = "2026-11-22"
SCORES = {"42": ("VJG", "Ikari Warriors")}
PLAYERS = {"DON", "VJG"}


def sample(reaction):
    event = {"id": 1, "reaction_id": 7, "score_id": 42,
             "player_initials": "DON", "event_action": "added",
             "new_reaction": reaction}
    active = {7: {"id": 7, "score_id": 42, "player_initials": "DON",
                  "reaction": reaction}}
    return reconcile([event], active, SCORES, PLAYERS)


class NegativeDigestTests(unittest.TestCase):
    def test_every_supported_reaction_is_eligible(self):
        for reaction in ("heart", "invader", "joystick", "gamepad",
                         "quarter", "trophy", "poop", "angry"):
            with self.subTest(reaction=reaction):
                entries, excluded, count = sample(reaction)
                self.assertEqual(entries, [("DON", "VJG", "Ikari Warriors", reaction)])
                self.assertFalse(excluded)
                self.assertEqual(count, 1)
                self.assertIn(reaction, EMOJI)

    def test_negative_only_day_builds_payload(self):
        entries, _, _ = sample("poop")
        decision, payload = plan_delivery(DAY, entries, 0, [])
        self.assertIn("NOT AUTHORIZED", decision)
        validate_payload(payload, DAY)
        self.assertIn("💩", payload["contents"]["en"])
        self.assertIn("Arcade Reactions", payload["headings"]["en"])

    def test_angry_emoji_in_message(self):
        entries, _, _ = sample("angry")
        title, body = format_digest(DAY, entries)
        self.assertIn("😡", body)
        self.assertIn("Arcade Reactions", title)

    def test_removed_negative_still_excluded(self):
        event = {"id": 1, "reaction_id": 7, "score_id": 42,
                 "player_initials": "DON", "event_action": "removed",
                 "new_reaction": None}
        entries, excluded, _ = reconcile([event], {}, SCORES, PLAYERS)
        self.assertEqual(entries, [])
        self.assertEqual(excluded["not_eligible_at_day_end"], 1)

    def test_empty_day_still_skips(self):
        self.assertIsNone(build_payload(DAY, []))


if __name__ == "__main__":
    unittest.main()
