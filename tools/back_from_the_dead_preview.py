#!/usr/bin/env python3
"""Read-only BACK FROM THE DEAD evidence. No awards, writes or notifications."""
import json
from collections import defaultdict
from datetime import datetime,timezone
from gold_holder_history import HISTORY
from personal_best_preview import JOURNAL,CUTOFF,timestamp

def preview(journal,history):
    if (not isinstance(journal,dict) or journal.get('schema_version')!=1 or journal.get('policy')!='post_2026_11_19_approved_iscored_scores' or not isinstance(journal.get('scores'),dict)):
        raise ValueError('Invalid approved score journal')
    if (not isinstance(history,dict) or history.get('schema_version')!=1 or history.get('policy')!='observed_approved_snapshots_only' or not isinstance(history.get('transitions'),list)):
        raise ValueError('Invalid Gold history')
    scores={}
    for sid,row in journal['scores'].items():
        if not isinstance(row,dict) or str(row.get('score_id'))!=str(sid):
            raise ValueError('Malformed approved score')
        name,game,score=row.get('name'),row.get('game'),row.get('score')
        if not isinstance(name,str) or not name or name!=name.strip().upper() or not isinstance(game,str) or not game or type(score)!=int or score<0:
            raise ValueError('Malformed score fields')
        submitted=timestamp(row['date']);observed=timestamp(row['first_observed_at'])
        if submitted<CUTOFF or submitted>observed:raise ValueError('Invalid score timing')
        scores[str(sid)]=(name,game,score,submitted,observed)
    by_game=defaultdict(list);seen=set()
    for event in history['transitions']:
        if not isinstance(event,dict) or not isinstance(event.get('id'),str) or not event['id'] or event['id'] in seen or event.get('type') not in ('takeover','tie_joined'):
            raise ValueError('Invalid Gold transition')
        seen.add(event['id'])
        for key in ('previous_holders','new_holders','gained_holders','lost_holders','new_score_ids'):
            if not isinstance(event.get(key),list):raise ValueError('Malformed holder/score list')
        before,after=event.get('previous_score'),event.get('new_score')
        if type(before)!=int or type(after)!=int or before<0 or after<before or (event['type']=='takeover' and after<=before):
            raise ValueError('Invalid Gold transition scores')
        observed=timestamp(event['observed_at'])
        by_game[str(event['game_id'])].append((observed,event))
    candidates=[]
    for gid,events in by_game.items():
        events.sort(key=lambda x:(x[0],x[1]['id']))
        losses={}
        for observed,event in events:
            if event['type']!='takeover':continue
            for player in event['lost_holders']:
                if not isinstance(player,str) or not player or player!=player.strip().upper():raise ValueError('Invalid lost holder')
                losses[player]=event
            for player in event['gained_holders']:
                if not isinstance(player,str) or not player or player!=player.strip().upper():raise ValueError('Invalid gained holder')
                loss=losses.get(player)
                if loss is None or timestamp(loss['observed_at'])>=observed:continue
                winners=[]
                for sid in event['new_score_ids']:
                    row=scores.get(str(sid))
                    if row and row[0]==player and row[1]==gid and row[2]==event['new_score'] and row[3]>timestamp(loss['observed_at']) and row[3]<=observed and row[4]<=observed:
                        winners.append((row[3],str(sid)))
                if not winners:continue
                _,sid=min(winners)
                candidates.append({'id':'back_from_the_dead:'+player,'player':player,'game_id':gid,'game':event.get('game',''),'lost_event_id':loss['id'],'reclaimed_event_id':event['id'],'reclaimed_score_id':sid,'reclaimed_score':event['new_score'],'submitted_at':scores[sid][3].isoformat()})
                losses.pop(player,None)
    earliest={}
    for item in sorted(candidates,key=lambda x:(x['submitted_at'],x['reclaimed_score_id'],x['game_id'])):
        earliest.setdefault(item['player'],item)
    return {'mode':'PREVIEW_ONLY_NO_AWARDS','observed_gold_transitions':len(seen),'candidates':sorted(earliest.values(),key=lambda x:x['player'])}

def main():
    result=preview(json.loads(JOURNAL.read_text(encoding='utf-8')),json.loads(HISTORY.read_text(encoding='utf-8')))
    print('BACK FROM THE DEAD evidence preview (NO awards or pushes):',result['observed_gold_transitions'],'Gold transitions,',len(result['candidates']),'eligible players')
    for item in result['candidates']:print('  Candidate:',item['player'],item['game'],item['reclaimed_score_id'])
if __name__=='__main__':main()
