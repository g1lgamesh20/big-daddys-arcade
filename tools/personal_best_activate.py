#!/usr/bin/env python3
"""Controlled, idempotent Personal Best milestone awards. Default OFF; no pushes."""
import copy
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from personal_best_preview import preview, JOURNAL, ROOT

LEDGER = ROOT / 'verified-challenge-awards.json'

def activate(journal, ledger, now, *, enabled=False):
    if not enabled:
        return copy.deepcopy(ledger), []
    if now.tzinfo is None:
        raise ValueError('Activation time must be timezone-aware')
    if (not isinstance(ledger, dict) or ledger.get('schema_version') != 1
            or not isinstance(ledger.get('awards'), list)
            or not isinstance(ledger.get('verified_plays'), list)):
        raise ValueError('Invalid permanent award ledger')
    candidates = preview(journal)['milestones']
    result = copy.deepcopy(ledger)
    seen = set()
    for existing in result['awards']:
        if not isinstance(existing, dict) or not isinstance(existing.get('id'), str):
            raise ValueError('Malformed existing award')
        if existing['id'] in seen:
            raise ValueError('Duplicate existing award ID')
        seen.add(existing['id'])
    added = []
    for item in candidates:
        if item['id'] in seen:
            continue
        award = {'id': item['id'], 'event_key': 'personal_best:' + item['qualifying_score_id'],
                 'type': 'personal_best_milestone', 'name': item['name'],
                 'player': item['player'], 'date': item['unlocked_at'][:10],
                 'game': 'Personal Best Challenge', 'milestone': item['milestone'],
                 'score_id': item['qualifying_score_id'],
                 'original_submitted_at_et': item['unlocked_at'],
                 'verified_at': now.isoformat(),
                 'verification_method': 'postcutover_approved_iscored_personal_best_evidence'}
        result['awards'].append(award)
        added.append(award)
        seen.add(item['id'])
    result['awards'].sort(key=lambda a:(str(a.get('date','')), str(a.get('id',''))))
    return result, added

def main():
    if os.environ.get('PERSONAL_BEST_AWARDS_ENABLED') != '1':
        print('Personal Best activation OFF; no changes or notifications')
        return
    journal = json.loads(JOURNAL.read_text(encoding='utf-8'))
    ledger = json.loads(LEDGER.read_text(encoding='utf-8'))
    updated, awards = activate(journal, ledger, datetime.now(timezone.utc), enabled=True)
    if awards:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=LEDGER.parent,
                prefix='.personal-best-', suffix='.json', delete=False) as tmp:
            json.dump(updated, tmp, indent=2, ensure_ascii=False)
            tmp.write('\n')
            path = Path(tmp.name)
        path.replace(LEDGER)
    print('Personal Best milestones awarded:', len(awards), '(NO notifications)')

if __name__ == '__main__':
    main()
