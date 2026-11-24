#!/usr/bin/env python3
"""Finalize a previously REVEALED Game of the Month at 9 AM Eastern on the 2nd.

The operator assumes responsibility for approving all scores submitted before
midnight by the 9 AM results announcement. iScored's public feed includes only
approved scores; it cannot independently prove that no pending scores remain.
The recorded all_pending_resolved flag represents THIS EXPLICIT OPERATOR POLICY,
not an API pending-queue query. Do not execute before the policy is fulfilled.

No sealed game selection is opened. Both files are committed in the same Git
transaction before any push. Previously finalized results never change.
"""
import json
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from generous_approval_credits import capture_monthly_reveals
from iscored_timestamp import parse_iscored_time
from submission_time_participation import load
from unified_milestone_awards import issue as issue_other_milestones

ROOT=Path(__file__).resolve().parents[1]
LEDGER=ROOT/'verified-challenge-awards.json'
FINAL=ROOT/'monthly-final-results.json'
REPORT=ROOT/'monthly-finalization-report.json'
NY=ZoneInfo('America/New_York')

def previous_month(now):
    year,month=now.year,now.month
    return f'{year-1 if month==1 else year:04d}-{12 if month==1 else month-1:02d}'

def boundaries(month):
    y,m=map(int,month.split('-'))
    start=datetime(y,m,1,tzinfo=NY)
    end=datetime(y+(m==12),m%12+1,1,tzinfo=NY)
    return start,end

def finalize(rows, archive, ledger, final, now, enabled=False):
    if now.tzinfo is None:raise ValueError('Aware timestamp required')
    now=now.astimezone(NY)
    report={'schema_version':1,'mode':'enabled' if enabled else 'preview',
            'status':'not_ready','scope':'previous_revealed_month_only',
            'policy':'operator_all_submissions_approved_before_2nd_9AM_Eastern',
            'no_pending_feed':'operator_responsibility_not_api_verified',
            'no_sealed_game_access':True,'no_push_sent':True,
            'participation_added':0,'awards_added':0}
    if now.day!=2 or now.hour<9:return ledger,final,report,False
    if ledger.get('schema_version')!=1 or not isinstance(ledger.get('awards'),list) or not isinstance(ledger.get('verified_plays'),list):
        raise ValueError('Invalid verified ledger')
    if final.get('schema_version')!=1 or not isinstance(final.get('months'),dict):
        raise ValueError('Invalid monthly final archive')
    if archive.get('schema_version')!=1 or not isinstance(archive.get('months'),dict):
        raise ValueError('Missing public monthly reveal archive')
    month=previous_month(now)
    if month<'2026-12':return ledger,final,report,False
    report['month']=month
    old=final['months'].get(month)
    if old is not None:
        if old.get('status')!='final_verified':raise ValueError('Existing monthly final state is not final')
        report['status']='already_final'
        return ledger,final,report,False
    published=archive['months'].get(month)
    if not isinstance(published,dict):
        report['status']='missing_revealed_month';return ledger,final,report,False
    gid=str(published.get('game_id') or '')
    game=str(published.get('game') or '')
    record=published.get('starting_record')
    target=published.get('benchmark')
    if not gid or not game or type(record) is not int or record<0 or type(target) is not int or target!=(record*3+3)//4:
        report['status']='missing_valid_locked_public_benchmark'
        return ledger,final,report,False
    start,end=boundaries(month)
    best={}
    bad=0
    for r in rows:
        if not isinstance(r,dict) or str(r.get('game') or '')!=gid:continue
        ts=parse_iscored_time(r.get('date'))
        if ts is None:
            bad+=1;continue
        if not(start<=ts<end) or ts>now:continue
        player=str(r.get('name') or '').strip().upper()[:48]
        sid=str(r.get('id') or '').strip()
        if not player or not sid or isinstance(r.get('score'),bool):continue
        try: score=int(r.get('score'))
        except (TypeError,ValueError):continue
        if score<0:continue
        item={'player':player,'score':score,'score_id':sid,'submitted_at_et':ts.isoformat()}
        previous=best.get(player)
        if previous is None or (score,-ts.timestamp(),sid)>(previous['score'],-datetime.fromisoformat(previous['submitted_at_et']).timestamp(),previous['score_id']):
            best[player]=item
    if bad:
        report['status']='unparseable_dates_hold'
        report['unparseable_same_game_rows']=bad
        return ledger,final,report,False
    ordered=sorted(best.values(),key=lambda x:(-x['score'],x['submitted_at_et'],x['player']))
    # One score per person; competition ranks respect ties: 1,1,3.
    standings=[]
    last=None
    rank=0
    for pos,c in enumerate(ordered,1):
        if c['score']!=last: rank=pos
        last=c['score']
        standings.append({**c,'rank':rank})
    podium=[{'player':c['player'],'score':c['score'],'rank':c['rank']}
            for c in standings if c['rank']<=3]
    # Sender currently has a 20-person safe podium cap. Hold instead of
    # writing data that cannot pass its safety validation.
    if len(podium)>20:
        report['status']='too_many_podium_ties';return ledger,final,report,False
    if any(len(p['player'])>3 or not all(c.isupper() or c.isdigit() or c==' ' for c in p['player']) for p in podium):
        report['status']='unsupported_podium_handle';return ledger,final,report,False
    # Exact arithmetic mean of each verified entrant's best qualifying score.\n    # Integer cross-multiplication avoids floating-point rounding at the boundary.\n    entrant_count=len(standings)\n    total_best_scores=sum(c['score'] for c in standings)\n    final_record={'status':'final_verified',
                  'eligibility_source':'original_submission_timestamps_verified',
                  'all_pending_resolved':True,
                  'approval_attestation':'operator_assumes_all_eligible_scores_approved_by_2nd_9am_ET',
                  'game_id':gid,'game':game,'starting_record':record,
                  'locked_benchmark':target,'finalized_at':now.isoformat(),
                  'submission_cutoff_et':end.isoformat(),
                  'podium':podium,'no_verified_entrants':not bool(standings),
                  'entrant_count':entrant_count,\n                  'player_average_eligible':entrant_count>=3,\n                  'player_average_score_sum':total_best_scores if entrant_count>=3 else None,\n                  'player_average_score_count':entrant_count if entrant_count>=3 else None}
    result=json.loads(json.dumps(ledger))
    already={(p.get('kind'),str(p.get('date') or '')[:7],str(p.get('player') or '').upper())
             for p in result['verified_plays'] if isinstance(p,dict)}
    for c in standings:
        key=('monthly',month,c['player'])
        if key in already:continue
        result['verified_plays'].append({
            'event_key':f"monthly:{month}-01:{gid}:{c['player']}",
            'kind':'monthly','date':month+'-01','event_month':month,
            'player':c['player'],'game_id':gid,'game':game,
            'score':c['score'],'score_id':c['score_id'],
            'original_submitted_at_et':c['submitted_at_et'],
            'verified_at':now.isoformat(),'trophy_issued':False,
            'verification_method':'iscored_postfix_original_submission_9am_operator_approval'})
        report['participation_added']+=1
        already.add(key)
    seen={a.get('id') for a in result['awards'] if isinstance(a,dict)}
    for c in standings:
        base={'event_key':f"monthly:{month}-01:{gid}:{c['player']}",
              'date':month+'-01','event_month':month,
              'player':c['player'],'game_id':gid,'game':game,'score':c['score'],
              'score_id':c['score_id'],'original_submitted_at_et':c['submitted_at_et'],
              'verified_at':now.isoformat(),
              'verification_method':'iscored_postfix_original_submission_9am_operator_approval'}
        candidates=[]
        if c['rank']==1:
            candidates.append(('gotm_champion','Game of the Month Champion',{}))
        if c['rank']<=3:
            candidates.append((f"gotm_podium_{c['rank']}",{1:'Monthly Gold',2:'Monthly Silver',3:'Monthly Bronze'}[c['rank']],{'rank':c['rank']}))
        if c['score']>target:
            candidates.append(('gotm_beat_average','Beat the Benchmark',
                               {'starting_record':record,'locked_benchmark':target,
                                'comparison':'strictly_greater_than_locked_75_percent_benchmark'}))\n        if entrant_count>=3 and c['score']*entrant_count>total_best_scores:\n            candidates.append(('gotm_beat_player_average','Beat the Average',\n                               {'average_score_sum':total_best_scores,\n                                'average_score_count':entrant_count,\n                                'comparison':'strictly_greater_than_final_verified_player_mean'}))
        for typ,name,extra in candidates:
            aid=f"{typ}:{month}-01:{c['player']}"
            if aid in seen:continue
            result['awards'].append({'id':aid,'type':typ,'name':name,**base,**extra})
            seen.add(aid)
            report['awards_added']+=1
    before=len(result['awards'])
    issue_other_milestones(result,now)
    report['awards_added']+=len(result['awards'])-before
    result['verified_plays'].sort(key=lambda x:(str(x.get('date','')),str(x.get('event_key',''))))
    result['awards'].sort(key=lambda x:(str(x.get('date','')),str(x.get('id',''))))
    output=json.loads(json.dumps(final))
    output['months'][month]=final_record
    report['status']='finalized' if enabled else 'preview_finalizable'
    report['entrant_count']=len(standings)
    report['podium_places']=len(podium)
    return (result,output,report,True) if enabled else (ledger,final,report,False)

def main():
    from thursday_challenge import fetch
    now=datetime.now(timezone.utc)
    result,final,report,changed=finalize(
        fetch(),
        load('published-monthly-challenge-history.json',{'schema_version':1,'months':{}}),
        load('verified-challenge-awards.json',{'schema_version':1,'awards':[],'verified_plays':[]}),
        load('monthly-final-results.json',{'schema_version':1,'months':{}}),
        now,enabled=True)
    REPORT.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    if changed:
        LEDGER.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
        FINAL.write_text(json.dumps(final,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print('Monthly finalization status:',report['status'])
    print('New verified participation:',report['participation_added'])
    print('New awards:',report['awards_added'])
    print('No push sent here; existing notification workflow handles dispatch.')

if __name__=='__main__':main()
