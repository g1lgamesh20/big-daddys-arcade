#!/usr/bin/env python3
"""Update public eligibility exclusions only. No game selection, scores or awards."""
import json,os
from pathlib import Path
root=Path(__file__).resolve().parent.parent
catalog=json.loads((root/'monthly-game-catalog.json').read_text())['games']
path=root/'monthly-game-pool.json'
pool=json.loads(path.read_text())
action=os.environ.get('POOL_ACTION','')
gid=os.environ.get('GAME_ID','').strip()
if action not in ('exclude','include') or gid not in catalog:
    raise SystemExit('Choose include/exclude and a valid iScored game ID')
excluded=set(pool['excluded_game_ids'])
if action=='exclude': excluded.add(gid)
else: excluded.discard(gid)
pool['excluded_game_ids']=sorted(excluded)
path.write_text(json.dumps(pool,indent=2)+'\\n')
print(f'{action}: {catalog[gid]} (ID {gid}); excluded total: {len(excluded)}')
