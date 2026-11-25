#!/usr/bin/env python3
"""Conservative PHOTO FINISH preview using observed Gold baselines, not inferred past records."""
import json
from personal_best_preview import JOURNAL,CUTOFF,timestamp
from gold_holder_history import HISTORY
def preview(journal,history):
    if not isinstance(journal,dict) or journal.get('schema_version')!=1 or journal.get('policy')!='post_2026_11_19_approved_iscored_scores' or not isinstance(journal.get('scores'),dict):raise ValueError('Invalid approved score journal')
    if not isinstance(history,dict) or history.get('schema_version')!=1 or history.get('policy')!='observed_approved_snapshots_only' or not isinstance(history.get('holders_by_game'),dict) or not isinstance(history.get('transitions'),list):raise ValueError('Invalid Gold history')
    # Only currently observed Gold snapshots: never reconstruct unobserved historical values.
    # Exclude games with transitions after the current observation.
    latest={}
    for e in history['transitions']:
        if not isinstance(e,dict) or not e.get('game_id') or not e.get('observed_at'):raise ValueError('Malformed transition')
        gid=str(e['game_id']);t=timestamp(e['observed_at'])
        if gid not in latest or t>latest[gid]:latest[gid]=t
    candidates=[]
    for sid,row in journal['scores'].items():
        if not isinstance(row,dict) or str(row.get('score_id'))!=str(sid):raise ValueError('Invalid score ID')
        player,gid,score=row.get('name'),row.get('game'),row.get('score')
        if not isinstance(player,str) or not player or player!=player.strip().upper() or not isinstance(gid,str) or not gid or type(score)!=int or score<0:raise ValueError('Malformed score')
        submitted=timestamp(row['date']);first=timestamp(row['first_observed_at'])
        if submitted<CUTOFF or submitted>first:raise ValueError('Invalid score timestamps')
        gold=history['holders_by_game'].get(gid)
        if gold is None:continue
        if not isinstance(gold,dict) or type(gold.get('score'))!=int or gold['score']<0 or not isinstance(gold.get('holders'),list) or not isinstance(gold.get('winning_scores'),list):raise ValueError('Malformed Gold baseline')
        observed=timestamp(gold['observed_at'])
        # The record must have been observed before submission, and still be the
        # recorded champion when this approved score was first observed.
        if submitted<=observed or latest.get(gid,observed)>observed:continue
        if str(gold.get('game','')).strip().casefold()=='test game':continue
        record=gold['score']
        # Integer-safe: 0 < record-score <= 1% of record.
        if record>0 and score<record and 100*(record-score)<=record and player not in gold['holders']:
            candidates.append({'player':player,'game_id':gid,'game':gold.get('game',''),'score_id':str(sid),'score':score,'gold_score':record,'gold_observed_at':observed.isoformat(),'submitted_at':submitted.isoformat()})
    earliest={}
    for x in sorted(candidates,key=lambda x:(x['submitted_at'],x['score_id'])):earliest.setdefault(x['player'],x)
    return {'mode':'PREVIEW_ONLY_NO_AWARDS','candidates':sorted(earliest.values(),key=lambda x:x['player'])}
def main():
    result=preview(json.loads(JOURNAL.read_text()),json.loads(HISTORY.read_text()))
    print('PHOTO FINISH evidence preview (NO awards or pushes):',len(result['candidates']),'eligible players')
if __name__=='__main__':main()
