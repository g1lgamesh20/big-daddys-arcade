#!/usr/bin/env python3
"""Prove social trophies are one credit per ET day, fail-closed and idempotent."""
import unittest
from datetime import datetime, timezone
from social_achievement_rules import verified_days, awards_due, MILESTONES

NOW = datetime(2026, 11, 20, 17, tzinfo=timezone.utc)
LEDGER = {'schema_version': 1, 'awards': []}

def evt(n, kind='give_props', when='2026-11-19T16:01:00+00:00', player='DON',
        target='RDG', reaction='quarter', **kw):
    e = {'event_id': str(n), 'event_kind': kind, 'actor_player': player,
         'target_player': target, 'reaction': reaction, 'created_at': when,
         'trusted_source': 'authenticated_social_audit',
         'identity_verified': True, 'active': True}
    e.update(kw)
    return e

class SocialAchievementsTests(unittest.TestCase):
    def test_one_daily_credit_despite_mass_reacting(self):
        rows = [evt(i, target='RDG') for i in range(200)]
        days = verified_days(rows, NOW)
        self.assertEqual(len(days[('DON', 'give_props')]), 1)
        earned = awards_due(LEDGER, rows, NOW)
        self.assertEqual([a['milestone'] for a in earned], [1])

    def test_separate_tracks_and_both_trash_talk_locations(self):
        rows = [evt(1, 'give_props'), evt(2, 'trash_talk'),
                evt(3, 'trash_talk', reaction=None, target=None)]
        awards = awards_due(LEDGER, rows, NOW)
        self.assertEqual({a['type'] for a in awards},
            {'social_give_props_milestone', 'social_trash_talk_milestone'})
        self.assertEqual(len(awards), 2)

    def test_eastern_midnight_and_dst(self):
        rows = [evt(1, when='2026-11-19T04:58:00Z'),
                evt(2, when='2026-11-19T05:02:00Z')]
        self.assertEqual(len(verified_days(rows, NOW)[('DON','give_props')]), 2)
        # Fall DST repeated local hour is the SAME Eastern calendar day.
        rows = [evt(3, when='2026-11-01T05:30:00Z'),
                evt(4, when='2026-11-01T06:30:00Z')]
        self.assertEqual(len(verified_days(rows, NOW)[('DON','give_props')]), 1)

    def test_milestones_stack_not_reset(self):
        rows = [evt(i,when=f'2026-11-{i:02d}T17:00:00Z') for i in range(1, 11)]
        unlocked = awards_due(LEDGER, rows, NOW)
        self.assertEqual([a['milestone'] for a in unlocked], [1,5,10])
        prior = {'schema_version':1,'awards':[unlocked[0]]}
        self.assertEqual([a['milestone'] for a in awards_due(prior, rows, NOW)], [5,10])
        self.assertEqual(MILESTONES, (1,5,10,25,50,100))

    def test_no_self_props_or_negative_reaction(self):
        rows = [evt(1,target='DON'), evt(2,reaction='angry'),
                evt(3,reaction='poop'), evt(4,reaction=None),
                evt(5,target='DON',reaction='heart')]
        self.assertEqual(awards_due(LEDGER,rows,NOW),[])

    def test_failed_or_anonymous_identity_never_awards(self):
        rows = [evt(1, identity_verified=False),evt(2,trusted_source='browser'),
                evt(3,player=''),evt(4,player='UNKNOWN'),evt(5,active=False),
                evt(6,created_at='2026-11-19T05:00:00')]
        self.assertEqual(awards_due(LEDGER,rows,NOW),[])

    def test_duplicate_event_ids_no_duplicated_credit(self):
        rows = [evt('same',when='2026-11-18T16:00:00Z'),
                evt('same',when='2026-11-19T16:00:00Z')]
        self.assertEqual(len(verified_days(rows,NOW)[('DON','give_props')]),1)

    def test_future_dated_events_rejected(self):
        self.assertEqual(awards_due(LEDGER,[evt(1,when='2026-12-19T16:00:00Z')],NOW),[])

    def test_fail_closed_invalid_ledger(self):
        with self.assertRaises(ValueError):
            awards_due({},[evt(1)],NOW)

if __name__=='__main__':
    unittest.main()
