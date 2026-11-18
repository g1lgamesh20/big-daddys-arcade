#!/usr/bin/env python3
"""Read-only iScored approval visibility test; no writes, trophy or push actions."""
import json
from urllib.request import Request, urlopen

URL = 'https://www.iScored.info/api/G1LGAMESH/getAllScores'
TARGETS = [
    ('DON', '720 Degrees', 2020, 'PENDING'),
    ('DON', 'Strider', 17200, 'PENDING'),
    ('VJG', 'Tempest Tubes', 15378, 'PENDING - may be edited'),
    ('VJG', 'Crystal Castles', 160125, 'PENDING - may be denied'),
    ('VJG', 'Major Havoc', 26003, 'APPROVED'),
]

def main():
    req = Request(URL, headers={'Accept': 'application/json', 'User-Agent': 'BigDaddysArcadeReadOnlyApprovalCheck/1.1'})
    with urlopen(req, timeout=40) as response:
        raw = json.load(response)
    rows = raw.get('scores') if isinstance(raw, dict) else None
    if not isinstance(rows, list):
        raise ValueError('Public iScored API missing scores array')
    print('Public API returned', len(rows), 'score entries')
    for player, game, score, status in TARGETS:
        matches = []
        same_game_player = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            name = str(row.get('name') or '').strip().upper()
            game_name = str(row.get('gameName') or '').strip()
            if name != player or game_name.casefold() != game.casefold():
                continue
            try:
                value = int(row.get('score'))
            except (TypeError, ValueError):
                continue
            summary = {'player': name, 'game': game_name, 'score': value,
                       'submission_date_raw': str(row.get('date') or ''),
                       'score_id': str(row.get('id') or ''),
                       'game_id': str(row.get('game') or '')}
            same_game_player.append(summary)
            if value == score:
                matches.append(summary)
        print(f'CHECK [{status}]: {player} / {game} / {score:,}')
        print('  Exact public matches:', json.dumps(matches, ensure_ascii=False))
        if not matches:
            print('  Other public scores for this player/game:', json.dumps(same_game_player, ensure_ascii=False))
            print('  Absence from API alone does not prove pending/denied status.')
    print('READ-ONLY COMPLETE. No score, approval, trophy, or push changes.')

if __name__ == '__main__':
    main()
