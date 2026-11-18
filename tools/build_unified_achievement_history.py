#!/usr/bin/env python3
"""Build a read-only unified challenge history from existing permanent records.

Never treats public iScored API timestamps, score candidates, or provisional
leaderboards as verified submission evidence. Never issues awards or pushes.
"""
import json
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'unified-achievement-history.json'
DAILY_START='2026-11-16'
THURSDAY_START='2026-11-12'
MONTHLY_START='2026-12'

def load(name, default):
    path=ROOT/name
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else default

def iso_day(s):
    if not isinstance(s,str):return False
    try:return date.fromisoformat(s).isoformat()==s
    except ValueError:return False

def add_event(events,kind,day,game_id,game,source,**extra):
    if not iso_day(day) or not str(game_id).strip():return
    key=kind+':'+day
    item={'event_key':key,'kind':kind,'date':day,
          'game_id':str(game_id),'game':str(game),'schedule_source':source,
          'participants':[],'champions':[],'unverified_candidates':[]}
    item.update(extra)
    old=events.get(key)
    if old:
        if old['game_id']!=item['game_id']:
            raise ValueError('Conflicting historical game selection: '+key)
        return
    events[key]=item

def verified_dates(events,ledger):
    """Verified plays and champion awards are explicit evidence, never candidates."""
    participation=set()
    champions=set()
    for p in ledger['verified_plays']:
        if not isinstance(p,dict) or p.get('kind') not in ('daily','thursday','monthly'):continue
        kind=p['kind'];day=p.get('date');player=str(p.get('player') or '').strip().upper()
        key=kind+':'+str(day)
        event=events.get(key)
        if not event or not player or str(p.get('game_id'))!=event['game_id']:continue
        # The entry was expressly recorded in the permanent verified ledger.
        participation.add((key,player))
    champion_types={'thursday_champion':'thursday','daily_champion':'daily','gotm_champion':'monthly'}
    for a in ledger['awards']:
        if not isinstance(a,dict):continue
        kind=champion_types.get(a.get('type'))
        if not kind:continue
        key=kind+':'+str(a.get('date'))
        event=events.get(key)
        player=str(a.get('player') or '').strip().upper()
        if not event or not player or str(a.get('game_id'))!=event['game_id']:continue
        # A verified champion competed, even if their participation play record
        # predates the unified format. This is a derived count, not a new award.
        champions.add((key,player))
        participation.add((key,player))
    for key,player in sorted(participation):
        events[key]['participants'].append(player)
    for key,player in sorted(champions):
        events[key]['champions'].append(player)
    return participation,champions

def consecutive_streak(days,kind,ordered_dates):
    """Longest consecutive scheduled-event streak, never consecutive approvals."""
    if not days:return 0
    if kind=='daily':
        # Missing schedule dates must not silently bridge a gap in a streak.
        all_days=[date.fromisoformat(x) for x in ordered_dates]
        valid={x for x in all_days if x.isoformat() in days}
        best=run=0
        last=None
        for d in all_days:
            if d in valid:
                run=run+1 if last and (d-last).days==1 else 1
                last=d
            else:
                run=0
                last=None
            best=max(best,run)
        return best
    if kind=='thursday':
        ordered=[date.fromisoformat(x) for x in ordered_dates]
        best=run=0
        previous=None
        for d in ordered:
            if d.isoformat() in days:
                run=run+1 if previous and (d-previous).days==7 else 1
                previous=d
                best=max(best,run)
            else:run=0;previous=None
        return best
    if kind=='monthly':
        months=sorted({x[:7] for x in days})
        best=run=0;last=None
        for m in months:
            y,mon=map(int,m.split('-'))
            index=y*12+mon
            run=run+1 if last is not None and index==last+1 else 1
            last=index;best=max(best,run)
        return best
    return 0

def build(daily_history,daily_live,thursday_state,thursday_winners,monthly_live,ledger,candidates):
    if ledger.get('schema_version')!=1 or not isinstance(ledger.get('awards'),list) or not isinstance(ledger.get('verified_plays'),list):
        raise ValueError('Invalid permanent verified ledger: fail closed')
    events={}
    for packet,source in [(daily_history,'daily-champion-history.json'),(daily_live,'daily-champion.json')]:
        for row in packet.get('days',[]):
            if not isinstance(row,dict):continue
            day=row.get('date')
            if isinstance(day,str) and day>=DAILY_START:
                add_event(events,'daily',day,row.get('game_id'),row.get('game',''),source)
    for day,row in thursday_state.get('weeks',{}).items():
        if day<THURSDAY_START or not isinstance(row,dict):continue
        add_event(events,'thursday',day,row.get('game_id'),row.get('game',''),'thursday-challenge-state.json')
    # Archived results are historical evidence; do not award new winners from them.
    for row in thursday_winners.get('weeks',[]):
        if not isinstance(row,dict):continue
        day=row.get('week')
        if not isinstance(day,str) or day<THURSDAY_START:continue
        add_event(events,'thursday',day,row.get('game_id'),row.get('game',''),'thursday-winners.json')
        key='thursday:'+day
        if key in events:
            events[key]['result_status']=str(row.get('status') or 'unknown')
            if row.get('winner'):
                events[key]['archived_winner_unverified_by_this_report']=str(row['winner'].get('player') or '')
    # Never expose sealed monthly selections. Only *published* month/game after reveal.
    if isinstance(monthly_live,dict) and monthly_live.get('status')=='provisional':
        month=monthly_live.get('month')
        if isinstance(month,str) and month>=MONTHLY_START and len(month)==7:
            day=month+'-01'
            add_event(events,'monthly',day,monthly_live.get('game_id'),
                      monthly_live.get('game',''),'monthly-challenge-live.json',
                      provisional=True)
    verified,champions=verified_dates(events,ledger)
    seen=set()
    for c in candidates.get('candidates',[]):
        if not isinstance(c,dict):continue
        kind=c.get('kind');day=c.get('date')
        if kind not in ('daily','thursday') or not isinstance(day,str):continue
        event=events.get(kind+':'+day)
        if not event or str(c.get('game_id'))!=event['game_id']:continue
        player=str(c.get('player') or '').strip().upper()
        sid=str(c.get('score_id') or '')
        if not player or not sid or (event['event_key'],player) in verified:continue
        identity=(event['event_key'],player,sid)
        if identity in seen:continue
        seen.add(identity)
        event['unverified_candidates'].append({
            'player':player,'score_id':sid,'score':c.get('best_score'),
            'status':'ORIGINAL_SUBMISSION_TIME_NOT_VERIFIED'})
    for event in events.values():
        event['unverified_candidates'].sort(key=lambda x:(x['player'],x['score_id']))
        event['verified_participant_count']=len(event['participants'])
        event['verified_champion_count']=len(event['champions'])
    per_player=defaultdict(lambda:{'daily':set(),'thursday':set(),'monthly':set()})
    wins=defaultdict(lambda:{'daily':0,'thursday':0,'monthly':0})
    for key,player in verified:
        event=events[key];per_player[player][event['kind']].add(event['date'])
    for key,player in champions:
        wins[player][events[key]['kind']]+=1
    ordered={kind:sorted(e['date'] for e in events.values() if e['kind']==kind)
             for kind in ('daily','thursday','monthly')}
    players={}
    for player,dates in sorted(per_player.items()):
        players[player]={
            'participation':{kind:len(dates[kind]) for kind in ('daily','thursday','monthly')},
            'championships':dict(wins[player]),
            'longest_verified_streaks':{
                kind:consecutive_streak(dates[kind],kind,ordered[kind])
                for kind in ('daily','thursday','monthly')},
        }
    return {
        'schema_version':1,'timezone':'America/New_York',
        'official_start':{'daily':DAILY_START,'thursday':THURSDAY_START,'monthly':MONTHLY_START+'-01'},
        'mode':'READ_ONLY_PROJECTION_FROM_PERMANENT_VERIFIED_LEDGER',
        'rules':{'one_participation_per_player_per_event':True,
                 'championship_implies_participation':True,
                 'unverified_candidates_count_as_zero':True,
                 'api_approval_time_never_proves_submitted_before_midnight':True,
                 'no_awards_or_push_sent_by_this_builder':True},
        'events':sorted(events.values(),key=lambda e:(e['date'],e['kind'])),
        'players':players,
    }

def main():
    inputs=[
        load('daily-champion-history.json',{'days':[]}),
        load('daily-champion.json',{'days':[]}),
        load('thursday-challenge-state.json',{'weeks':{}}),
        load('thursday-winners.json',{'weeks':[]}),
        load('monthly-challenge-live.json',{}),
        load('verified-challenge-awards.json',{'schema_version':1,'awards':[],'verified_plays':[]}),
        load('challenge-award-candidates.json',{'candidates':[]}),
    ]
    history=build(*inputs)
    OUT.write_text(json.dumps(history,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print('Official challenge events:',len(history['events']))
    print('Verified participating players:',len(history['players']))
    print('Historical candidate entries:',
        sum(len(e['unverified_candidates']) for e in history['events']))
    print('No trophy/medal/push changes.')

if __name__=='__main__':main()
