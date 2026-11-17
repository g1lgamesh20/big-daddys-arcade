#!/usr/bin/env python3
"""Maintain game catalog from iScored score feed; preserve names, exclusions, operator metadata."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CATALOG=ROOT/'monthly-game-catalog.json'
def sync_games(rows):
    existing=json.loads(CATALOG.read_text(encoding='utf-8'))
    games=existing.get('games')
    if not isinstance(games,dict):raise ValueError('Invalid game catalog')
    found={}
    for row in rows:
        if not isinstance(row,dict):continue
        gid=row.get('game')
        name=str(row.get('gameName') or '').strip()[:100]
        if gid is None or not name:continue
        found[str(gid)]=name
    if not found:raise ValueError('No games in iScored feed; refusing catalog update')
    added=0
    for gid,name in found.items():
        if gid not in games:games[gid]=name;added+=1
    # Do not remove existing IDs: no-score games may be absent from the score feed.
    # Never modify exclusions or operator aliases.
    if added:
        CATALOG.write_text(json.dumps(existing,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'Catalog sync: {added} new game IDs; {len(games)} total; {len(found)} present in feed')
    return added
