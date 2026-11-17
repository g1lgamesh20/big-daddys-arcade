#!/usr/bin/env python3
"""Apply operator-authorized, validated game label changes (merge, not replace)."""
import json
import os
from pathlib import Path

root = Path(__file__).resolve().parents[1]
catalog = json.loads((root / 'monthly-game-catalog.json').read_text(encoding='utf-8'))['games']
path = root / 'monthly-game-labels.json'
state = json.loads(path.read_text(encoding='utf-8'))
labels = state.get('labels')
if not isinstance(labels, dict):
    raise SystemExit('Invalid labels file; nothing changed')
if os.environ.get('CONFIRM_LABELS', '').lower() != 'true':
    raise SystemExit('Confirm label changes in the GitHub workflow')
try:
    changes = json.loads(os.environ.get('LABELS_JSON', ''))
except json.JSONDecodeError as err:
    raise SystemExit('Invalid label JSON: ' + str(err))
if not isinstance(changes, list) or not 1 <= len(changes) <= 500:
    raise SystemExit('Expected 1 to 500 label changes')
categories = {'Arcade', 'Pinball', 'Console', 'Other', 'Uncategorized'}
seen = set()
for item in changes:
    if not isinstance(item, dict) or set(item) != {'id','label','category'}:
        raise SystemExit('Each change requires id, label, and category')
    gid, label, category = item['id'], item['label'], item['category']
    if not isinstance(gid,str) or gid not in catalog or gid in seen:
        raise SystemExit('Unknown or duplicate game ID')
    if not isinstance(label,str) or len(label.strip()) > 100:
        raise SystemExit('Nickname must be at most 100 characters')
    if not isinstance(category,str) or category not in categories:
        raise SystemExit('Invalid game category')
    seen.add(gid)
for item in changes:
    gid = item['id']
    label = item['label'].strip()
    category = item['category']
    if not label and category == 'Uncategorized':
        labels.pop(gid, None)
    else:
        labels[gid] = {'label': label, 'category': category}
path.write_text(json.dumps(state, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
print('Saved', len(changes), 'game labels/categories; existing exclusions unchanged')
