#!/usr/bin/env python3
"""Offline Stage 4 integration preview. Does not fetch, write or publish data.

Usage: python tools/secret_preview.py --approved-scores-file /path/to/approved.json \
       --ledger-file /path/to/verified-challenge-awards.json
Only use trusted operator-reviewed approved score export; no API calls are made.
"""
import argparse,json
from datetime import datetime,timezone
from pathlib import Path
from secret_achievements import evaluate

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--approved-scores-file',required=True)
    ap.add_argument('--ledger-file',required=True)
    args=ap.parse_args()
    raw=json.loads(Path(args.approved_scores_file).read_text())
    if not isinstance(raw,dict) or not isinstance(raw.get('scores'),list):
        raise SystemExit('FAIL CLOSED: expected iScored approved export with scores list')
    ledger=json.loads(Path(args.ledger_file).read_text())
    # A local file path alone cannot prove approval. Preview is diagnostic only.
    next_ledger,awards=evaluate(raw['scores'],ledger,datetime.now(timezone.utc),trusted_approved_feed=True)
    print(json.dumps({'mode':'PREVIEW_ONLY_NO_WRITES','approval_evidence':'OPERATOR_ATTESTATION_REQUIRED',
                      'candidate_award_count':len(awards),
                      'candidate_award_types':sorted({a['type'] for a in awards}),
                      'existing_award_count':len(ledger['awards']),
                      'proposed_award_count':len(next_ledger['awards'])},indent=2))
if __name__=='__main__':main()
