#!/usr/bin/env python3
"""Prospective empty-game observations; first Gold only after a prior empty snapshot."""
import copy,json
from datetime import datetime,timezone
from pathlib import Path
from golden_encore import snapshot
from personal_best_preview import ROOT
STATE=ROOT/'treasure-hunter-state.json'
CATALOG=ROOT/'monthly-game-catalog.json'
def evaluate(rows,catalog,prior,now):
    if now.tzinfo is None:raise ValueError('Timezone required')
    if not isinstance(catalog,dict) or not isinstance(catalog.get('games'),dict):raise ValueError('Invalid game catalog')
    if prior is not None and (not isinstance(prior,dict) or prior.get('schema_version')!=1 or not isinstance(prior.get('empty_games'),dict) or not isinstance(prior.get('first_gold'),list) or not isinstance(prior.get('seen_scored_games'),list)):raise ValueError('Invalid prospective state')
    current=snapshot(rows);scored=set(current)
    state=copy.deepcopy(prior) if prior is not None else {'schema_version':1,'empty_games':{},'first_gold':[],'seen_scored_games':[]}
    seen=set(state['seen_scored_games']);events={str(x.get('game_id')) for x in state['first_gold']}
    nowstr=now.astimezone(timezone.utc).isoformat()
    # Never consider any game that had a score on initial observation.
    for gid,name in sorted(catalog['games'].items()):
        gid=str(gid)
        if gid not in scored and gid not in seen and gid not in events and gid not in state['empty_games'] and str(name).strip().casefold()!='test game':
            state['empty_games'][gid]={'game':str(name),'observed_empty_at':nowstr}
    if prior is not None:
        for gid,champion in sorted(current.items()):
            empty=state['empty_games'].get(gid)
            if not empty or gid in events or str(champion['game']).strip().casefold()=='test game':continue
            winners=champion['winning_scores']
            if not winners:continue
            state['first_gold'].append({'game_id':gid,'game':champion['game'],'score':champion['score'],
                'holders':list(champion['holders']),'winning_scores':copy.deepcopy(winners),
                'observed_empty_at':empty['observed_empty_at'],'observed_gold_at':nowstr})
            events.add(gid);del state['empty_games'][gid]
    seen.update(scored);state['seen_scored_games']=sorted(seen)
    return state
def sync(rows,now=None):
    now=now or datetime.now(timezone.utc)
    catalog=json.loads(CATALOG.read_text(encoding='utf-8'))
    prior=json.loads(STATE.read_text(encoding='utf-8')) if STATE.exists() else None
    state=evaluate(rows,catalog,prior,now)
    if state!=prior:STATE.write_text(json.dumps(state,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print('Treasure Hunter prospective empty games:',len(state['empty_games']),'first Gold events:',len(state['first_gold']))
if __name__=='__main__':raise SystemExit('Run through update_legends.py using the approved score feed')
