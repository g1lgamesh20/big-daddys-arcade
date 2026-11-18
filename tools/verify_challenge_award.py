#!/usr/bin/env python3
"""Operator-reviewed Daily score evidence and permanent Thursday Champion awards.

This workflow is intentionally NOT an automatic inference of iScored approval.
The operator confirms photo/approval and event-local submission timing in iScored.
No push notifications or medal events are emitted.
"""
import json,os,re
from datetime import datetime,timezone
from pathlib import Path
from unified_milestone_awards import issue as issue_cross_challenge_milestones

ROOT=Path(__file__).resolve().parents[1]
PENDING=ROOT/'challenge-award-candidates.json'
WINNERS=ROOT/'thursday-winners.json'
OUT=ROOT/'verified-challenge-awards.json'

# Permanent, one-time rewards for cumulative verified Daily Challenge participation.
# Award IDs are deterministic; scores and dates are NOT inferred from iScored API timestamps.
DAILY_MILESTONES=(
    (5,'Getting Started'),
    (10,'Dedicated Challenger'),
    (25,'Champion Chaser'),
    (50,'Never Back Down'),
)

def daily_play_dates(ledger, player):
    """A player earns at most one credit for each explicitly verified Daily date."""
    return {p['date'] for p in ledger['verified_plays']
        if isinstance(p,dict) and p.get('kind')=='daily'
        and str(p.get('player','')).strip().upper()==player
        and isinstance(p.get('date'),str)
        and re.fullmatch(r'20\d\d-\d\d-\d\d',p['date'])
        and isinstance(p.get('event_key'),str) and p['event_key'].startswith('daily:')}

def issue_daily_milestones(ledger, player, now):
    """Create milestone awards only from permanent operator-verified play records."""
    days=daily_play_dates(ledger,player)
    count=len(days)
    seen={str(a.get('id')) for a in ledger['awards'] if isinstance(a,dict)}
    for threshold,name in DAILY_MILESTONES:
        key=f'daily_participation:{player}:{threshold}'
        if count<threshold or key in seen:
            continue
        unlocked_on=sorted(days)[threshold-1]
        ledger['awards'].append({
            'id':key,'event_key':key,'type':'daily_participation_milestone',
            'name':name,'date':unlocked_on,'player':player,'game':'Beat the Champion',
            'milestone':threshold,'verified_daily_days':count,
            'verified_at':now.isoformat(),
            'verification_method':'operator_verified_daily_play_ledger',
        })
        seen.add(key)

def read(path, default):
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else default

def approve(pending, winner_archive, ledger, *, kind, event_date, player, score_id, confirmed, now):
    if confirmed is not True:
        raise ValueError('Explicit operator approval, photo, and timestamp confirmation required.')
    if kind not in ('thursday_champion','thursday_verified_play','daily_verified_play'):
        raise ValueError('Unknown award action')
    if not re.fullmatch(r'20\d\d-\d\d-\d\d',event_date):
        raise ValueError('Enter event date YYYY-MM-DD')
    datetime.strptime(event_date,'%Y-%m-%d')
    player=player.strip().upper()
    if not re.fullmatch(r'[A-Z0-9][A-Z0-9 _.-]{0,47}',player):
        raise ValueError('Invalid player name')
    if not score_id.strip():
        raise ValueError('Score ID must be nonempty; cannot approve untraceable result')
    if ledger.get('schema_version')!=1 or not isinstance(ledger.get('awards'),list) or not isinstance(ledger.get('verified_plays'),list):
        raise ValueError('Invalid official ledger')
    candidates=[c for c in pending.get('candidates',[]) if isinstance(c,dict)
        and c.get('kind')==('thursday' if kind.startswith('thursday_') else 'daily')
        and c.get('date')==event_date and c.get('player')==player
        and str(c.get('score_id'))==score_id.strip()]
    if len(candidates)!=1:
        raise ValueError('Exactly one matching pending score required; review the candidate file')
    c=candidates[0]
    if c.get('verification')!='pending_iscored_approval_and_timezone_review' or c.get('awarded') is not False:
        raise ValueError('Candidate verification state unexpected')
    if not isinstance(c.get('best_score'),int) or c['best_score']<0:
        raise ValueError('Invalid candidate score')
    event=':'.join([c['kind'],event_date,c['game_id'],player])
    if kind=='thursday_champion':
        matching=[w for w in winner_archive.get('weeks',[]) if isinstance(w,dict)
            and w.get('week')==event_date and w.get('status')=='final'
            and str(w.get('game_id'))==c['game_id']]
        if len(matching)!=1:
            raise ValueError('No uniquely finalized Thursday event')
        w=matching[0].get('winner')
        if not isinstance(w,dict) or str(w.get('player','')).strip().upper()!=player or w.get('score')!=c['best_score']:
            raise ValueError('Archived Thursday winner does not match score; do not award')
        # One winner per Thursday unless a future tie-aware review policy is introduced.
        for a in ledger['awards']:
            if a.get('type')=='thursday_champion' and a.get('date')==event_date:
                if a.get('event_key')==event:
                    print('Existing Thursday trophy preserved; no duplicate')
                    return ledger,False
                raise ValueError('Thursday already awarded to another player; manual correction required')
        award={'id':'thursday_champion:'+event_date,'event_key':event,
            'type':'thursday_champion','name':'Thursday Champion',
            'date':event_date,'player':player,'game':c['game'],'game_id':c['game_id'],
            'score':c['best_score'],'score_id':score_id.strip(),'verified_at':now.isoformat(),
            'verification_method':'operator_confirmed_iscored_approved_photo_and_time'}
        ledger['awards'].append(award)
    else:
        play_kind='thursday' if kind=='thursday_verified_play' else 'daily'
        if any(p.get('event_key')==event for p in ledger['verified_plays']):
            print('Verified challenge participation already recorded; no duplicate')
            return ledger,False
        ledger['verified_plays'].append({'event_key':event,'kind':play_kind,
            'date':event_date,'player':player,'game_id':c['game_id'],
            'game':c['game'],'score':c['best_score'],'score_id':score_id.strip(),
            'verified_at':now.isoformat(),'trophy_issued':False})
        if play_kind=='daily':issue_daily_milestones(ledger,player,now)
    issue_cross_challenge_milestones(ledger,now)
    ledger['awards'].sort(key=lambda a:(a['date'],a['id']))
    ledger['verified_plays'].sort(key=lambda a:(a['date'],a['event_key']))
    return ledger,True

def main():
    kind=os.environ.get('TROPHY_ACTION','')
    date=os.environ.get('TROPHY_DATE','')
    player=os.environ.get('TROPHY_PLAYER','')
    sid=os.environ.get('TROPHY_SCORE_ID','')
    ok=os.environ.get('TROPHY_CONFIRMED','').lower()=='true'
    pending=read(PENDING,{'candidates':[]})
    winners=read(WINNERS,{'weeks':[]})
    ledger=read(OUT,{'schema_version':1,'awards':[],'verified_plays':[]})
    updated,changed=approve(pending,winners,ledger,kind=kind,event_date=date,
         player=player,score_id=sid,confirmed=ok,now=datetime.now(timezone.utc))
    if changed:
        OUT.write_text(json.dumps(updated,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print('Operator-reviewed event recorded permanently:',kind,date)
    print('No OneSignal message, medal, or unreviewed award was issued.')

if __name__=='__main__':main()
