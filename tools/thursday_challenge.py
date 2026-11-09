#!/usr/bin/env python3
"""Publish weekly Thursday challenge and Thursday-only standings from iScored.
Uses persisted selection, no database. Times are America/New_York; date parsing
must be verified against the live iScored API before trusting winner results.
"""
import json, os, hashlib
from datetime import datetime, date, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'thursday-challenge.json'
STATE=ROOT/'thursday-challenge-state.json'
NY=ZoneInfo('America/New_York')
URL=os.environ.get('ISCORED_READ_URL','https://www.iScored.info/api/G1LGAMESH/getAllScores')

def get_week(now):
    today=now.astimezone(NY).date()
    return today-timedelta(days=(today.weekday()-3)%7)

def parse_time(value):
    if not value:return None
    s=str(value).strip()
    try:
        d=datetime.fromisoformat(s.replace('Z','+00:00'))
        # iScored dates without a timezone are assumed to be Eastern local time.
        # Confirm this against the actual API before awarding winners.
        return (d.replace(tzinfo=NY) if d.tzinfo is None else d).astimezone(NY)
    except ValueError:pass
    for fmt in ('%m/%d/%Y %I:%M:%S %p','%m/%d/%Y %I:%M %p','%m/%d/%Y %H:%M:%S','%Y-%m-%d %H:%M:%S'):
        try:return datetime.strptime(s,fmt).replace(tzinfo=NY)
        except ValueError:pass
    return None

def fetch():
    req=Request(URL,headers={'Accept':'application/json','User-Agent':'BigDaddysArcadeThursdayChallenge/1.0'})
    with urlopen(req,timeout=30) as r:
        data=json.load(r)
    if not isinstance(data,dict) or not isinstance(data.get('scores'),list):raise ValueError('Missing iScored scores')
    return data['scores']

def build(now=None,rows=None):
    now=now or datetime.now(timezone.utc)
    rows=rows if rows is not None else fetch()
    week=get_week(now); key=week.isoformat()
    state=json.loads(STATE.read_text()) if STATE.exists() else {'weeks':{}}
    weeks=state.setdefault('weeks',{})
    games={}
    for r in rows:
        if not isinstance(r,dict):continue
        gid=r.get('game'); name=str(r.get('gameName') or '').strip()
        if gid is None or not name:continue
        gid=str(gid)
        if gid not in games:games[gid]=name[:100]
    if not games:raise ValueError('No games available; refusing to overwrite challenge')
    # First run after Thursday starts freezes the game for the whole week.
    if key not in weeks:
        ordered=sorted(games.items(),key=lambda p:(p[1].casefold(),p[0]))
        index=(week.toordinal()//7)%len(ordered)
        gid,name=ordered[index]
        weeks[key]={'game_id':gid,'game':name}
    selection=weeks[key]; gid=selection['game_id']
    start=datetime.combine(week,datetime.min.time(),tzinfo=NY)
    end=start+timedelta(days=1)
    competitors={}; unparseable=0
    for r in rows:
        if not isinstance(r,dict) or str(r.get('game'))!=gid:continue
        t=parse_time(r.get('date'))
        if t is None:
            unparseable+=1;continue
        if not start<=t<end:continue
        player=str(r.get('name') or '').strip().upper()[:48]
        if not player:continue
        try:score=int(r.get('score'))
        except (ValueError,TypeError):continue
        if score<0:continue
        if player not in competitors or score>competitors[player]['score']:
            competitors[player]={'player':player,'score':score,'submitted_at':t.isoformat()}
    standings=sorted(competitors.values(),key=lambda r:(-r['score'],r['submitted_at'],r['player']))
    complete=now.astimezone(NY)>=end
    # If dates cannot be interpreted, do not declare a definitive champion.
    confirmed=complete and unparseable==0
    winner=standings[0] if confirmed and standings else None
    result={'week':key,'game_id':gid,'game':selection['game'],'thursday_date':key,
            'cutoff':'Thursday 11:59 PM America/New_York',
            'status':('final' if confirmed else 'needs_date_review' if complete else 'live' if now.astimezone(NY)>=start else 'upcoming'),
            'winner':winner,'standings':standings[:20], 'eligible_scores':len(standings),
            'unparseable_game_dates':unparseable,'updated_at':now.isoformat()}
    # Retain only a small selection history, but keep previous winners in the public feed separately if needed.
    state['weeks']={k:v for k,v in sorted(weeks.items())[-20:]}
    OUT.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    STATE.write_text(json.dumps(state,indent=2,ensure_ascii=False)+'\n')
    print(f'Thursday {key}: {selection["game"]} / {result["status"]} / {len(standings)} players')
    return result

if __name__=='__main__':build()
