#!/usr/bin/env python3
"""Issue cumulative milestones and streak trophies from permanent VERIFIED entries.

No use of public iScored API timestamps, pending candidates or provisional
leaderboards. Call only after a genuine operator-verified ledger mutation.
"""
from datetime import date
from collections import defaultdict

START={'daily':'2026-11-16','thursday':'2026-11-12','monthly':'2026-12-01'}
# Daily participation milestones 5/10/25/50 are handled by the existing routine.
MILESTONES={
  'thursday':((3,'Thursday Regular'),(5,'Thursday Devotee'),(10,'Thursday Veteran'),(25,'Thursday Legend')),
  'monthly':((3,'Monthly Challenger'),(6,'Half-Year Hero'),(12,'Year-Round Legend'),
             (24,'Two-Year Titan'),(36,'Three-Year Legend'),(60,'Five-Year Immortal')),
}
STREAKS={
  'daily':((3,'Three-Day Streak'),(7,'Seven-Day Streak'),(14,'Two-Week Streak')),
  'thursday':((3,'Three-Thursday Streak'),(5,'Five-Thursday Streak')),
  'monthly':((3,'Three-Month Streak'),(6,'Six-Month Streak')),
}
CHAMPION={'daily_champion':'daily','thursday_champion':'thursday','gotm_champion':'monthly'}

def day_for(kind,value):
    if not isinstance(value,str):return None
    if kind=='monthly':
        if len(value)<7:return None
        value=value[:7]+'-01'
    try:
        day=date.fromisoformat(value)
        if day.isoformat()!=value or day.isoformat()<START[kind]:return None
        if kind=='thursday' and day.weekday()!=3:return None
        if kind=='monthly' and day.day!=1:return None
        return day
    except (ValueError,TypeError):return None

def activity(ledger):
    """Return one event date per player/type from verified plays OR champions."""
    days=defaultdict(set)
    for play in ledger.get('verified_plays',[]):
        if not isinstance(play,dict) or play.get('kind') not in START:continue
        kind=play['kind'];player=str(play.get('player') or '').strip().upper()
        when=day_for(kind,play.get('date'))
        if player and when and str(play.get('event_key') or '').startswith(kind+':'):
            days[(player,kind)].add(when)
    for award in ledger.get('awards',[]):
        if not isinstance(award,dict):continue
        kind=CHAMPION.get(award.get('type'))
        if not kind:continue
        player=str(award.get('player') or '').strip().upper()
        when=day_for(kind,award.get('date'))
        if player and when and str(award.get('event_key') or '').startswith(kind+':'):
            days[(player,kind)].add(when)
    return days

def adjacent(previous,current,kind):
    if kind=='daily':return (current-previous).days==1
    if kind=='thursday':return (current-previous).days==7
    return previous.year*12+previous.month+1==current.year*12+current.month

def awards_due(ledger,now):
    if ledger.get('schema_version')!=1 or not isinstance(ledger.get('awards'),list) or not isinstance(ledger.get('verified_plays'),list):
        raise ValueError('Invalid verified ledger')
    seen={str(a.get('id')) for a in ledger['awards'] if isinstance(a,dict)}
    new=[]
    for (player,kind),found in sorted(activity(ledger).items()):
        ordered=sorted(found)
        if kind in MILESTONES:
            for threshold,name in MILESTONES[kind]:
                if len(ordered)<threshold:continue
                key=f'{kind}_participation:{player}:{threshold}'
                if key in seen:continue
                new.append({'id':key,'event_key':key,
                    'type':f'{kind}_participation_milestone','name':name,
                    'date':ordered[threshold-1].isoformat(),'player':player,
                    'game':'Thursday Arcade Challenge' if kind=='thursday' else 'Game of the Month',
                    'milestone':threshold,'verified_at':now.isoformat(),
                    'verification_method':'permanent_verified_event_history'})
                seen.add(key)
        # A streak trophy unlocks once the first verified consecutive run reaches
        # its threshold, and remains earned even if the streak later ends.
        run=0;last=None;first_unlock={}
        for day in ordered:
            run=run+1 if last and adjacent(last,day,kind) else 1
            last=day
            for threshold,name in STREAKS[kind]:
                if run>=threshold and threshold not in first_unlock:
                    first_unlock[threshold]=(day,name)
        for threshold,(day,name) in first_unlock.items():
            key=f'{kind}_streak:{player}:{threshold}'
            if key in seen:continue
            new.append({'id':key,'event_key':key,'type':f'{kind}_streak',
                'name':name,'date':day.isoformat(),'player':player,
                'game':{'daily':'Beat the Champion','thursday':'Thursday Arcade Challenge',
                        'monthly':'Game of the Month'}[kind],
                'milestone':threshold,'verified_at':now.isoformat(),
                'verification_method':'permanent_verified_event_history'})
            seen.add(key)
    return new

def issue(ledger,now):
    new=awards_due(ledger,now)
    if not new:return 0
    ledger['awards'].extend(new)
    return len(new)
