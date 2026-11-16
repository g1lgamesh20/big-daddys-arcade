#!/usr/bin/env python3
"""Mark all currently visible medals as previously handled; never send a push."""
import json
from datetime import datetime, timezone
from pathlib import Path
root = Path(__file__).resolve().parents[1]
feed = json.loads((root/'medals.json').read_text(encoding='utf-8'))
state_path = root/'medal-notification-state.json'
state = json.loads(state_path.read_text(encoding='utf-8')) if state_path.exists() else {}
ids = set(map(str,state.get('sent_ids',[])))
new = {str(a['id']) for a in feed.get('alerts',[]) if isinstance(a,dict) and a.get('id') is not None}
ids |= new
state_path.write_text(json.dumps({'sent_ids':sorted(ids),'updated_at':datetime.now(timezone.utc).isoformat()},indent=2)+'\n',encoding='utf-8')
print(f'Baselined {len(new)} currently visible medals; total recorded IDs {len(ids)}; zero push notifications sent.')
