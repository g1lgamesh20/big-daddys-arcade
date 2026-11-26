#!/usr/bin/env python3
"""Append-only observed Gold holder transitions. No trophy or push issuance.

A first observation is a baseline, never a historical takeover. Events describe
changes between approved iScored snapshots, not exact real-world change times.
"""
import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from golden_encore import snapshot

ROOT = Path(__file__).resolve().parents[1]
HISTORY = ROOT / 'gold-holder-history.json'

def initial():
    return {'schema_version': 1, 'policy': 'observed_approved_snapshots_only',
            'holders_by_game': {}, 'transitions': []}

def evaluate(rows, previous, known_ids, now):
    if now.tzinfo is None:
        raise ValueError('Observation time must be timezone-aware')
    if previous is not None and (previous.get('schema_version') != 1 or
        previous.get('policy') != 'observed_approved_snapshots_only' or
        not isinstance(previous.get('holders_by_game'), dict) or
        not isinstance(previous.get('transitions'), list)):
        raise ValueError('Invalid permanent Gold history; refusing reset')
    current = snapshot(rows)
    if not current:
        raise ValueError('Empty approved score snapshot; refusing Gold history update')
    state = copy.deepcopy(previous) if previous is not None else initial()
    known = {str(x) for x in known_ids}
    feed_ids = {str(r.get('id')) for r in rows if isinstance(r, dict) and r.get('id') is not None}
    seen = {e.get('id') for e in state['transitions']}
    events = []
    observed_at = now.astimezone(timezone.utc).isoformat()
    for gid, champion in sorted(current.items()):
        old = state['holders_by_game'].get(gid)
        new = {'score': champion['score'], 'holders': champion['holders'],
               'winning_scores': champion['winning_scores'],
               'game': champion['game'], 'observed_at': observed_at,
               'last_confirmed_at': observed_at}
        if old is None:
            state['holders_by_game'][gid] = new
            continue
        if (not isinstance(old.get('score'), int) or
            not isinstance(old.get('holders'), list) or
            not isinstance(old.get('winning_scores'), list)):
            raise ValueError('Invalid Gold baseline for game '+gid)
        # A missing former winning score may indicate a deleted/unapproved row,
        # not a real takeover. Preserve the last trusted observation.
        former_ids = {str(x.get('score_id')) for x in old['winning_scores']}
        if not former_ids.issubset(feed_ids):
            continue
        if champion['score'] < old['score']:
            continue
        if champion['score'] == old['score'] and champion['holders'] == old['holders']:
            old['last_confirmed_at'] = observed_at
            continue
        # Never interpret already-known scores as new holder changes.
        new_winners = [w for w in champion['winning_scores']
                       if str(w['score_id']) not in known]
        if not new_winners:
            continue
        old_holders = set(old['holders'])
        gained = sorted(set(champion['holders']) - old_holders)
        lost = sorted(old_holders - set(champion['holders']))
        if not gained and not lost:
            # Existing holder improved their Gold; Golden Encore owns awards.
            state['holders_by_game'][gid] = new
            continue
        event_type = 'takeover' if champion['score'] > old['score'] else 'tie_joined'
        ids = sorted(str(w['score_id']) for w in new_winners)
        event_id = 'gold_transition:' + gid + ':' + ':'.join(ids)
        if event_id not in seen:
            event = {'id': event_id, 'game_id': gid, 'game': champion['game'],
                     'type': event_type, 'previous_holders': sorted(old_holders),
                     'new_holders': list(champion['holders']),
                     'gained_holders': gained, 'lost_holders': lost,
                     'previous_score': old['score'], 'new_score': champion['score'],
                     'new_score_ids': ids, 'previous_observed_at': old['observed_at'],
                     'observed_at': observed_at,
                     'time_policy': 'observed_between_refreshes_not_exact_takeover_time'}
            state['transitions'].append(event)
            events.append(event)
            seen.add(event_id)
        state['holders_by_game'][gid] = new
    return state, events

def sync(rows, known_ids, now=None):
    now = now or datetime.now(timezone.utc)
    prior = json.loads(HISTORY.read_text(encoding='utf-8')) if HISTORY.exists() else None
    updated, events = evaluate(rows, prior, known_ids, now)
    if updated != prior:
        HISTORY.write_text(json.dumps(updated, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    print('Gold holder history:', len(events), 'new observed transitions (no awards/push)')
    return events
