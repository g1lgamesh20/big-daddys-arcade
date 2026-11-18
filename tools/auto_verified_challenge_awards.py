#!/usr/bin/env python3
"""One-approval iScored -> Hall of Legends automatic challenge evidence.

Controlled November 18, 2026 testing found that unapproved submissions are absent
from the public API, but API date values track approval time (apparently ~1 hour
behind Eastern in November), NOT reliable original submission time.
The default remains PREVIEW ONLY and enabling awards is HARD-BLOCKED until a
verifiable independent original-submission-time source is integrated.

Never sends push messages or changes medals. Award only uniquely matching
final Thursday Champion results after 24h grace. Daily score participation
is recorded as verified play, NOT a Daily winner/trophy.
"""
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from thursday_challenge import parse_time, fetch as fetch_scores
from verify_challenge_award import ROOT, OUT, read

NY=ZoneInfo('America/New_York')
PENDING=ROOT/'challenge-award-candidates.json'
WINNERS=ROOT/'thursday-winners.json'
PREVIEW=ROOT/'challenge-auto-awards-preview.json'

def truth(value):
    return str(value).strip().lower() in ('true','1','yes')

def live_by_event(rows):
    out={}
    bad_dates=0
    for row in rows:
        if not isinstance(row,dict):continue
        gid=str(row.get('game') or '')
        player=str(row.get('name') or '').strip().upper()[:48]
        sid=str(row.get('id') or '')
        if not gid or not player or not sid:continue
        when=parse_time(row.get('date'))
        if when is None:
            bad_dates+=1
            continue
        score=row.get('score')
        if isinstance(score,bool):continue
        try:score=int(score)
        except (ValueError,TypeError):continue
        if score<0:continue
        day=when.astimezone(NY).date().isoformat()
        key=(day,gid)
        out.setdefault(key,[]).append({
          'player':player,'score':score,'score_id':sid,
          'submitted_at_assumed_et':when.isoformat()
        })
    return out,bad_dates

def build(rows, pending, winners, ledger, now, enabled=False):
    # SECURITY: Public iScored 'date' has behaved as APPROVAL time in controlled
    # tests. Candidate histories and Thursday winner archives were derived from
    # the same field, so cross-matching them cannot prove a pre-midnight submit.
    # Do not enable awards (including daily verified plays) until original
    # submission evidence is independently collected and verified per score.
    if enabled:
        raise ValueError(
            'Automatic challenge awards BLOCKED: iScored API date reflects '
            'approval time, not proven original submission time. No awards '
            'can be issued until independent submission-time verification '
            'is implemented. Leave AUTO_CHALLENGE_AWARDS_ENABLED unset.'
        )
    now=now.astimezone(NY)
    if not isinstance(pending.get('candidates'),list) or not isinstance(winners.get('weeks'),list):
        raise ValueError('Invalid candidate or Thursday winner archive')
    if ledger.get('schema_version')!=1 or not isinstance(ledger.get('awards'),list) or not isinstance(ledger.get('verified_plays'),list):
        raise ValueError('Invalid permanent trophy ledger')
    lookup,bad_dates=live_by_event(rows)
    candidate_index={}
    for c in pending['candidates']:
        if not isinstance(c,dict):continue
        key=(c.get('kind'),c.get('date'),str(c.get('game_id')),c.get('player'),str(c.get('score_id')))
        candidate_index[key]=c

    awards=list(ledger['awards'])
    plays=list(ledger['verified_plays'])
    seen_awards={a.get('id') for a in awards}
    seen_plays={p.get('event_key') for p in plays}
    existing_by_day={a.get('date'):a for a in awards if a.get('type')=='thursday_champion'}
    eligible_thursday=[]
    blocked=[]

    for event in winners['weeks']:
        if not isinstance(event,dict) or event.get('status')!='final':continue
        day=event.get('week')
        gid=str(event.get('game_id') or '')
        if not isinstance(day,str) or len(day)!=10 or not gid:continue
        try:date=datetime.strptime(day,'%Y-%m-%d').replace(tzinfo=NY)
        except ValueError:continue
        # 24h grace after event closes. Existing award remains immutable.
        if now < date+timedelta(days=2):continue
        award_id='thursday_champion:'+day
        if award_id in seen_awards:continue
        if day in existing_by_day:
            blocked.append(day+':conflicting_record')
            continue
        best=lookup.get((day,gid),[])
        if not best:
            blocked.append(day+':no_live_feed_score')
            continue
        maximum=max(x['score'] for x in best)
        leaders={x['player'] for x in best if x['score']==maximum}
        if len(leaders)!=1:
            blocked.append(day+':tie_requires_rule_review')
            continue
        winner=event.get('winner')
        if not isinstance(winner,dict):
            blocked.append(day+':no_archived_winner')
            continue
        player=str(winner.get('player') or '').strip().upper()
        if player not in leaders or winner.get('score')!=maximum:
            blocked.append(day+':archive_live_mismatch')
            continue
        evidence=[x for x in best if x['player']==player and x['score']==maximum
             and candidate_index.get(('thursday',day,gid,player,x['score_id']))]
        if not evidence:
            blocked.append(day+':missing_matching_candidate')
            continue
        best_proof=sorted(evidence,key=lambda x:x['score_id'])[0]
        c=candidate_index[('thursday',day,gid,player,best_proof['score_id'])]
        if c.get('best_score')!=maximum or c.get('awarded') is not False:
            blocked.append(day+':candidate_mismatch')
            continue
        eligible_thursday.append({
           'id':award_id,
           'event_key':'thursday:'+day+':'+gid+':'+player,
           'type':'thursday_champion','name':'Thursday Champion',
           'date':day,'player':player,'game':str(event.get('game') or c.get('game') or ''),
           'game_id':gid,'score':maximum,'score_id':best_proof['score_id'],
           'verified_at':now.isoformat(),
           'verification_method':'public_iscored_approved_feed_live_match',
        })

    eligible_daily=[]
    for c in pending['candidates']:
        if not isinstance(c,dict) or c.get('kind')!='daily':continue
        day=c.get('date')
        gid=str(c.get('game_id') or '')
        player=str(c.get('player') or '').strip().upper()
        sid=str(c.get('score_id') or '')
        if not isinstance(day,str) or not gid or not player or not sid:continue
        key='daily:'+day+':'+gid+':'+player
        if key in seen_plays:continue
        matches=[x for x in lookup.get((day,gid),[]) if x['player']==player
           and x['score_id']==sid and x['score']==c.get('best_score')]
        if len(matches)!=1:continue
        eligible_daily.append({'event_key':key,'kind':'daily','date':day,
          'player':player,'game_id':gid,'game':str(c.get('game') or ''),
          'score':matches[0]['score'],'score_id':sid,'verified_at':now.isoformat(),
          'trophy_issued':False})

    preview={'schema_version':1,'mode':'enabled' if enabled else 'preview_only',
       'generated_at':now.isoformat(),
       'approval_source':'public_iScored_feed_only_after_operator_approval_tested_2026-11-18',
       'timestamp_note':'iScored API date appears to reflect approval time; NOT valid original submission evidence',
       'release_blocker':'No independent original submission timestamp; potential matches below are diagnostic only, not award-eligible',
       'eligible_new_thursday_trophies':0,
       'eligible_new_daily_play_records':0,
       'potential_thursday_matches_without_submission_proof':len(eligible_thursday),
       'potential_daily_matches_without_submission_proof':len(eligible_daily),
       'blocked_thursday_events':blocked,
       'unparseable_feed_dates':bad_dates,
       'notifications_sent':False}
    if not enabled:return ledger,preview,False
    if bad_dates:
        raise ValueError('Unparseable live feed dates; refusing automated award')
    awards.extend(eligible_thursday)
    plays.extend(eligible_daily)
    next_ledger={**ledger,'awards':sorted(awards,key=lambda a:(a['date'],a['id'])),
          'verified_plays':sorted(plays,key=lambda a:(a['date'],a['event_key']))}
    return next_ledger,preview,bool(eligible_thursday or eligible_daily)

def main():
    enabled=truth(os.environ.get('AUTO_CHALLENGE_AWARDS_ENABLED','false'))
    candidates=read(PENDING,{'candidates':[]})
    winners=read(WINNERS,{'weeks':[]})
    ledger=read(OUT,{'schema_version':1,'awards':[],'verified_plays':[]})
    rows=fetch_scores()
    output,preview,changed=build(rows,candidates,winners,ledger,
        datetime.now(timezone.utc),enabled=enabled)
    PREVIEW.write_text(json.dumps(preview,indent=2)+'\n',encoding='utf-8')
    if enabled and changed:
        OUT.write_text(json.dumps(output,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print('Automation mode:',preview['mode'])
    print('New eligible Thursday trophies:',preview['eligible_new_thursday_trophies'])
    print('New eligible Daily play records:',preview['eligible_new_daily_play_records'])
    print('Blocked Thursday events:',len(preview['blocked_thursday_events']))
    print('No push notifications sent. No Daily winner awards inferred.')

if __name__=='__main__':main()
