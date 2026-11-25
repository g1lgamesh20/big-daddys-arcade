#!/usr/bin/env python3
"""Verify first Gold on a prospectively observed empty game, never historical backfill."""
import json
from treasure_hunter_state import STATE
from personal_best_preview import JOURNAL,timestamp,CUTOFF
def preview(journal,state):
    if not isinstance(journal,dict) or journal.get('schema_version')!=1 or journal.get('policy')!='post_2026_11_19_approved_iscored_scores' or not isinstance(journal.get('scores'),dict):raise ValueError('Invalid approved journal')
    if not isinstance(state,dict) or state.get('schema_version')!=1 or not isinstance(state.get('first_gold'),list):raise ValueError('Invalid prospective Gold state')
    candidates=[];seen_games=set()
    for event in state['first_gold']:
        gid=str(event['game_id'])
        if gid in seen_games:raise ValueError('Duplicate first Gold event')
        seen_games.add(gid)
        if str(event.get('game','')).strip().casefold()=='test game':continue
        empty=timestamp(event['observed_empty_at']);gold=timestamp(event['observed_gold_at'])
        if empty>=gold or type(event['score'])!=int or event['score']<0:raise ValueError('Invalid Gold observation')
        for winner in event['winning_scores']:
            sid=str(winner['score_id']);row=journal['scores'].get(sid)
            if row is None:continue
            if str(row.get('score_id'))!=sid or row.get('name')!=winner['player'] or row.get('game')!=gid or row.get('score')!=event['score'] or winner['player'] not in event['holders']:continue
            submitted=timestamp(row['date']);observed=timestamp(row['first_observed_at'])
            if submitted<CUTOFF or submitted<=empty or submitted>observed or observed>gold:continue
            candidates.append({'player':winner['player'],'game_id':gid,'game':event['game'],
                'score_id':sid,'score':event['score'],'submitted_at':submitted.isoformat(),
                'observed_empty_at':empty.isoformat(),'observed_gold_at':gold.isoformat()})
    earliest={}
    for c in sorted(candidates,key=lambda x:(x['submitted_at'],x['score_id'])):earliest.setdefault(c['player'],c)
    return {'mode':'PREVIEW_ONLY_NO_AWARDS','candidates':sorted(earliest.values(),key=lambda x:x['player'])}
def main():
    result=preview(json.loads(JOURNAL.read_text()),json.loads(STATE.read_text()))
    print('TREASURE HUNTER evidence preview (NO awards or pushes):',len(result['candidates']),'eligible players')
if __name__=='__main__':main()
