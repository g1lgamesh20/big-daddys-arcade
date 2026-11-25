#!/usr/bin/env python3
"""DOUBLE TROUBLE: two verified new Gold takeovers on distinct games in one ET day."""
import json
from collections import defaultdict
from datetime import timezone
from zoneinfo import ZoneInfo
from back_from_the_dead_preview import preview as validate_comeback_evidence
from gold_holder_history import HISTORY
from personal_best_preview import JOURNAL,timestamp,CUTOFF
ET=ZoneInfo('America/New_York')
def preview(journal,history):
    # Reuse strict structural and timestamp validation for both permanent sources.
    validate_comeback_evidence(journal,history)
    approved=journal['scores'];by_day=defaultdict(dict)
    for event in history['transitions']:
        if event['type']!='takeover':continue
        gid=str(event['game_id'])
        if str(event.get('game','')).strip().casefold()=='test game':continue
        if event['new_score']<=event['previous_score']:raise ValueError('Invalid takeover')
        observed=timestamp(event['observed_at'])
        for sid in event['new_score_ids']:
            sid=str(sid);row=approved.get(sid)
            if not row:continue
            player=row['name'];submitted=timestamp(row['date']);first=timestamp(row['first_observed_at'])
            if (row['game']!=gid or row['score']!=event['new_score'] or
                player not in event['gained_holders'] or player not in event['new_holders'] or
                player in event['previous_holders'] or submitted<CUTOFF or
                submitted>first or first>observed or submitted>observed):
                continue
            day=submitted.astimezone(ET).date().isoformat()
            key=(player,day)
            candidate={'player':player,'day':day,'game_id':gid,'game':event.get('game',''),
                       'score_id':sid,'score':row['score'],'submitted_at':submitted.isoformat(),
                       'transition_id':event['id']}
            previous=by_day[key].get(gid)
            if previous is None or (candidate['submitted_at'],sid)<(previous['submitted_at'],previous['score_id']):
                by_day[key][gid]=candidate
    candidates=[]
    for (player,day),games in by_day.items():
        if len(games)<2:continue
        first_two=sorted(games.values(),key=lambda x:(x['submitted_at'],x['score_id'],x['game_id']))[:2]
        candidates.append({'id':'secret_double_trouble:'+player,'player':player,'day':day,
                           'events':first_two,'unlocked_at':max(x['submitted_at'] for x in first_two)})
    earliest={}
    for candidate in sorted(candidates,key=lambda x:(x['unlocked_at'],x['player'])):
        earliest.setdefault(candidate['player'],candidate)
    return {'mode':'PREVIEW_ONLY_NO_AWARDS','candidates':sorted(earliest.values(),key=lambda x:x['player'])}
def main():
    result=preview(json.loads(JOURNAL.read_text()),json.loads(HISTORY.read_text()))
    print('DOUBLE TROUBLE evidence preview (NO awards or pushes):',len(result['candidates']),'eligible players')
if __name__=='__main__':main()
