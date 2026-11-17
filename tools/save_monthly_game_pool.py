#!/usr/bin/env python3
"""Operator-authorized bulk replacement of monthly exclusions."""
import json, os
from pathlib import Path
root = Path(__file__).resolve().parent.parent
catalog = json.loads((root / 'monthly-game-catalog.json').read_text(encoding='utf-8'))['games']
path = root / 'monthly-game-pool.json'
state = json.loads(path.read_text(encoding='utf-8'))
raw = os.environ.get('EXCLUDED_IDS', '').strip()
ids = [v.strip() for v in raw.split(',') if v.strip()]
if len(ids) != len(set(ids)):
    raise SystemExit('Duplicate IDs in submitted list')
unknown = [v for v in ids if v not in catalog]
if unknown:
    raise SystemExit('Unknown game IDs: ' + ', '.join(unknown[:20]))
if os.environ.get('CONFIRM_REPLACE', '').lower() != 'true':
    raise SystemExit('You must confirm replacing the excluded list')
state['excluded_game_ids'] = sorted(ids)
path.write_text(json.dumps(state, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
print(f'Saved {len(ids)} exclusions of {len(catalog)} games.')
