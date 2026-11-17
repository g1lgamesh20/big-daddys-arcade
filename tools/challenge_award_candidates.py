#!/usr/bin/env python3
"""Append-only Daily/Thursday score evidence for future achievement approval.

These are NOT verified achievements. iScored exposes no confirmed approval flag
and its date strings lack explicit timezone. Preserve candidate history, never
send notifications, and never add anything to permanent trophy counts.
"""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo
from thursday_challenge import parse_time

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'challenge-award-candidates.json'
DAILY=ROOT/'daily-champion.json'
DAILY_HISTORY=ROOT/'daily-champion-history.json'
THURSDAY=ROOT/'thursday-challenge-state.json'
NY=ZoneInfo('America/New_York')
URL='https://www.iScored.info/api/G1LGAMESH/getAllScores'

def read(path,default):
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else default

def selections():
    # Permanent selections retain credit for scores approved after their day.
    daily=read(DAILY_HISTORY,{'days':[]}).get('days',[])
    recent=read(DAILY,{}).get('days',[])
    if not isinstance(daily,list) or not isinstance(recent,list):
        raise ValueError('Invalid Daily selection data')
    known={item['date']:item for item in daily if isinstance(item,dict) and isinstance(item.get('date'),str)}
    for item in recent:
        if not isinstance(item,dict) or not isinstance(item.get('date'),str):continue
        previous=known.get(item['date'])
        if previous and previous.get('game_id')!=item.get('game_id'):
            raise ValueError('Daily live schedule differs from permanent history')
        known.setdefault(item['date'],item)
    daily=list(known.values())
    weeks=read(THURSDAY,{}).get('weeks',{})
    entries={}
    for day in daily:
        if not isinstance(day,dict):continue
        date=day.get('date'); gid=str(day.get('game_id') or '')
        if isinstance(date,str) and len(date)==10 and gid:
            entries[('daily',date,gid)]=str(day.get('game') or '')[:100]
    if isinstance(weeks,dict):
        for day,info in weeks.items():
            if not isinstance(info,dict):continue
            gid=str(info.get('game_id') or '')
            if isinstance(day,str) and len(day)==10 and gid:
                entries[('thursday',day,gid)]=str(info.get('game') or '')[:100]
    return entries

def collect(rows, eligible, now=None, existing=None):
    now=now or datetime.now(timezone.utc)
    old=existing or {'schema_version':1,'candidates':[]}
    if old.get('schema_version')!=1 or not isinstance(old.get('candidates'),list):
        raise ValueError('Invalid candidate ledger; refusing to overwrite')
    by_key={}
    for item in old['candidates']:
        if not isinstance(item,dict) or not isinstance(item.get('key'),str):raise ValueError('Invalid stored candidate')
        if item['key'] in by_key:raise ValueError('Duplicate existing candidate key')
        by_key[item['key']]=item
    bad=0
    for row in rows:
        if not isinstance(row,dict):continue
        gid=str(row.get('game') or '')
        name=str(row.get('name') or '').strip().upper()[:48]
        if not gid or not name:continue
        raw_date=str(row.get('date') or '').strip()
        t=parse_time(raw_date)
        if t is None:
            bad+=1
            continue
        day=t.astimezone(NY).date().isoformat()
        try:
            if isinstance(row.get('score'),bool):continue
            score=int(row.get('score'))
            if score<0:continue
        except (ValueError,TypeError):continue
        for kind in ('daily','thursday'):
            selected=eligible.get((kind,day,gid))
            if selected is None:continue
            key=':'.join([kind,day,gid,name])
            current=by_key.get(key)
            if current is not None and score<=current['best_score']:continue
            # Do not overwrite first-seen audit evidence. Scores may improve.
            candidate={
                'key':key,'kind':kind,'date':day,'game_id':gid,'game':selected,
                'player':name,'best_score':score,'score_id':str(row.get('id') or ''),
                'submitted_at_assumed_et':t.isoformat(),
                'first_seen_at':current['first_seen_at'] if current else now.isoformat(),
                'last_seen_at':now.isoformat(),
                'verification':'pending_iscored_approval_and_timezone_review',
                'awarded':False
            }
            by_key[key]=candidate
    return {
      'schema_version':1,
      'warning':'Pending evidence only: not verified trophies. Timestamps assumed Eastern; iScored approval status unconfirmed.',
      'updated_at':now.isoformat(),
      'unparseable_feed_dates':bad,
      'candidates':sorted(by_key.values(),key=lambda x:(x['date'],x['kind'],x['game_id'],x['player']))
    }

def main():
    available=selections()
    if not available:raise ValueError('No selected challenges; preserving candidate history')
    req=Request(URL,headers={'Accept':'application/json','User-Agent':'BigDaddysPendingAwards/1.0'})
    with urlopen(req,timeout=35) as response:data=json.load(response)
    if not isinstance(data,dict) or not isinstance(data.get('scores'),list):raise ValueError('Missing iScored scores')
    previous=read(OUT,{'schema_version':1,'candidates':[]})
    result=collect(data['scores'],available,existing=previous)
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Pending Daily/Thursday score evidence recorded:',len(result['candidates']))
    print('No trophies, points, or notifications were awarded.')

if __name__=='__main__':main()
