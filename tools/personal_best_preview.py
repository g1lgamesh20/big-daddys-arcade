#!/usr/bin/env python3
"""Read-only Personal Best evidence preview from immutable approved-score journal.

No awards, notifications, or writes. Only post-cutover entries already accepted
into the permanent journal are considered. A newer approved submission must
strictly beat every earlier accepted score for that player/game.
"""
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JOURNAL = ROOT / 'secret-score-evidence.json'
CUTOFF = datetime.fromisoformat('2026-11-20T00:00:00-05:00')

def timestamp(value):
    d = datetime.fromisoformat(value)
    if d.tzinfo is None:
        raise ValueError('Submission time must have a timezone')
    return d

def preview(journal):
    if (not isinstance(journal, dict) or journal.get('schema_version') != 1
            or journal.get('policy') != 'post_2026_11_19_approved_iscored_scores'
            or not isinstance(journal.get('scores'), dict)):
        raise ValueError('Invalid approved evidence journal')
    groups = defaultdict(list)
    for sid, row in journal['scores'].items():
        if not isinstance(row, dict) or str(row.get('score_id')) != str(sid):
            raise ValueError('Malformed score ID evidence')
        player = row.get('name')
        game = row.get('game')
        score = row.get('score')
        if (not isinstance(player, str) or not player.strip() or player != player.strip().upper()
                or not isinstance(game, str) or not game.strip()
                or type(score) is not int or score < 0):
            raise ValueError('Malformed player/game/score evidence')
        submitted = timestamp(row['date'])
        observed = timestamp(row['first_observed_at'])
        if submitted < CUTOFF or submitted > observed:
            raise ValueError('Unsafe evidence timestamps')
        groups[(player, game)].append((submitted, str(sid), score, row.get('gameName', '')))
    improvements = []
    for (player, game), records in sorted(groups.items()):
        records.sort()
        best = None
        best_id = None
        for submitted, sid, score, game_name in records:
            if best is not None and score > best:
                improvements.append({'player': player, 'game_id': game,
                    'game': game_name, 'previous_best': best, 'new_best': score,
                    'previous_score_id': best_id, 'improved_score_id': sid,
                    'submitted_at': submitted.isoformat()})
            if best is None or score > best:
                best, best_id = score, sid
    return {'mode': 'PREVIEW_ONLY_NO_AWARDS', 'approved_scores': len(journal['scores']),
            'player_game_pairs': len(groups), 'improvement_events': len(improvements),
            'players_with_improvements': len({x['player'] for x in improvements}),
            'examples': improvements[:10]}

def main():
    data = json.loads(JOURNAL.read_text(encoding='utf-8'))
    result = preview(data)
    print('Personal Best evidence preview (NO awards or pushes):',
          result['approved_scores'], 'approved scores,',
          result['improvement_events'], 'improvements,',
          result['players_with_improvements'], 'players')
    for item in result['examples']:
        print('  ', item['player'], item['game'], item['previous_best'],
              '->', item['new_best'], '(score IDs', item['previous_score_id'],
              '->', item['improved_score_id'] + ')')

if __name__ == '__main__':
    main()
