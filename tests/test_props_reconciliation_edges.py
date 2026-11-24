"""Offline synthetic event fixtures for digest reconciliation. No live data/writes."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from preview_props_reconciliation import reconcile

SCORES = {"42": ("VJG", "Ikari Warriors")}
PLAYERS = {"DON", "VJG", "ABC"}


def event(event_id, action, reaction, rid=7, giver="DON"):
    return {"id": event_id, "reaction_id": rid, "score_id": 42,
            "player_initials": giver, "event_action": action,
            "new_reaction": reaction}


def active(reaction="joystick", rid=7, giver="DON"):
    return {rid: {"id": rid, "score_id": 42, "player_initials": giver,
                  "reaction": reaction}}


class ReconciliationEdgeTests(unittest.TestCase):
    def test_added_positive(self):
        entries, excluded, count = reconcile([event(1, "added", "joystick")],
                                             active(), SCORES, PLAYERS)
        self.assertEqual(entries, [("DON", "VJG", "Ikari Warriors", "joystick")])
        self.assertEqual(count, 1)

    def test_changed_before_midnight_uses_latest_event_once(self):
        entries, _, count = reconcile([
            event(1, "added", "heart"),
            event(2, "changed", "joystick"),
        ], active(), SCORES, PLAYERS)
        self.assertEqual(entries, [("DON", "VJG", "Ikari Warriors", "joystick")])
        self.assertEqual(count, 1)

    def test_changed_to_negative_before_midnight_included(self):
        entries, excluded, _ = reconcile([
            event(1, "added", "heart"), event(2, "changed", "angry"),
        ], active("angry"), SCORES, PLAYERS)
        self.assertEqual(entries, [("DON", "VJG", "Ikari Warriors", "angry")])
        self.assertEqual(sum(excluded.values()), 0)

    def test_removed_before_midnight_excluded(self):
        entries, excluded, _ = reconcile([
            event(1, "added", "heart"), event(2, "removed", None),
        ], {}, SCORES, PLAYERS)
        self.assertEqual(entries, [])
        self.assertEqual(excluded["not_eligible_at_day_end"], 1)

    def test_removed_after_midnight_before_send_excluded(self):
        entries, excluded, _ = reconcile([event(1, "added", "heart")],
                                         {}, SCORES, PLAYERS)
        self.assertEqual(entries, [])
        self.assertEqual(excluded["since_removed"], 1)

    def test_changed_after_midnight_before_send_excluded_current_policy(self):
        # Current implementation suppresses yesterday's event when current
        # reaction differs. This policy needs operator confirmation.
        entries, excluded, _ = reconcile([event(1, "added", "heart")],
                                         active("joystick"), SCORES, PLAYERS)
        self.assertEqual(entries, [])
        self.assertEqual(excluded["since_changed"], 1)

    def test_changed_after_midnight_to_negative_excluded_as_changed(self):
        entries, excluded, _ = reconcile([event(1, "added", "heart")],
                                         active("poop"), SCORES, PLAYERS)
        self.assertEqual(entries, [])
        self.assertEqual(excluded["since_changed"], 1)

    def test_removed_and_readded_after_midnight_does_not_reuse_old_identity(self):
        entries, excluded, _ = reconcile([event(1, "added", "heart", rid=7)],
                                         active("heart", rid=8), SCORES, PLAYERS)
        self.assertEqual(entries, [])
        self.assertEqual(excluded["since_removed"], 1)

    def test_unknown_initials_excluded(self):
        entries, excluded, _ = reconcile([event(1, "added", "heart", giver="ZZZ")],
                                         active("heart", giver="ZZZ"), SCORES, PLAYERS)
        self.assertEqual(entries, [])
        self.assertEqual(excluded["invalid_giver"], 1)

    def test_giver_mismatch_excluded(self):
        entries, excluded, _ = reconcile([event(1, "added", "heart")],
                                         active("heart", giver="ABC"), SCORES, PLAYERS)
        self.assertEqual(entries, [])
        self.assertEqual(excluded["giver_mismatch"], 1)

    def test_score_mismatch_excluded(self):
        rows = active("heart")
        rows[7]["score_id"] = 99
        entries, excluded, _ = reconcile([event(1, "added", "heart")],
                                         rows, SCORES, PLAYERS)
        self.assertEqual(entries, [])
        self.assertEqual(excluded["score_mismatch"], 1)

    def test_missing_score_excluded(self):
        entries, excluded, _ = reconcile([event(1, "added", "heart")],
                                         active("heart"), {}, PLAYERS)
        self.assertEqual(entries, [])
        self.assertEqual(excluded["unresolved_score"], 1)

    def test_duplicate_event_updates_single_entry(self):
        entries, _, count = reconcile([
            event(1, "added", "heart"),
            event(2, "changed", "joystick"),
            event(3, "changed", "heart"),
        ], active("heart"), SCORES, PLAYERS)
        self.assertEqual(len(entries), 1)
        self.assertEqual(count, 1)


if __name__ == "__main__":
    unittest.main()
