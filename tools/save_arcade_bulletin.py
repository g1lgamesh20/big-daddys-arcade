#!/usr/bin/env python3
"""Archive an operator-authored bulletin from an authenticated GitHub workflow."""
import datetime,json,os,uuid
from pathlib import Path
p=Path(__file__).resolve().parent.parent/'arcade-news.json'
title=os.environ.get('ANNOUNCEMENT_TITLE','').strip()
message=os.environ.get('ANNOUNCEMENT_MESSAGE','').strip()
if not title or len(title)>80 or not message or len(message)>240: raise SystemExit('Title (1-80) and message (1-240) required')
data=json.loads(p.read_text())
items=data.get('bulletins',[])
items.insert(0,{'id':str(uuid.uuid4()),'title':title,'message':message,'created_at':datetime.datetime.now(datetime.timezone.utc).isoformat()})
p.write_text(json.dumps({'bulletins':items[:100]},ensure_ascii=False,indent=2)+'\n')
