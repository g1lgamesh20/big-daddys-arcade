#!/usr/bin/env python3
"""Read-only Stage 4 live iScored contract audit. Never writes files or issues awards."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from iscored_fetch_retry import read_scores
from secret_evidence_journal import merge, preview

ROOT = Path(__file__).resolve().parents[1]
URL = 'https://www.iScored.info/api/G1LGAMESH/getAllScores'

def main():
    raw = read_scores(Request(URL, headers={
        'User-Agent': 'BigDaddysArcadeStage4ReadOnlyAudit/1.0',
        'Accept': 'application/json'}), opener=urlopen)
    journal = json.loads((ROOT / 'secret-score-evidence.json').read_text(encoding='utf-8'))
    ledger = json.loads((ROOT / 'verified-challenge-awards.json').read_text(encoding='utf-8'))
    now = datetime.now(timezone.utc)
    updated, added = merge(journal, raw['scores'], now)
    result = preview(updated, ledger, now)
    # Only aggregate diagnostics: do not print player names, score IDs, or submissions.
    kinds = {}
    for a in result['proposed']:
        kind = a['id'].split(':', 1)[0]
        kinds[kind] = kinds.get(kind, 0) + 1
    print(json.dumps({
        'mode': 'READ_ONLY_LIVE_AUDIT',
        'raw_approved_feed_rows': len(raw['scores']),
        'new_eligible_score_ids': added,
        'journal_entries_after_in_memory_merge': result['journal_entries'],
        'potential_awards_by_type': kinds,
        'writes': False, 'notifications': False, 'awards_issued': False
    }, indent=2, sort_keys=True))

if __name__ == '__main__':
    main()
