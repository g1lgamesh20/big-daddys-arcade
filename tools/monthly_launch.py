#!/usr/bin/env python3
"""Monthly launch gate: private midnight benchmark, 9 AM ET reveal, provisional scores.

No push notifications, trophy awards or verified winners are produced.
Selection/benchmark remain encrypted until release gate, and only release
fields become public. All times are America/New_York.
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from monthly_private_selection import ROOT, STATE, key_from_secret, read_json, unseal
from monthly_benchmark import run as benchmark_run, get_scores, bounds
from thursday_challenge import parse_time

NY=ZoneInfo('America/New_York')
PUBLIC=ROOT/'monthly-challenge-live.json'
CUTOFF_HOUR=9

def eastern_month(now):
    return now.strftime('%Y-%m')

def serialize(data):
    return json.dumps(data,indent=2,ensure_ascii=False)+'\n'

def standings(rows, gid, start, end):
    """Read-only, clearly provisional scores. No inferred approval status."""
    best={}
    missing_dates=0
    for row in rows:
        if not isinstance(row,dict) or str(row.get('game'))!=gid:continue
        when=parse_time(row.get('date'))
        if when is None:
            missing_dates+=1
            continue
        if not start<=when<end:continue
        person=str(row.get('name') or '').strip().upper()[:48]
        if not person:continue
        score=row.get('score')
        if isinstance(score,bool):continue
        try:score=int(score)
        except (ValueError,TypeError):continue
        if score<0:continue
        if person not in best or score>best[person]:
            best[person]=score
    rank=0
    prior=None
    sorted_rows=sorted(best.items(),key=lambda x:(-x[1],x[0]))
    out=[]
    for i,(person,score) in enumerate(sorted_rows):
        if score!=prior:rank=i+1
        prior=score
        out.append({'rank':rank,'player':person,'score':score})
    return out,missing_dates

def run(now=None, rows=None):
    now=(now or datetime.now(timezone.utc)).astimezone(NY)
    month=eastern_month(now)
    start,end=bounds(month)
    if now<start or now>=end:raise ValueError('Outside month')
    selection_state=read_json(STATE)
    selected=selection_state.get('selections',{}).get(month)
    if not selected:
        # No game is selected: do not print a title/ID or create public content.
        print('No sealed selection for this month; launch postponed safely.')
        return 'missing_selection'
    aes=AESGCM(key_from_secret())
    private=unseal(aes,selected)
    if private.get('month')!=month or not isinstance(private.get('game_id'),str):
        raise ValueError('Sealed selection did not match month')
    gid=private['game_id']
    cutoff=now.replace(hour=CUTOFF_HOUR,minute=0,second=0,microsecond=0)
    # Midnight ET: the first workflow run after local midnight locks the starting record.
    if 'benchmark_lock' not in private and now<cutoff:
        old_month=os.environ.get('MONTHLY_BENCHMARK_MONTH')
        old_action=os.environ.get('MONTHLY_BENCHMARK_ACTION')
        try:
            os.environ['MONTHLY_BENCHMARK_MONTH']=month
            os.environ['MONTHLY_BENCHMARK_ACTION']='lock'
            result=benchmark_run(now=now,rows=rows)
        finally:
            if old_month is None:os.environ.pop('MONTHLY_BENCHMARK_MONTH',None)
            else:os.environ['MONTHLY_BENCHMARK_MONTH']=old_month
            if old_action is None:os.environ.pop('MONTHLY_BENCHMARK_ACTION',None)
            else:os.environ['MONTHLY_BENCHMARK_ACTION']=old_action
        if result.get('status') not in ('locked','already_locked'):
            raise ValueError('No benchmark lock confirmed')
        print('Local-midnight benchmark lock completed privately.')
        return 'locked'
    if now<cutoff:
        print('Private benchmark already locked; reveal is not yet permitted.')
        return 'waiting_for_reveal'
    if 'benchmark_lock' not in private:
        # Delayed GitHub Actions run cannot quietly create an after-reveal baseline.
        print('No midnight benchmark lock; public launch blocked pending operator review.')
        return 'blocked_missing_lock'
    locked=private['benchmark_lock']
    if locked.get('month_start')!=start.isoformat():
        raise ValueError('Benchmark is for the wrong start date')
    starting=locked.get('starting_record')
    target=locked.get('benchmark')
    if type(starting) is not int or type(target) is not int or starting<0 or target!=(starting*3+3)//4:
        raise ValueError('Invalid encrypted benchmark')
    catalog=read_json(ROOT/'monthly-game-catalog.json').get('games')
    if not isinstance(catalog,dict) or gid not in catalog:
        raise ValueError('Featured game ID absent from catalog')
    old=read_json(PUBLIC) if PUBLIC.exists() else {'status':'not_launched'}
    if old.get('month')==month and str(old.get('game_id'))!=gid:
        raise ValueError('Published game cannot be silently replaced')
    if old.get('month')==month and old.get('starting_record')!=starting:
        raise ValueError('Published starting record cannot change')
    if rows is None:rows=get_scores()
    provisional,unparseable=standings(rows,gid,start,end)
    live={
      'schema_version':1,'month':month,'timezone':'America/New_York',
      'reveal_at':cutoff.isoformat(),
      'game_id':gid,'game':catalog[gid],'starting_record':starting,
      'benchmark':target,
      'status':'provisional',
      'approval_status':'unverified_iscored_feed',
      'timestamp_assumption':'iScored naive timestamps interpreted as America/New_York; pending verification',
      'podium_status':'not_awarded',
      'leaderboard':provisional[:100],
      'unparseable_selected_game_dates':unparseable,
      'updated_at':now.isoformat()
    }
    if old==live:
        return 'unchanged'
    PUBLIC.write_text(serialize(live),encoding='utf-8')
    print('Monthly public challenge generated after 9 AM ET; player scores are provisional only.')
    print('No marquee URL supplied; no push, trophy, or verified awards were issued.')
    return 'published'

if __name__=='__main__':
    run()
