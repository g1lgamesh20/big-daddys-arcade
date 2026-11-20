#!/usr/bin/env python3
"""Post-fix Daily/Thursday championship awards from approved iScored scores.

iScored confirmed that score dates now represent original submissions in
Central server time. The feed includes only approved scores, and exposes no
count of pending scores. The existing 24-hour *approval grace* is retained:
championships are assessed only after the whole Eastern event day plus 24h.
This protects typical late approvals but cannot guarantee that an approval
arriving after that window won't change a previously issued Thursday result.
Never silently change an existing Thursday champion; report a conflict.

Only events beginning at or after the Nov 20, 2026 Eastern cutover are
eligible for *new* championship awards. Earlier manually verified awards and
participation credits are immutable. No Monthly trophies or push messages.
"""
import json
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from generous_approval_credits import scheduled
from iscored_timestamp import parse_iscored_time
from submission_time_participation import CUTOVER, load

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'verified-challenge-awards.json'
REPORT = ROOT / 'postfix-champion-report.json'
NY = ZoneInfo('America/New_York')
GRACE = timedelta(hours=24)
KINDS = ('daily', 'thursday')
AWARD_TYPES = {'daily':'daily_champion', 'thursday':'thursday_champion'}

def window(day):
    start = datetime.combine(date.fromisoformat(day),time.min,tzinfo=NY)
    end = datetime.combine(date.fromisoformat(day)+timedelta(days=1),time.min,tzinfo=NY)
    return start,end,end+GRACE

def eligible_rows(rows, kind, day, gid, now):
    start,end,_ = window(day)
    best = {}
    malformed = 0
    for row in rows:
        if not isinstance(row,dict) or str(row.get('game') or '')!=gid:continue
        ts=parse_iscored_time(row.get('date'))
        if ts is None:
            # A score on the featured game with an unreadable date might be an
            # eligible winner. Do not choose a champion until it's resolved.
            malformed+=1
            continue
        if not (start<=ts<end) or ts>now:continue
        player=str(row.get('name') or '').strip().upper()[:48]
        sid=str(row.get('id') or '').strip()
        if not player or not sid or isinstance(row.get('score'),bool):continue
        try:score=int(row.get('score'))
        except (TypeError,ValueError):continue
        if score<0:continue
        item={'player':player,'score':score,'score_id':sid,'submitted_at_et':ts.isoformat()}
        previous=best.get(player)
        if previous is None or (score,-ts.timestamp(),sid)>(previous['score'],-datetime.fromisoformat(previous['submitted_at_et']).timestamp(),previous['score_id']):
            best[player]=item
    return list(best.values()),malformed

def finalize(rows, daily_archive, daily_live, thursday_state, baselines, ledger, now, enabled=False):
    """Pure deterministic award scan, returning ledger/report/changed."""
    if now.tzinfo is None:raise ValueError('now must be timezone-aware')
    if ledger.get('schema_version')!=1 or not isinstance(ledger.get('awards'),list) or not isinstance(ledger.get('verified_plays'),list):
        raise ValueError('Invalid permanent award ledger')
    now=now.astimezone(NY)
    events=scheduled(daily_archive,daily_live,thursday_state,{},baselines=baselines)
    updated=json.loads(json.dumps(ledger))
    report={'schema_version':1,'mode':'enabled' if enabled else 'preview',
            'policy':'postfix_original_submission_time_Eastern_event_day_plus_24h_approval_grace',
            'earliest_event_start_et':CUTOVER.isoformat(),
            'no_monthly_trophies_or_push':True,
            'pending_approval_visibility':'unavailable_from_public_iscored_feed',
            'evaluated_events':0,'events_waiting_for_grace':0,
            'events_missing_baseline':0,'events_held_bad_dates':0,
            'existing_champion_events':0,'thursday_result_conflicts':0,
            'new_daily_champions':0,'new_thursday_champions':0}
    # Award protection is based on event identity, not an API score update time.
    for (kind,day),ev in sorted(events.items()):
        if kind not in KINDS:continue
        start,end,ready=window(day)
        if start<CUTOVER:continue
        if now<ready:
            report['events_waiting_for_grace']+=1
            continue
        gid=str(ev.get('game_id') or '')
        if not gid:continue
        report['evaluated_events']+=1
        candidates,bad=eligible_rows(rows,kind,day,gid,now)
        if bad:
            report['events_held_bad_dates']+=1
            continue
        champions=[a for a in updated['awards'] if isinstance(a,dict)
                   and a.get('type')==AWARD_TYPES[kind] and a.get('date')==day]
        if kind=='daily':
            lock=baselines.get(day,{}) if isinstance(baselines,dict) else {}
            # Never infer a pre-event target retroactively from current scores.
            baseline=lock.get('starting_champion_score')
            observed=lock.get('observed_at')
            if (str(lock.get('game_id'))!=gid or type(baseline) is not int or baseline<0
                or lock.get('evidence')!='pre_start_approved_iscored_score_snapshot'):
                report['events_missing_baseline']+=1
                continue
            try: observed_time=datetime.fromisoformat(str(observed).replace('Z','+00:00'))
            except ValueError: observed_time=None
            if observed_time is None or observed_time.tzinfo is None or observed_time.astimezone(NY)>=start:
                report['events_missing_baseline']+=1
                continue
            for c in sorted(candidates,key=lambda x:(x['player'],x['score_id'])):
                if c['score']<=baseline:continue
                if any(str(a.get('player') or '').upper()==c['player'] for a in champions):continue
                award_id=f"daily_champion:{day}:{c['player']}"
                if any(a.get('id')==award_id for a in updated['awards']):continue
                award={'id':award_id,'event_key':f"daily:{day}:{gid}:{c['player']}",
                       'type':'daily_champion','name':'Daily Champion',
                       'date':day,'player':c['player'],'game_id':gid,
                       'game':ev.get('game') or '','score':c['score'],'score_id':c['score_id'],
                       'verified_at':now.isoformat(),
                       'original_submitted_at_et':c['submitted_at_et'],
                       'verification_method':'iscored_postfix_submission_time_and_locked_prestart_baseline',
                       'starting_champion_score':baseline,
                       'starting_champion_observed_at':observed,
                       'starting_champion_evidence':lock['evidence'],
                       'gold_level':True,
                       'win_rule':'strictly_greater_than_locked_starting_champion_score'}
                if enabled:
                    updated['awards'].append(award)
                    champions.append(award)
                report['new_daily_champions']+=1
        else:
            # One single Thursday Champion, as currently defined. Detect but
            # never silently overwrite an older winner if a late score appears.
            winner=sorted(candidates,key=lambda c:(-c['score'],c['submitted_at_et'],c['player']))[0] if candidates else None
            if champions:
                report['existing_champion_events']+=1
                if winner and not any(str(a.get('player') or '').upper()==winner['player']
                                      and int(a.get('score') or 0)==winner['score'] for a in champions):
                    report['thursday_result_conflicts']+=1
                continue
            if not winner:continue
            # Do not add a 2026-11-19 or older result: they precede cutover.
            award_id=f"thursday_champion:{day}"
            if any(a.get('id')==award_id for a in updated['awards']):continue
            award={'id':award_id,
                   'event_key':f"thursday:{day}:{gid}:{winner['player']}",
                   'type':'thursday_champion','name':'Thursday Champion',
                   'date':day,'player':winner['player'],'game_id':gid,
                   'game':ev.get('game') or '',
                   'score':winner['score'],'score_id':winner['score_id'],
                   'verified_at':now.isoformat(),
                   'original_submitted_at_et':winner['submitted_at_et'],
                   'verification_method':'iscored_postfix_submission_time_after_24h_approval_grace',
                   'grace_ended_at_et':ready.isoformat()}
            if enabled:updated['awards'].append(award)
            report['new_thursday_champions']+=1
    if enabled and updated!=ledger:
        updated['awards'].sort(key=lambda x:(str(x.get('date') or ''),str(x.get('id') or '')))
    return updated if enabled else ledger,report,enabled and updated!=ledger

def main():
    from thursday_challenge import fetch
    rows=fetch()
    result,report,changed=finalize(
        rows,
        load('daily-champion-history.json',{'days':[]}),
        load('daily-champion.json',{'days':[]}),
        load('thursday-challenge-state.json',{'weeks':{}}),
        load('daily-champion-baselines.json',{}),
        load('verified-challenge-awards.json',{'schema_version':1,'awards':[],'verified_plays':[]}),
        datetime.now(timezone.utc),enabled=True)
    REPORT.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    if changed:OUT.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print('New Daily Champion trophies:',report['new_daily_champions'])
    print('New Thursday Champion trophies:',report['new_thursday_champions'])
    if report['thursday_result_conflicts']:
        print('WARNING: late approved Thursday score disagrees with saved winner; review needed.')
    print('No monthly awards, iScored medals, or OneSignal notifications.')
if __name__=='__main__':main()
