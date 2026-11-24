#!/usr/bin/env python3
"""Pure, fail-closed secret trophy evaluator. No network, writes, or pushes.

Approved iScored rows are accepted only when the caller supplies a trusted
post-fix approval feed. Pre-cutover timestamps are excluded because earlier
approval edits may have overwritten submission dates. This evaluator must not
be wired into production until the integration checks are completed.
"""
import copy
from collections import defaultdict
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from iscored_timestamp import parse_iscored_time

EASTERN = ZoneInfo('America/New_York')
CUTOVER = datetime(2026, 11, 20, tzinfo=EASTERN)
NAMES = {'secret_high_five': 'HIGH FIVE!', 'secret_night_owl': 'NIGHT OWL',
         'secret_arcade_hopper': 'ARCADE HOPPER'}


def evidence(rows, now):
    """Deduplicate approved score IDs and reject unsafe timestamps."""
    if now.tzinfo is None:
        raise ValueError('now must be timezone-aware')
    now = now.astimezone(EASTERN)
    unique = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        sid = str(row.get('id') or '').strip()
        player = str(row.get('name') or '').strip().upper()[:48]
        game = str(row.get('game') or '').strip()
        if not sid or not player or not game:
            continue
        raw = row.get('score')
        if isinstance(raw, bool):
            continue
        try:
            score = int(raw)
        except (ValueError, TypeError):
            continue
        if score < 0:
            continue
        dt = parse_iscored_time(row.get('date'))
        if dt is None or dt < CUTOVER or dt > now:
            continue
        candidate = {'score_id': sid, 'player': player, 'game_id': game,
                       'game': str(row.get('gameName') or '')[:100], 'score': score,
                       'submitted_at_et': dt, 'day': dt.date()}
        if sid in unique and unique[sid] != candidate:
            raise ValueError('Conflicting approved rows for the same score ID; refusing award preview')
        unique[sid] = candidate
    return list(unique.values())


def evaluate(rows, ledger, now, *, trusted_approved_feed=False):
    """Return (new_ledger, awards), never mutating the caller's ledger.

    One lifetime unlock per player per secret. Deterministic score ID evidence;
    no retroactive pre-fix credit. No browser-asserted identity or client awards.
    """
    if not trusted_approved_feed:
        raise ValueError('Caller must confirm rows are the approved iScored feed')
    if ledger.get('schema_version') != 1 or not isinstance(ledger.get('awards'), list) or not isinstance(ledger.get('verified_plays'), list):
        raise ValueError('Invalid verified ledger')
    rows = evidence(rows, now)
    by_player = defaultdict(list)
    for row in rows:
        by_player[row['player']].append(row)
    result = copy.deepcopy(ledger)
    seen = {str(a.get('id')) for a in result['awards'] if isinstance(a, dict)}
    added = []
    for player, records in sorted(by_player.items()):
        records.sort(key=lambda x:(x['submitted_at_et'], x['score_id']))
        by_day = defaultdict(list)
        for rec in records:
            by_day[rec['day']].append(rec)
        triggers = {}
        # HIGH FIVE!: five distinct game IDs on one Eastern calendar day.
        for day, items in sorted(by_day.items()):
            distinct = {}
            for rec in items:
                distinct.setdefault(rec['game_id'], rec)
            if len(distinct) >= 5:
                triggers['secret_high_five'] = max(distinct.values(), key=lambda x:x['submitted_at_et'])
                break
        # NIGHT OWL: approved score originally submitted from 00:00 to <03:00 ET.
        for rec in records:
            if rec['submitted_at_et'].hour < 3:
                triggers['secret_night_owl'] = rec
                break
        # ARCADE HOPPER: ten different games within any rolling seven Eastern days.
        for end in sorted(by_day):
            start = end - timedelta(days=6)
            window = [r for r in records if start <= r['day'] <= end]
            distinct = {}
            for rec in window:
                distinct.setdefault(rec['game_id'], rec)
            if len(distinct) >= 10:
                triggers['secret_arcade_hopper'] = max(distinct.values(), key=lambda x:x['submitted_at_et'])
                break
        for kind, rec in sorted(triggers.items()):
            award_id = kind + ':' + player
            if award_id in seen:
                continue
            award = {'id': award_id, 'event_key': 'secret:' + rec['score_id'],
                     'type': kind, 'name': NAMES[kind], 'player': player,
                     'date': rec['day'].isoformat(), 'game': rec['game'],
                     'game_id': rec['game_id'], 'score_id': rec['score_id'],
                     'original_submitted_at_et': rec['submitted_at_et'].isoformat(),
                     'verified_at': now.isoformat(),
                     'verification_method': 'postfix_approved_iscored_original_submission_time'}
            result['awards'].append(award)
            added.append(award)
            seen.add(award_id)
    result['awards'].sort(key=lambda a:(str(a.get('date','')),str(a.get('id',''))))
    return result, added
