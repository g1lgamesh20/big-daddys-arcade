#!/usr/bin/env python3
"""One lifetime JUST IN TIME trophy per player; no push."""
import copy,json,os,tempfile
from datetime import datetime,timezone
from pathlib import Path
from just_in_time_preview import preview,HISTORY,BASELINES
from personal_best_preview import JOURNAL,ROOT
LEDGER=ROOT/'verified-challenge-awards.json'
def activate(journal,history,baselines,ledger,now,*,enabled=False):
    if not enabled:return copy.deepcopy(ledger),[]
    if now.tzinfo is None:raise ValueError('Timezone required')
    if not isinstance(ledger,dict) or ledger.get('schema_version')!=1 or not isinstance(ledger.get('awards'),list) or not isinstance(ledger.get('verified_plays'),list):raise ValueError('Invalid award ledger')
    candidates=preview(journal,history,baselines)['candidates'];result=copy.deepcopy(ledger)
    seen=set();awarded=set()
    for a in result['awards']:
        if not isinstance(a,dict) or not isinstance(a.get('id'),str) or not a['id'] or a['id'] in seen:raise ValueError('Invalid or duplicate award')
        seen.add(a['id'])
        if a.get('type')=='secret_just_in_time':awarded.add(a.get('player'))
    added=[]
    for c in candidates:
        player=c['player'];aid='secret_just_in_time:'+player
        if player in awarded or aid in seen:continue
        award={'id':aid,'type':'secret_just_in_time','name':'JUST IN TIME','player':player,
               'date':c['day'],'game':c['game'],'game_id':c['game_id'],
               'score_id':c['score_id'],'score':c['score'],
               'starting_champion_score':c['starting_champion_score'],
               'original_submitted_at_et':c['submitted_at_et'],
               'starting_champion_observed_at':c['baseline_observed_at'],
               'verified_at':now.astimezone(timezone.utc).isoformat(),
               'verification_method':'approved_score_final_five_minutes_et_above_prestart_locked_daily_champion'}
        result['awards'].append(award);added.append(award);seen.add(aid);awarded.add(player)
    result['awards'].sort(key=lambda a:(str(a.get('date','')),str(a.get('id',''))))
    return result,added
def main():
    if os.environ.get('JUST_IN_TIME_AWARDS_ENABLED')!='1':
        print('JUST IN TIME activation OFF; no changes or notifications');return
    journal=json.loads(JOURNAL.read_text());history=json.loads(HISTORY.read_text());baselines=json.loads(BASELINES.read_text());ledger=json.loads(LEDGER.read_text())
    updated,added=activate(journal,history,baselines,ledger,datetime.now(timezone.utc),enabled=True)
    if added:
        with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=LEDGER.parent,prefix='.just-in-time-',suffix='.json',delete=False) as tmp:
            json.dump(updated,tmp,indent=2,ensure_ascii=False);tmp.write('\n');path=Path(tmp.name)
        path.replace(LEDGER)
    print('JUST IN TIME lifetime awards:',len(added),'(NO notifications)')
if __name__=='__main__':main()
