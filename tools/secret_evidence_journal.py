#!/usr/bin/env python3
"""Append-only approved iScored evidence journal, fail closed on conflicts.

No notifications and no awards. The existing iScored public feed is considered
approved by the application contract, not a cryptographically signed attestation.
"""
import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from secret_achievements import evidence, evaluate

ROOT = Path(__file__).resolve().parents[1]
JOURNAL = ROOT / 'secret-score-evidence.json'
PREVIEW = ROOT / 'secret-achievement-preview.json'
LEDGER = ROOT / 'verified-challenge-awards.json'


def empty():
    return {'schema_version': 1, 'policy': 'post_2026_11_19_approved_iscored_scores', 'scores': {}}


def merge(previous, rows, now):
    if not isinstance(previous, dict) or previous.get('schema_version') != 1 or not isinstance(previous.get('scores'), dict):
        raise ValueError('Invalid journal; refusing reset')
    incoming = evidence(rows, now)
    result = copy.deepcopy(previous)
    added = 0
    for rec in incoming:
        sid = rec['score_id']
        item = {'score_id': sid, 'name': rec['player'], 'game': rec['game_id'],
                'gameName': rec['game'], 'score': rec['score'], 'date': rec['submitted_at_et'].isoformat(),
                'first_observed_at': now.isoformat()}
        old = result['scores'].get(sid)
        if old is not None:
            # Metadata can change, but player, game and original timestamp cannot.
            for key in ('score_id', 'name', 'game', 'score', 'date'):
                if old.get(key) != item[key]:
                    raise ValueError(f'Immutable evidence conflict for score ID {sid} ({key})')
        else:
            result['scores'][sid] = item
            added += 1
    return result, added


def preview(journal, ledger, now):
    if not isinstance(journal.get('scores'), dict):
        raise ValueError('Missing score journal')
    # Stored journal rows are evidence, not direct proof of an award; run the
    # same offline evaluator and NEVER write the proposed ledger in preview.
    rows = [{'id': sid, 'name': r['name'], 'game': r['game'],
             'gameName': r.get('gameName', ''), 'date': r['date'], 'score': r['score']}
            for sid, r in journal['scores'].items()]
    _, proposed = evaluate(rows, ledger, now, trusted_approved_feed=True)
    return {'schema_version': 1, 'mode': 'preview_only',
            'generated_at': now.isoformat(), 'journal_entries': len(rows),
            'potential_new_awards': len(proposed),
            'proposed': [{'id': a['id'], 'score_id': a['score_id'], 'player': a['player']}
                         for a in proposed],
            'warning': 'Preview is not an award. Verify feed completeness and timestamps before activation.'}


def main():
    # Fetch once in the scheduled workflow, using the same bounded retry helper
    # as the existing scoreboard. This independent process cannot edit awards.
    from urllib.request import Request, urlopen
    import os
    from iscored_fetch_retry import read_scores
    url = os.environ.get('ISCORED_READ_URL', 'https://www.iScored.info/api/G1LGAMESH/getAllScores')
    raw = read_scores(Request(url, headers={'User-Agent':'BigDaddysArcadeSecretJournal/1.0',
                                           'Accept':'application/json'}), opener=urlopen)
    if not isinstance(raw, dict) or not isinstance(raw.get('scores'), list):
        raise ValueError('Unexpected approved score feed')
    if not JOURNAL.exists():
        raise RuntimeError('Journal baseline missing: deploy seeded empty journal file before first run')
    if not LEDGER.exists():
        raise RuntimeError('Permanent achievement ledger missing')
    now = datetime.now(timezone.utc)
    old = json.loads(JOURNAL.read_text(encoding='utf-8'))
    next_state, added = merge(old, raw['scores'], now)
    ledger = json.loads(LEDGER.read_text(encoding='utf-8'))
    report = preview(next_state, ledger, now)
    # Both computations succeed before either file changes.
    JOURNAL.write_text(json.dumps(next_state, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    PREVIEW.write_text(json.dumps(report, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    print('Secret evidence journal:', added, 'new approved IDs; preview:', report['potential_new_awards'])
    print('NO SECRET AWARDS OR NOTIFICATIONS ISSUED')

if __name__ == '__main__':
    main()
