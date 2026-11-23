#!/usr/bin/env python3
"""Fail-closed SOCIAL achievement milestone rules.

This is a pure calculator, NOT a live sync, award job, or Supabase scraper.
A privileged, authenticated server-side audit must eventually supply verified
immutable social events. The current public initials + device tokens are NOT
trusted player identities and MUST NOT be passed off as verified events.

Only approved social events with a verified actor and an auditable server event
ID are eligible. Calendar boundaries use America/New_York, not browser time.
"""
from collections import defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo
import re

TZ = ZoneInfo('America/New_York')
MILESTONES = (1, 5, 10, 25, 50, 100)
TRACKS = ('trash_talk', 'give_props')
# Give Props means supportive reactions, not negative reactions.
POSITIVE_REACTIONS = frozenset(('heart', 'invader', 'joystick', 'gamepad', 'quarter', 'trophy'))
NAMES = {
    'trash_talk': {
        1: 'Trash Talk Rookie', 5: 'Trash Talk Regular', 10: 'Trash Talk Veteran',
        25: 'Trash Talk Legend', 50: 'Master of Banter', 100: 'Arcade Mouthpiece',
    },
    'give_props': {
        1: 'Props Giver', 5: 'Hi 5!', 10: 'Good Sport',
        25: 'Hype Squad', 50: 'Community Champion', 100: 'Props Legend',
    },
}
PLAYER = re.compile(r'[A-Z0-9 ]{1,3}\Z')
SERVER_SOURCE = 'authenticated_social_audit'

def verified_days(events, now):
    """Build separate daily credits from independently verified immutable records.

    Required server-side evidence: identity_verified, trusted_source, event_id,
    immutable created_at, event_kind, actor_player, target_player for Give Props,
    active/not-deleted status. All must be verified by a secure backend BEFORE
    calling this pure function. No client-side initials assertion is trusted.
    """
    if not isinstance(events, list):
        raise ValueError('Expected list of privileged social audit events')
    end = now.astimezone(TZ).date()
    days = defaultdict(set)
    event_ids = set()
    for item in events:
        if not isinstance(item, dict):
            continue
        if (item.get('trusted_source') != SERVER_SOURCE or
                item.get('identity_verified') is not True or
                item.get('active') is not True):
            continue
        event_id = item.get('event_id')
        if not isinstance(event_id, str) or not event_id.strip():
            continue
        if event_id in event_ids:
            continue
        kind = item.get('event_kind')
        if kind not in TRACKS:
            continue
        player = item.get('actor_player')
        if not isinstance(player, str) or not PLAYER.fullmatch(player) or not player.strip():
            continue
        if kind == 'give_props':
            if item.get('reaction') not in POSITIVE_REACTIONS:
                continue
            target = item.get('target_player')
            if not isinstance(target, str) or not PLAYER.fullmatch(target) or not target.strip():
                continue
            if target == player:
                continue  # No self-props, including another of own scores.
        try:
            timestamp = datetime.fromisoformat(item['created_at'].replace('Z', '+00:00'))
            if timestamp.utcoffset() is None:
                continue  # Server event timestamp must contain offset.
            day = timestamp.astimezone(TZ).date()
            if day > end:
                continue
        except (TypeError, ValueError, KeyError, AttributeError, OverflowError):
            continue
        event_ids.add(event_id)
        days[(player, kind)].add(day)
    return days

def awards_due(ledger, events, now):
    """Preview social awards due; never writes files or issues trophies.

    The caller must be a trusted server/operator job with a verified source.
    """
    if (not isinstance(ledger, dict) or ledger.get('schema_version') != 1 or
            not isinstance(ledger.get('awards'), list)):
        raise ValueError('Invalid verified achievement ledger; refusing social awards')
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError('Explicit timezone required')
    present = {a.get('id') for a in ledger['awards'] if isinstance(a, dict)}
    result = []
    for (player, kind), dates in sorted(verified_days(events, now).items()):
        ordered = sorted(dates)
        for threshold in MILESTONES:
            if len(ordered) < threshold:
                continue
            key = f'social_{kind}:{player}:{threshold}'
            if key in present:
                continue
            result.append({
                'id': key, 'event_key': key, 'type': f'social_{kind}_milestone',
                'name': NAMES[kind][threshold], 'player': player,
                'date': ordered[threshold-1].isoformat(),
                'game': 'Arcade Community', 'milestone': threshold,
                'verification_method': SERVER_SOURCE,
                'verified_at': now.isoformat(),
            })
            present.add(key)
    return result
