#!/usr/bin/env python3
"""JUST IN TIME: verified Daily Challenge winning score in final five ET minutes."""
import json
from datetime import datetime,timedelta,time
from zoneinfo import ZoneInfo
from personal_best_preview import JOURNAL,CUTOFF,timestamp
from generous_approval_credits import BASELINES
from pathlib import Path
from personal_best_preview import ROOT
HISTORY=ROOT/'daily-champion-history.json'
ET=ZoneInfo('America/New_York')
def preview(journal,history,baselines):
    if not isinstance(journal,dict) or journal.get('schema_version')!=1 or journal.get('policy')!='post_2026_11_19_approved_iscored_scores' or not isinstance(journal.get('scores'),dict):raise ValueError('Invalid approved journal')
    if not isinstance(history,dict) or history.get('schema_version')!=1 or history.get('timezone')!='America/New_York' or not isinstance(history.get('days'),list) or not isinstance(baselines,dict):raise ValueError('Invalid Daily history/baselines')
    days={}
    for entry in history['days']:
        if not isinstance(entry,dict) or not isinstance(entry.get('date'),str) or not isinstance(entry.get('game_id'),str):raise ValueError('Malformed Daily selection')
        day=entry['date']
        if day in days and days[day]['game_id']!=entry['game_id']:raise ValueError('Conflicting Daily selection')
        days[day]=entry
    candidates=[]
    for sid,row in journal['scores'].items():
        if not isinstance(row,dict) or str(row.get('score_id'))!=str(sid):raise ValueError('Invalid score ID')
        player,gid,score=row.get('name'),row.get('game'),row.get('score')
        if not isinstance(player,str) or not player or player!=player.strip().upper() or not isinstance(gid,str) or not gid or type(score)!=int or score<0:raise ValueError('Malformed score evidence')
        submitted=timestamp(row['date']);observed=timestamp(row['first_observed_at'])
        if submitted<CUTOFF or submitted>observed:raise ValueError('Invalid score timestamps')
        local=submitted.astimezone(ET);day=local.date().isoformat()
        if local.hour!=23 or local.minute<55:continue
        entry=days.get(day);baseline=baselines.get(day)
        if not entry or not baseline or gid!=entry['game_id'] or gid!=baseline.get('game_id'):continue
        locked=baseline.get('starting_champion_score')
        if type(locked)!=int or locked<0 or score<=locked:continue
        start=datetime.combine(local.date(),time.min,tzinfo=ET)
        observed_baseline=timestamp(baseline['observed_at'])
        if observed_baseline>=start:continue
        if str(entry.get('game','')).strip().casefold()=='test game':continue
        candidates.append({'player':player,'day':day,'game_id':gid,'game':entry.get('game',''),
                           'score_id':str(sid),'score':score,'starting_champion_score':locked,
                           'submitted_at_et':local.isoformat(),'baseline_observed_at':observed_baseline.isoformat()})
    earliest={}
    for c in sorted(candidates,key=lambda x:(x['submitted_at_et'],x['score_id'])):earliest.setdefault(c['player'],c)
    return {'mode':'PREVIEW_ONLY_NO_AWARDS','candidates':sorted(earliest.values(),key=lambda x:x['player'])}
def main():
    result=preview(json.loads(JOURNAL.read_text()),json.loads(HISTORY.read_text()),json.loads(BASELINES.read_text()))
    print('JUST IN TIME evidence preview (NO awards or pushes):',len(result['candidates']),'eligible players')
if __name__=='__main__':main()
