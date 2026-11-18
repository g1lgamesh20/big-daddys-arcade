#!/usr/bin/env python3
"""Read-only Daily participation audit: NEVER infer original submission time.

The public iScored score date tracks APPROVAL time in controlled Nov 2026 tests.
Matching a public score to a selected Daily game only creates an UNVERIFIED
candidate; it cannot grant participation, trophy, points or push notifications.
"""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from thursday_challenge import fetch, parse_time

ROOT=Path(__file__).resolve().parents[1]
HISTORY=ROOT/'daily-champion-history.json'
RECENT=ROOT/'daily-champion.json'
LEDGER=ROOT/'verified-challenge-awards.json'
OUT=ROOT/'daily-participation-audit.json'
NY=ZoneInfo('America/New_York')

def selections(history, recent):
    result={}
    for source in (history, recent):
        for entry in source.get('days',[]):
            if not isinstance(entry,dict): continue
            day=entry.get('date')
            game_id=str(entry.get('game_id') or '')
            if not isinstance(day,str) or not game_id: continue
            try:datetime.strptime(day,'%Y-%m-%d')
            except ValueError:continue
            if day in result and result[day]['game_id']!=game_id:
                raise ValueError('Daily selection conflict: '+day)
            result[day]={'game_id':game_id,'game':str(entry.get('game') or '')}
    return result

def audit(rows, selections_by_date, ledger, now=None):
    """Review queue only: selected game + public approval is NOT event proof."""
    now=now or datetime.now(timezone.utc)
    if ledger.get('schema_version')!=1 or not isinstance(ledger.get('verified_plays'),list):
        raise ValueError('Invalid permanent verified ledger')
    verified={(str(p.get('player','')).strip().upper(),p.get('date'))
        for p in ledger['verified_plays'] if isinstance(p,dict) and p.get('kind')=='daily'}
    seen=set()
    candidates=[]
    for row in rows:
        if not isinstance(row,dict):continue
        score_id=str(row.get('id') or '').strip()
        player=str(row.get('name') or '').strip().upper()
        game_id=str(row.get('game') or '').strip()
        if not score_id or not player or not game_id or score_id in seen:continue
        seen.add(score_id)
        try:
            if isinstance(row.get('score'),bool):continue
            score=int(row.get('score'))
        except (TypeError,ValueError):continue
        if score<0:continue
        approval=parse_time(row.get('date'))
        if not approval:continue
        # The API date is not a trusted submission date; use a conservative
        # *candidate discovery* window only. Unknown older submission is possible.
        approval_day=approval.astimezone(NY).date()
        for day,selection in selections_by_date.items():
            if game_id!=selection['game_id'] or (player,day) in verified:continue
            challenge_day=datetime.strptime(day,'%Y-%m-%d').date()
            # Check same-day approvals and next-day approvals; allow one-day
            # skew caused by observed iScored date offset at local midnight.
            if not challenge_day<=approval_day<=challenge_day+timedelta(days=2):
                continue
            candidates.append({
                'date':day,'player':player,'game':selection['game'],
                'game_id':game_id,'score_id':score_id,'score':score,
                'api_approval_date_raw':str(row.get('date')),
                'status':'NEEDS_ORIGINAL_SUBMISSION_TIME',
                'verified':False,'eligible_for_trophy':False,
            })
    candidates.sort(key=lambda c:(c['date'],c['player'],c['score_id']),reverse=True)
    return {
        'schema_version':1,'generated_at':now.isoformat(),
        'mode':'READ_ONLY_NO_AWARDS',
        'warning':'Public iScored date reflects approval time, NOT reliable original submission time. This report is a POSSIBLE MATCH queue only.',
        'possible_matches':len(candidates),
        'automatic_verified_plays_added':0,'trophies_issued':0,'pushes_sent':0,
        'candidates':candidates
    }

def main():
    history=json.loads(HISTORY.read_text(encoding='utf-8'))
    recent=json.loads(RECENT.read_text(encoding='utf-8'))
    ledger=json.loads(LEDGER.read_text(encoding='utf-8'))
    selected=selections(history,recent)
    report=audit(fetch(),selected,ledger)
    OUT.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print('Possible Daily participation matches (unverified):',report['possible_matches'])
    print('NO verified play credits, trophy awards or notifications issued.')
    print('Original iScored submission timestamps remain the release blocker.')

if __name__=='__main__':main()
