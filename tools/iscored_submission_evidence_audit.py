#!/usr/bin/env python3
"""Read-only iScored submission evidence inventory for monthly awards.

This NEVER converts a field-name guess into eligibility evidence, publishes
a player/score record, updates a trophy, or sends any push notifications.
The public iScored date has behaved like approval time in controlled tests.
Original submission timestamp semantics require iScored confirmation.
"""
import json
import os
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

URL = os.environ.get('ISCORED_READ_URL', 'https://www.iScored.info/api/G1LGAMESH/getAllScores')
OUTPUT = Path(os.environ.get('SUBMISSION_EVIDENCE_OUTPUT', 'submission-evidence-private.json'))
SENSITIVE = ('key','token','secret','password','authorization','email','photo','image','url','name','player','score','game','id','ip','device')
HINT = ('submit','creat','approv','pend','status','date','time','event','updated','modified')
KNOWN_APPROVAL_OR_AMBIGUOUS = {'date','approvedat','approved_at','approvaltime','approval_time','updatedat','updated_at','timestamp'}

def paths(value, prefix='', depth=0):
    """Collect nested schema keys only. Never retain row values."""
    if not isinstance(value,dict) or depth > 3:
        return []
    out=[]
    for key,item in value.items():
        if not isinstance(key,str):
            continue
        path = (prefix+'.' if prefix else '')+key
        out.append(path[:100])
        if isinstance(item,dict):
            out.extend(paths(item,path,depth+1))
    return out

def classify(raw):
    base=raw.lower().replace('-','').replace('_','').replace(' ','').split('.')[-1]
    if base in {x.replace('_','') for x in KNOWN_APPROVAL_OR_AMBIGUOUS}:
        return 'ambiguous_or_approval_date'
    if ('submit' in base or 'created' in base or 'create' in base) and ('date' in base or 'time' in base or 'at' in base):
        return 'possible_submission_field_UNCONFIRMED'
    if any(v in base for v in ('approv','pend','status')):
        return 'possible_approval_state_UNCONFIRMED'
    return 'other_time_or_event_field_UNCONFIRMED'

def inspect(data):
    if not isinstance(data,dict) or not isinstance(data.get('scores'),list):
        raise ValueError('iScored API did not supply scores list')
    counts=Counter()
    for item in data['scores']:
        counts.update(set(paths(item)))
    relevant=[]
    for key,seen in sorted(counts.items()):
        if any(h in key.lower() for h in HINT):
            relevant.append({'field':key,'rows_present':seen,'interpretation':classify(key)})
    candidates=[v for v in relevant if v['interpretation']=='possible_submission_field_UNCONFIRMED']
    return {
      'schema_version':1,
      'audit_type':'iScored_getAllScores_public_fields_ONLY',
      'score_rows':len(data['scores']),
      'public_field_names':sorted(counts),
      'possible_evidence_fields':relevant,
      'submission_field_candidates_unconfirmed':len(candidates),
      'original_submission_time_verified':False,
      'approval_pending_state_verified':False,
      'eligible_for_automatic_official_winner_announcement':False,
      'blocking_reason':'Public API field names alone cannot prove original score submission timestamp, timezone or approval history. Prior controlled tests suggest public date may represent approval time.',
      'next_step':'Get iScored developer confirmation of immutable original submitted-at timestamp, timezone, pending/denied and edited-score metadata or a supported audited event API.',
      'privacy':'Schema keys and aggregate counts only; no player initials, scores, game selection, score IDs, API secrets or example timestamps.',
      'no_publication_awards_or_push':True,
    }

def main():
    req=Request(URL,headers={'Accept':'application/json','User-Agent':'BigDaddysArcadeSubmissionEvidenceAudit/1.0'})
    with urlopen(req,timeout=45) as response:
        report=inspect(json.load(response))
    report['checked_at_utc']=datetime.now(timezone.utc).isoformat()
    OUTPUT.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print('iScored schema evidence audit complete, read-only.')
    print('Rows scanned:',report['score_rows'])
    print('Potential submission-time fields:',report['submission_field_candidates_unconfirmed'])
    print('Original submission evidence VERIFIED: NO (provider confirmation needed)')
    print('No participant identity, scores, mystery game, push or trophy changed.')

if __name__=='__main__':
    main()
