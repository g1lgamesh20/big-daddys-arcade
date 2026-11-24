#!/usr/bin/env python3
"""Read-only evidence preview for future Gold-history secrets; issues NO awards.

A comeback requires two observed TAKEOVERS for the same game: the player was
removed from Gold, then later rejoined Gold via a new strictly higher score.
A 24-hour observation is a candidate only, not proof of exact possession time.
"""
import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from gold_holder_history import HISTORY

def parsed(value):
    d = datetime.fromisoformat(value)
    if d.tzinfo is None:
        raise ValueError('Gold observation timestamp lacks timezone')
    return d.astimezone(timezone.utc)

def preview(history, now):
    if history.get('schema_version') != 1 or history.get('policy') != 'observed_approved_snapshots_only' or not isinstance(history.get('holders_by_game'), dict) or not isinstance(history.get('transitions'), list):
        raise ValueError('Invalid Gold history; refusing evidence preview')
    if now.tzinfo is None:
        raise ValueError('Current time lacks timezone')
    events_by_game = defaultdict(list)
    seen_ids = set()
    for e in history['transitions']:
        if not isinstance(e, dict) or not e.get('id') or e['id'] in seen_ids or e.get('type') not in ('takeover','tie_joined'):
            raise ValueError('Malformed or duplicate Gold transition')
        seen_ids.add(e['id'])
        for field in ('previous_holders','new_holders','gained_holders','lost_holders'):
            if not isinstance(e.get(field), list):
                raise ValueError('Malformed holder list')
        parsed(e['observed_at'])
        events_by_game[str(e['game_id'])].append(e)
    comebacks = []
    for gid, events in events_by_game.items():
        events.sort(key=lambda e:(parsed(e['observed_at']),e['id']))
        removed = {}
        for e in events:
            if e['type'] != 'takeover':
                continue
            for player in e['lost_holders']:
                removed[player] = e
            for player in e['gained_holders']:
                if player in removed:
                    lost = removed.pop(player)
                    comebacks.append({'player':player,'game_id':gid,'game':e['game'],
                        'lost_event_id':lost['id'],'reclaimed_event_id':e['id'],
                        'lost_observed_at':lost['observed_at'],
                        'reclaimed_observed_at':e['observed_at']})
    # Conservative 24h candidates: last known holder transition/baseline
    # must have been observed at least 24 hours ago, with no intervening
    # transition removing that holder. This does NOT prove exact possession.
    candidates = []
    for gid, entry in history['holders_by_game'].items():
        if not isinstance(entry, dict) or not isinstance(entry.get('holders'), list):
            raise ValueError('Invalid Gold holder snapshot')
        events = sorted(events_by_game.get(gid, []),
                        key=lambda e:(parsed(e['observed_at']),e['id']))
        for player in entry['holders']:
            latest = None
            for e in events:
                if player in e['gained_holders']:
                    latest = e['observed_at']
                if player in e['lost_holders']:
                    latest = None
            # Baseline is usable only if there were no transitions for
            # this game; otherwise a start cannot be safely reconstructed.
            if latest is None and not events:
                latest = entry['observed_at']
            if latest is not None and now.astimezone(timezone.utc) - parsed(latest) >= timedelta(hours=24):
                candidates.append({'player':player,'game_id':gid,'game':entry['game'],
                    'first_observed_at':latest,
                    'note':'observed_duration only; not exact record-holder duration'})
    return {'schema_version':1,'mode':'PREVIEW_ONLY_NO_AWARDS',
            'observed_transitions':len(seen_ids),
            'comeback_evidence':sorted(comebacks,key=lambda x:(x['game_id'],x['player'],x['reclaimed_event_id'])),
            'king_day_candidates':sorted(candidates,key=lambda x:(x['game_id'],x['player']))}

def main():
    history=json.loads(HISTORY.read_text(encoding='utf-8'))
    report=preview(history,datetime.now(timezone.utc))
    print('Gold history preview (NO awards or pushes):',
          report['observed_transitions'],'transitions,',
          len(report['comeback_evidence']),'comeback evidence chains,',
          len(report['king_day_candidates']),'24h observation candidates')
    for item in report['comeback_evidence'][:10]:
        print('  Comeback evidence:',item['player'],item['game'])
if __name__=='__main__':
    main()
