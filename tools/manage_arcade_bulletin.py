#!/usr/bin/env python3
"""Edit/delete existing bulletins via authenticated GitHub Actions. Never sends push."""
import json
import os
from pathlib import Path

path = Path(__file__).resolve().parent.parent / 'arcade-news.json'
data = json.loads(path.read_text(encoding='utf-8'))
items = data.get('bulletins')
if not isinstance(items, list):
    raise SystemExit('Invalid bulletin archive: bulletins must be a list')
action = os.environ.get('BULLETIN_ACTION', '').strip()
bulletin_id = os.environ.get('BULLETIN_ID', '').strip()
matches = [i for i, item in enumerate(items) if item.get('id') == bulletin_id]
if not bulletin_id or len(matches) != 1:
    raise SystemExit('Bulletin ID not found or not unique; nothing changed')
index = matches[0]
if action == 'edit':
    title = os.environ.get('BULLETIN_TITLE', '').strip()
    message = os.environ.get('BULLETIN_MESSAGE', '').strip()
    if not (1 <= len(title) <= 80 and 1 <= len(message) <= 240):
        raise SystemExit('Editing requires both a title (1-80) and message (1-240); nothing changed')
    items[index]['title'] = title
    items[index]['message'] = message
elif action == 'delete':
    if os.environ.get('CONFIRM_DELETE', '').lower() != 'true':
        raise SystemExit('Delete confirmation required; nothing changed')
    items.pop(index)
else:
    raise SystemExit('Unknown action; nothing changed')
path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(f'{action} completed for bulletin {bulletin_id}')
