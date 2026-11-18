#!/usr/bin/env python3
"""Generous, explicitly opt-in iScored approval-window challenge credits.

The public feed includes scores only AFTER iScored operator approval; the
public score date behaves as approval time, not original submission time.
Operator policy prefers crediting borderline approvals to denying attendance.
An approval in [event start, event end + grace] is ACCEPTED as a policy proxy,
not proof of original play time. This can credit late/early submissions.
Never silently rewrite existing awards, alter score medals, or send pushes.
"""
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from verify_challenge_award import issue_daily_milestones
from unified_milestone_awards import issue as issue_other_milestones

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'verified-challenge-awards.json'
AUDIT=ROOT/'approval-window-credit-report.json'
BASELINES=ROOT/'daily-champion-baselines.json'
NY=ZoneInfo('America/New_York')
# Observed Nov 18 API timestamps were one hour behind ET; Central is a
# *working assumption*, NOT a proven iScored timezone contract.
SOURCE=ZoneInfo('America/Chicago')
GRACE_HOURS={'daily':24,'thursday':24,'monthly':24}
START={'daily':'2026-11-16','thursday':'2026-11-12','monthly':'2026-12-01'}

def load(filename,default):
    path=ROOT/filename
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else default

def approval_time(raw):
    if not raw:return None
    value=str(raw).strip()
    try:
        dt=datetime.fromisoformat(value.replace('Z','+00:00'))
    except ValueError:
        dt=None
        for fmt in ('%m/%d/%Y %I:%M:%S %p','%m/%d/%Y %I:%M %p',
                    '%Y-%m-%d %H:%M:%S','%Y-%m-%d %H:%M'):
            try:dt=datetime.strptime(value,fmt);break
            except ValueError:pass
    if dt is None:return None
    if dt.tzinfo is None:dt=dt.replace(tzinfo=SOURCE)
    return dt.astimezone(NY)

def scheduled(daily_archive,daily_live,thursday_state,monthly_public,baselines=None):
    events={}
    for packet in (daily_archive,daily_live):
        for entry in packet.get('days',[]):
            if not isinstance(entry,dict):continue
            day=entry.get('date')
            gid=str(entry.get('game_id') or '')
            if not isinstance(day,str) or day<START['daily'] or not gid:continue
            try:date=datetime.strptime(day,'%Y-%m-%d')
            except ValueError:continue
            if (old:=events.get(('daily',day))) and old['game_id']!=gid:
                raise ValueError('Daily game selection changed: '+day)
            previous=events.get(('daily',day),{})
            locked=(baselines or {}).get(day,{})
            baseline=(entry.get('starting_champion_score')
                     if type(entry.get('starting_champion_score')) is int
                     else locked.get('starting_champion_score') if locked.get('game_id')==gid else None)
            events[('daily',day)]={'game_id':gid,'game':str(entry.get('game') or previous.get('game') or ''),
                'starting_champion_score':baseline}
    for day,entry in thursday_state.get('weeks',{}).items():
        if day<START['thursday'] or not isinstance(entry,dict):continue
        gid=str(entry.get('game_id') or '')
        try:d=datetime.strptime(day,'%Y-%m-%d')
        except ValueError:continue
        if d.weekday()!=3 or not gid:continue
        events[('thursday',day)]={'game_id':gid,'game':str(entry.get('game') or '')}
    # Only PUBLICLY REVEALED monthly games may be scanned. Sealed selection is
    # never inspected, logged, or matched before the 9 AM reveal.
    if isinstance(monthly_public,dict) and monthly_public.get('status')=='provisional':
        month=monthly_public.get('month')
        gid=str(monthly_public.get('game_id') or '')
        if isinstance(month,str) and len(month)==7 and month>=START['monthly'][:7] and gid:
            try:date=datetime.strptime(month+'-01','%Y-%m-%d')
            except ValueError:pass
            else:events[('monthly',month+'-01')]={'game_id':gid,
                    'game':str(monthly_public.get('game') or '')}
    return events

def capture_daily_baselines(rows,archive,live,previous,now):
    """Snapshot tomorrow's starting champion BEFORE midnight, never retroactively.

    Repeat pre-midnight snapshots to get the latest available approved #1.
    Existing days are frozen when their local start passes. No secret games.
    """
    out=json.loads(json.dumps(previous))
    for (kind,day),event in scheduled(archive,live,{'weeks':{}},{},{}).items():
        if kind!='daily':continue
        begin=datetime.strptime(day,'%Y-%m-%d').replace(tzinfo=NY)
        if not now.astimezone(NY)<begin:continue
        gid=event['game_id']
        eligible=[]
        for row in rows:
            if not isinstance(row,dict) or str(row.get('game') or '')!=gid:continue
            when=approval_time(row.get('date'))
            if when is None or when>now.astimezone(NY) or when>=begin:continue
            try:score=int(row.get('score'))
            except (TypeError,ValueError):continue
            if score<0 or isinstance(row.get('score'),bool):continue
            eligible.append(score)
        if not eligible:continue
        existing=out.get(day)
        if existing and existing.get('game_id')!=gid:
            raise ValueError('Daily baseline game changed: '+day)
        out[day]={'game_id':gid,'starting_champion_score':max(eligible),
                  'observed_at':now.isoformat(),
                  'evidence':'pre_start_approved_iscored_score_snapshot'}
    return out

def interval(kind,day):
    begin=datetime.strptime(day,'%Y-%m-%d').replace(tzinfo=NY)
    if kind=='daily' or kind=='thursday':
        end=datetime.combine((begin+timedelta(days=1)).date(),
                             datetime.min.time(),tzinfo=NY)
    else:
        y,m=begin.year,begin.month
        end=datetime(y+(m==12),m%12+1,1,tzinfo=NY)
    return begin,end,end+timedelta(hours=GRACE_HOURS[kind])

def candidates(rows,events,now):
    by_event={}
    invalid=0
    for row in rows:
        if not isinstance(row,dict):continue
        gid=str(row.get('game') or '')
        sid=str(row.get('id') or '').strip()
        player=str(row.get('name') or '').strip().upper()[:48]
        if not gid or not sid or not player:continue
        raw=row.get('score')
        if isinstance(raw,bool):continue
        try:score=int(raw)
        except (ValueError,TypeError):continue
        if score<0:continue
        when=approval_time(row.get('date'))
        if not when:invalid+=1;continue
        # Prevent untrusted approval times in future from producing awards.
        if when>now.astimezone(NY)+timedelta(minutes=5):continue
        for (kind,day),event in events.items():
            if gid!=event['game_id']:continue
            start,end,cutoff=interval(kind,day)
            if start<=when<cutoff:
                key=(kind,day,player)
                item={'kind':kind,'date':day,'player':player,'game_id':gid,
                      'game':event['game'],'score':score,'score_id':sid,
                      'approved_at_policy_et':when.isoformat()}
                previous=by_event.get(key)
                if previous is None or (score,-when.timestamp(),sid)>(previous['score'],-datetime.fromisoformat(previous['approved_at_policy_et']).timestamp(),previous['score_id']):
                    by_event[key]=item
    return by_event,invalid

def process(rows,daily_archive,daily_live,thursday_state,monthly_public,ledger,now,enabled=False,baselines=None):
    if ledger.get('schema_version')!=1 or not isinstance(ledger.get('verified_plays'),list) or not isinstance(ledger.get('awards'),list):
        raise ValueError('Invalid official verified ledger')
    events=scheduled(daily_archive,daily_live,thursday_state,monthly_public,baselines)
    matched,invalid=candidates(rows,events,now)
    proposed=[]
    for (kind,day,player),c in sorted(matched.items()):
        if any(p.get('kind')==kind and p.get('date')==day and
               str(p.get('player') or '').upper()==player
               for p in ledger['verified_plays'] if isinstance(p,dict)):continue
        # An existing confirmed champion already implies attendance.
        if any(a.get('type')=={'daily':'daily_champion','thursday':'thursday_champion','monthly':'gotm_champion'}[kind]
               and str(a.get('player') or '').upper()==player and
               (str(a.get('event_month') or '')==day[:7] if kind=='monthly' else a.get('date')==day)
               for a in ledger['awards'] if isinstance(a,dict)):continue
        proposed.append(c)
    report={'schema_version':1,'mode':'enabled' if enabled else 'preview',
      'policy':'approved_score_within_event_start_to_end_plus_24h',
      'approval_timezone_assumption':'America/Chicago for naive iScored API timestamps; verify with source',
      'caveat':'Approval timestamp is NOT original submission time. Grace policy can include scores not originally played during event.',
      'matches':len(matched),'new_participation_credits':len(proposed),
      'unparseable_dates':invalid,'proposed_credits':proposed,
      'new_championships':[],'no_push_notifications':True}
    if not enabled:return ledger,report,False
    updated=json.loads(json.dumps(ledger))
    for c in proposed:
        kind=c['kind'];day=c['date'];player=c['player']
        p={k:c[k] for k in ('kind','date','player','game_id','game','score','score_id')}
        p.update({'event_key':f"{kind}:{day}:{c['game_id']}:{player}",
            'verified_at':now.isoformat(),'trophy_issued':False,
            'approval_time_policy':c['approved_at_policy_et'],
            'verification_method':'approved_iscored_score_with_24h_generous_grace'})
        if kind=='monthly':p['event_month']=day[:7]
        updated['verified_plays'].append(p)
    # Finalize winners only AFTER the entire generous approval window closes.
    # Daily champions require an actual LOCKED baseline; no starting score is
    # present in current Daily schedules, so we never invent one.
    newly_awarded=[]
    for (kind,day),ev in sorted(events.items()):
        _,_,cutoff=interval(kind,day)
        if now.astimezone(NY)<cutoff:continue
        attendees=[c for (k,d,_),c in matched.items() if k==kind and d==day]
        if not attendees:continue
        champion_type={'daily':'daily_champion','thursday':'thursday_champion',
                       'monthly':'gotm_champion'}[kind]
        if any(a.get('type')==champion_type and (
              (str(a.get('event_month') or '')==day[:7]) if kind=='monthly'
              else a.get('date')==day)
              for a in updated['awards'] if isinstance(a,dict)):continue
        if kind=='daily':
            baseline=ev.get('starting_champion_score')
            if type(baseline) is not int or baseline<0:continue
            leaders=[c for c in attendees if c['score']>baseline]
        else:
            # A weekly/monthly Champion is the highest qualifying score.
            max_score=max(c['score'] for c in attendees)
            leaders=[c for c in attendees if c['score']==max_score]
        for c in leaders:
            aid=f"{champion_type}:{day}:{c['player']}"
            award={'id':aid,'event_key':f"{kind}:{day}:{ev['game_id']}:{c['player']}",
               'type':champion_type,'name':{'daily':'Daily Champion',
                    'thursday':'Thursday Champion','monthly':'Game of the Month Champion'}[kind],
               'date':day,'player':c['player'],'game':ev['game'],
               'game_id':ev['game_id'],'score':c['score'],'score_id':c['score_id'],
               'verified_at':now.isoformat(),'verification_method':'approved_iscored_score_with_24h_generous_grace'}
            if kind=='monthly':award['event_month']=day[:7]
            updated['awards'].append(award)
            newly_awarded.append({'player':c['player'],'kind':kind,'date':day,'score':c['score']})
    report['new_championships']=newly_awarded
    for p in {c['player'] for c in proposed if c['kind']=='daily'}:
        issue_daily_milestones(updated,p,now)
    issue_other_milestones(updated,now)
    updated['awards'].sort(key=lambda a:(a.get('date',''),a.get('id','')))
    updated['verified_plays'].sort(key=lambda p:(p.get('date',''),p.get('event_key','')))
    changed=(updated!=ledger)
    return updated,report,changed

def main():
    from thursday_challenge import fetch
    enabled=os.environ.get('GENEROUS_CREDIT_ENABLED','false').strip().lower()=='true'
    ledger=load('verified-challenge-awards.json',{'schema_version':1,'awards':[],'verified_plays':[]})
    rows=fetch()
    archive=load('daily-champion-history.json',{'days':[]})
    live=load('daily-champion.json',{'days':[]})
    now=datetime.now(timezone.utc)
    previous_baselines=load('daily-champion-baselines.json',{})
    baselines=capture_daily_baselines(rows,archive,live,previous_baselines,now)
    if baselines!=previous_baselines:
        BASELINES.write_text(json.dumps(baselines,indent=2)+'\\n',encoding='utf-8')
    result,report,changed=process(rows,
      archive,
      live,
      load('thursday-challenge-state.json',{'weeks':{}}),
      load('monthly-challenge-live.json',{}),
      ledger,now,enabled=enabled,baselines=baselines)
    AUDIT.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    if changed:
        OUT.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print('Approval-window mode:',report['mode'])
    print('New participation:',report['new_participation_credits'])
    print('Championships finalized:',len(report['new_championships']))
    print('No OneSignal pushes or score-medal changes.')

if __name__=='__main__':main()
