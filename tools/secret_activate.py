#!/usr/bin/env python3
"""Stage 4 controlled award activation, default OFF.

Uses the durable approved-score journal, never the client or raw unverified input.
Operator must explicitly set STAGE4_AWARDS_ENABLED=1. No notifications.
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from secret_evidence_journal import JOURNAL, LEDGER, preview
from secret_achievements import evaluate

def activate(journal, ledger, now, *, enabled=False):
    if not enabled:
        return ledger, []
    if journal.get('schema_version') != 1 or not isinstance(journal.get('scores'), dict):
        raise ValueError('Invalid evidence journal')
    rows=[]
    for sid, item in journal['scores'].items():
        if not isinstance(item,dict) or str(item.get('score_id')) != str(sid):
            raise ValueError('Invalid journal entry')
        rows.append({'id':sid,'name':item['name'],'game':item['game'],
                     'gameName':item.get('gameName',''),'score':item['score'],'date':item['date']})
    return evaluate(rows, ledger, now, trusted_approved_feed=True)

def main():
    if os.environ.get('STAGE4_AWARDS_ENABLED') != '1':
        print('Stage 4 activation OFF; no changes')
        return
    journal=json.loads(JOURNAL.read_text(encoding='utf-8'))
    ledger=json.loads(LEDGER.read_text(encoding='utf-8'))
    updated,awards=activate(journal,ledger,datetime.now(timezone.utc),enabled=True)
    if awards:
        # Atomic replacement; existing awards retained by evaluator.
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=LEDGER.parent,
                                         prefix='.stage4-',suffix='.json',delete=False) as tmp:
            json.dump(updated,tmp,indent=2,ensure_ascii=False)
            tmp.write('\n')
            tmp_path=Path(tmp.name)
        tmp_path.replace(LEDGER)
    print('Stage 4 awards added:',len(awards),'(no notifications)')

if __name__=='__main__':
    main()
