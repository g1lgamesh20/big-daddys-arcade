#!/usr/bin/env python3
"""Save operator-assigned game labels and categories; IDs are stable."""
import json,os
from pathlib import Path
root=Path(__file__).resolve().parents[1]
catalog=json.loads((root/'monthly-game-catalog.json').read_text())['games']
path=root/'monthly-game-labels.json'
state=json.loads(path.read_text()) if path.exists() else {'labels':{}}
gid=os.environ.get('GAME_ID','').strip()
label=os.environ.get('DISPLAY_LABEL','').strip()
category=os.environ.get('GAME_CATEGORY','Uncategorized').strip()
if gid not in catalog:raise SystemExit('Unknown game ID')
if category not in ('Arcade','Pinball','Console','Other','Uncategorized'):raise SystemExit('Invalid category')
if len(label)>100:raise SystemExit('Label too long')
if not label and category=='Uncategorized':state['labels'].pop(gid,None)
else:state['labels'][gid]={'label':label,'category':category}
path.write_text(json.dumps(state,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print('Saved metadata for game ID',gid)
