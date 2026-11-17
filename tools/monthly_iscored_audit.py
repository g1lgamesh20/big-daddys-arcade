#!/usr/bin/env python3
"""Read-only iScored monthly integration audit. No publishing, awards or push."""
import json, os, re, sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
from thursday_challenge import parse_time

URL=os.environ.get('ISCORED_READ_URL','https://www.iScored.info/api/G1LGAMESH/getAllScores')
NY=ZoneInfo('America/New_York')
def audit(data, month):
    if not isinstance(data,dict) or not isinstance(data.get('scores'),list):
        raise ValueError('iScored response missing scores array')
    year, m=map(int,month.split('-'))
    start=datetime(year,m,1,tzinfo=NY)
    end=datetime(year+(m==12),m%12+1,1,tzinfo=NY)
    rows=data['scores']
    fields=Counter(k for row in rows if isinstance(row,dict) for k in row)
    date_examples=[]; bad_dates=0; naive_dates=0
    games={}
    for row in rows:
        if not isinstance(row,dict): continue
        gid=row.get('game')
        name=str(row.get('gameName') or '').strip()
        if gid is None or not name: continue
        gid=str(gid)
        game=games.setdefault(gid,{'game_id':gid,'game':name[:100],
            'starting_record_candidate':None,'record_source_count':0,
            'monthly_score_rows':0,'monthly_players':set(),'unparseable_dates':0})
        when=parse_time(row.get('date'))
        if when is None:
            bad_dates+=1;game['unparseable_dates']+=1
            if len(date_examples)<3:date_examples.append(str(row.get('date'))[:80])
            continue
        raw_date=str(row.get('date') or '')
        if not re.search(r'(Z|[+-]\d{2}:?\d{2})$',raw_date): naive_dates+=1
        try:score=int(row.get('score'))
        except (TypeError,ValueError):continue
        if score<0:continue
        if when<start:
            game['record_source_count']+=1
            if game['starting_record_candidate'] is None or score>game['starting_record_candidate']:
                game['starting_record_candidate']=score
        elif start<=when<end:
            game['monthly_score_rows']+=1
            player=str(row.get('name') or '').strip().upper()
            if player:game['monthly_players'].add(player)
    candidates=[]
    for g in games.values():
        g['monthly_player_count']=len(g.pop('monthly_players'))
        candidates.append(g)
    candidates.sort(key=lambda g:(g['game'].casefold(),g['game_id']))
    # This report is intentionally PRIVATE to a workflow artifact, never committed to Pages.
    return {'month':month,'audited_at':datetime.now(timezone.utc).isoformat(),
        'feed_rows':len(rows),'games':len(candidates),
        'field_names':sorted(fields),
        'approval_fields_present':[k for k in fields if any(x in k.lower() for x in ('approv','verif','pend','status'))],
        'dates_without_explicit_timezone':naive_dates,
        'unparseable_dates':bad_dates,'unparseable_examples':date_examples,
        'warnings':['Starting records are CANDIDATES from historical scores, not locked records.',
          'iScored feed approval semantics and timestamp timezone require manual verification.',
          'No award, leaderboard or notification is published by this audit.'],
        'candidates':candidates}
def main():
    month=os.environ.get('MONTHLY_AUDIT_MONTH',datetime.now(NY).strftime('%Y-%m'))
    if not re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])',month):raise ValueError('Invalid YYYY-MM month')
    req=Request(URL,headers={'Accept':'application/json','User-Agent':'BigDaddysArcadeMonthlyAudit/1.0'})
    with urlopen(req,timeout=40) as response:data=json.load(response)
    report=audit(data,month)
    dest=Path(os.environ.get('MONTHLY_AUDIT_OUTPUT','monthly-audit-private.json'))
    dest.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\\n')
    print('Read-only audit:',report['feed_rows'],'scores;',report['games'],'games')
    print('Approval-like fields:',report['approval_fields_present'])
    print('Naive dates:',report['dates_without_explicit_timezone'],'unparseable:',report['unparseable_dates'])
    print('PRIVATE report generated. No public files changed.')
if __name__=='__main__':main()
