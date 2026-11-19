#!/usr/bin/env python3
"""Import iScored GameID/GameLogo settings JSON without retaining private settings.

Usage: python tools/import_game_logos.py /path/to/iscored-games.json
The source should be a JSON list of game objects from the iScored Games
metadata response. Only GameID and GameLogo are used. It is never committed.
This importer safely merges into game-logo-map.json; unmentioned IDs remain.
"""
import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'game-logo-map.json'
ID = re.compile(r'[0-9]{1,12}\Z')
LOGO = re.compile(r'/(?:community/)?images/games/game[0-9]{1,12}\Z')

def rows_from(payload):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        if 'GameID' in payload:
            return [payload]
        for key in ('games', 'Games', 'rows', 'data', 'result'):
            nested = payload.get(key)
            if isinstance(nested, list):
                return nested
    raise ValueError('Expected an iScored game settings array or supported game list wrapper')

def merge(mapping, records, expected_room=1118):
    if not isinstance(mapping, dict):
        raise ValueError('Existing logo map is not an object')
    result = dict(mapping)
    seen = {}
    changed = 0
    unchanged = 0
    blank = 0
    invalid = 0
    wrong_room = 0
    for row in records:
        if not isinstance(row, dict):
            invalid += 1
            continue
        game_id = str(row.get('GameID', '')).strip()
        logo = row.get('GameLogo')
        room = row.get('RoomID')
        if room is not None and (str(room).strip() != str(expected_room)):
            wrong_room += 1
            continue
        if not ID.fullmatch(game_id):
            invalid += 1
            continue
        if logo is None or logo == '':
            blank += 1
            continue
        if not isinstance(logo, str) or not LOGO.fullmatch(logo):
            invalid += 1
            continue
        if game_id in seen and seen[game_id] != logo:
            raise ValueError('Conflicting logo paths for game '+game_id)
        seen[game_id] = logo
        if result.get(game_id) == logo:
            unchanged += 1
        else:
            result[game_id] = logo
            changed += 1
    if not seen:
        raise ValueError('No valid game-logo records found; refusing to alter map')
    ordered = dict(sorted(result.items(), key=lambda item: int(item[0])))
    return ordered, {
        'records': len(records), 'valid_games': len(seen), 'changed': changed,
        'unchanged': unchanged, 'missing_logo': blank,
        'invalid': invalid, 'other_room': wrong_room, 'total_mapped': len(ordered)
    }

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path, help='Local JSON export; never commit this file')
    parser.add_argument('--map', type=Path, default=DEST, help='Output map file')
    parser.add_argument('--room', type=int, default=1118, help='Expected iScored RoomID')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    raw = json.loads(args.source.read_text(encoding='utf-8'))
    current = json.loads(args.map.read_text(encoding='utf-8'))
    updated, report = merge(current, rows_from(raw), expected_room=args.room)
    print(json.dumps(report, indent=2))
    if not args.dry_run and updated != current:
        args.map.write_text(json.dumps(updated, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
        print('Updated:', args.map)
    elif args.dry_run:
        print('Dry run: did not write the map.')
    else:
        print('No logo mapping changes.')

if __name__ == '__main__':
    main()
