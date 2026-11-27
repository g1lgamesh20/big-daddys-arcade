#!/usr/bin/env python3
"""Apply operator-reviewed category changes in a single GitHub Actions run."""
import json
import os
from pathlib import Path

root = Path(__file__).resolve().parents[1]
catalog = json.loads((root / 'monthly-game-catalog.json').read_text(encoding='utf-8'))['games']
path = root / 'monthly-game-labels.json'
state = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'labels': {}}
allowed = {'Arcade', 'Pinball', 'Console', 'Driving', 'Gun', 'Other', 'Uncategorized'}
changes = json.loads(os.environ['CATEGORY_CHANGES'])
if not isinstance(changes, dict) or not changes or len(changes) > 1000:
    raise SystemExit('Expected 1–1000 game ID/category assignments')
for gid, category in changes.items():
    if not isinstance(gid, str) or gid not in catalog or category not in allowed:
        raise SystemExit('Invalid game ID or category: ' + str(gid))
for gid, category in changes.items():
    existing = state['labels'].get(gid, {})
    label = existing.get('label', '')
    if not label and category == 'Uncategorized':
        state['labels'].pop(gid, None)
    else:
        state['labels'][gid] = {'label': label, 'category': category}
path.write_text(json.dumps(state, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
print('Updated categories for', len(changes), 'games')
