#!/usr/bin/env python3
"""Golden Encore: permanent trophies for improving an already-held Gold score.

Uses successive approved iScored public score snapshots. Never counts a first
Gold, a tie, a lower score, a different player's takeover, or a previously
observed score ID. No OneSignal push is sent by this module.
"""
import json
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / 'golden-encore-state.json'
AWARDS = ROOT / 'verified-challenge-awards.json'
NY = ZoneInfo('America/New_York')
MILESTONES = ((1, 'Golden Encore'), (5, 'Gold Rush'), (10, 'Untouchable'))


def snapshot(rows):
    """Best approved score per player/game, then all tied Gold holders."""
    per_game = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        player = str(row.get('name') or '').strip().upper()[:48]
        game_id = str(row.get('game') or '').strip()
        score_id = str(row.get('id') or '').strip()
        game = str(row.get('gameName') or '').strip()[:100]
        raw = row.get('score')
        if not player or not game_id or not score_id or not game or isinstance(raw, bool):
            continue
        try:
            score = int(raw)
        except (TypeError, ValueError):
            continue
        if score < 0:
            continue
        group = per_game.setdefault(game_id, {})
        prev = group.get(player)
        candidate = {'player': player, 'score': score, 'score_id': score_id, 'game': game}
        if prev is None or score > prev['score'] or (
                score == prev['score'] and score_id > prev['score_id']):
            group[player] = candidate
    champions = {}
    for game_id, group in per_game.items():
        maximum = max(entry['score'] for entry in group.values())
        winners = [entry for entry in group.values() if entry['score'] == maximum]
        champions[game_id] = {
            'score': maximum,
            'holders': sorted(entry['player'] for entry in winners),
            'game': winners[0]['game'],
            'winning_scores': sorted(winners, key=lambda e: e['player']),
        }
    return champions


def evaluate(rows, old_state, known_score_ids, ledger, now):
    """Return new state/ledger and events, without mutating input data."""
    if ledger.get('schema_version') != 1 or not isinstance(ledger.get('awards'), list) or not isinstance(ledger.get('verified_plays'), list):
        raise ValueError('Invalid official award ledger; refusing Golden Encore update')
    current = snapshot(rows)
    # On the first run, quietly capture the current Gold holders. We do not
    # reverse-engineer old Gold improvements from API approval timestamps.
    if old_state is None:
        return {'schema_version': 1, 'gold_by_game': current, 'improvements': []}, ledger, []
    if old_state.get('schema_version') != 1 or not isinstance(old_state.get('gold_by_game'), dict) or not isinstance(old_state.get('improvements'), list):
        raise ValueError('Invalid Golden Encore state; refusing reset or backfill')
    saved = json.loads(json.dumps(old_state))
    updated_ledger = json.loads(json.dumps(ledger))
    known = {str(x) for x in known_score_ids}
    historical_ids = {str(e.get('score_id')) for e in saved['improvements'] if isinstance(e, dict)}
    seen_awards = {str(a.get('id')) for a in updated_ledger['awards'] if isinstance(a, dict)}
    earned = []
    # Track games absent from a feed snapshot. Their first reappearance is a
    # recovery baseline, not evidence of a newly earned Gold improvement.
    missing = set(saved.get('missing_games', []))
    missing.update(set(saved['gold_by_game']) - set(current))
    for game_id, winner in sorted(current.items()):
        previous = saved['gold_by_game'].get(game_id)
        recovering = game_id in missing
        if previous and type(previous.get('score')) is int and winner['score'] < previous['score']:
            # A lower Gold can reflect a deleted score or a truncated feed.
            # Preserve the trusted high-water mark. A truncated feed must not
            # lower the threshold for a later, false improvement trophy.
            missing.add(game_id)
            continue
        if not recovering and previous and type(previous.get('score')) is int and winner['score'] > previous['score']:
            old_holders = set(previous.get('holders', []))
            for entry in winner['winning_scores']:
                player = entry['player']
                score_id = entry['score_id']
                # Must have held Gold BEFORE this newly approved score appeared.
                if player not in old_holders or score_id in known or score_id in historical_ids:
                    continue
                event = {
                    'id': 'gold_improvement:' + score_id,
                    'player': player, 'game': entry['game'], 'game_id': game_id,
                    'score_id': score_id, 'previous_gold_score': previous['score'],
                    'improved_gold_score': entry['score'],
                    'recorded_at': now.isoformat(),
                }
                saved['improvements'].append(event)
                historical_ids.add(score_id)
                earned.append(event)
                count = sum(1 for item in saved['improvements']
                            if item.get('player') == player)
                for threshold, name in MILESTONES:
                    award_id = f'golden_encore:{player}:{threshold}'
                    if count < threshold or award_id in seen_awards:
                        continue
                    updated_ledger['awards'].append({
                        'id': award_id, 'event_key': event['id'],
                        'type': 'golden_encore_milestone', 'name': name,
                        'date': now.astimezone(NY).date().isoformat(),
                        'player': player, 'game': entry['game'], 'game_id': game_id,
                        'score_id': score_id, 'score': entry['score'],
                        'milestone': threshold, 'gold_improvements': count,
                        'verified_at': now.isoformat(),
                        'verification_method': 'approved_iscored_new_id_improved_existing_gold',
                    })
                    seen_awards.add(award_id)
        # Update observed Gold only after evaluating the prior snapshot.
        saved['gold_by_game'][game_id] = winner
        missing.discard(game_id)
    saved['missing_games'] = sorted(missing)
    updated_ledger['awards'].sort(key=lambda a: (str(a.get('date', '')), str(a.get('id', ''))))
    return saved, updated_ledger, earned


def sync(rows, known_score_ids, now=None):
    now = now or datetime.now(timezone.utc)
    old_state = json.loads(STATE.read_text(encoding='utf-8')) if STATE.exists() else None
    ledger = json.loads(AWARDS.read_text(encoding='utf-8'))
    state, updated, events = evaluate(rows, old_state, known_score_ids, ledger, now)
    if state != old_state:
        STATE.write_text(json.dumps(state, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    if updated != ledger:
        AWARDS.write_text(json.dumps(updated, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print('Golden Encore: newly verified Gold improvements:', len(events))
    return events
