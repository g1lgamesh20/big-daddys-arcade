#!/usr/bin/env python3
"""Idempotent lifetime DOUBLE TROUBLE award issuance. No push notifications."""
import copy,json,os,tempfile
from datetime import datetime,timezone
from pathlib import Path
from double_trouble_preview import preview
from gold_holder_history import HISTORY
from personal_best_preview import JOURNAL,ROOT
LEDGER=ROOT/'verified-challenge-awards.json'
def activate(journal,history,ledger,now,*,enabled=False):
    if not enabled:return copy.deepcopy(ledger),[]
    if now.tzinfo is None:raise ValueError('Timezone required')
    if not isinstance(ledger,dict) or ledger.get('schema_version')!=1 or not isinstance(ledger.get('awards'),list) or not isinstance(ledger.get('verified_plays'),list):raise ValueError('Invalid awards ledger')
    candidates=preview(journal,history)['candidates']
    result=copy.deepcopy(ledger);seen=set();holders=set()
    for a in result['awards']:
        if not isinstance(a,dict) or not isinstance(a.get('id'),str) or not a['id'] or a['id'] in seen:raise ValueError('Duplicate or malformed award')
        seen.add(a['id'])
        if a.get('type')=='secret_double_trouble':holders.add(a.get('player'))
    added=[]
    for c in candidates:
        player=c['player'];award_id='secret_double_trouble:'+player
        if player in holders or award_id in seen:continue
        award={'id':award_id,'type':'secret_double_trouble','name':'DOUBLE TROUBLE',
               'player':player,'date':c['day'],'game':c['events'][1]['game'],
               'game_id':c['events'][1]['game_id'],'score_id':c['events'][1]['score_id'],
               'score':c['events'][1]['score'],'qualifying_games':[x['game_id'] for x in c['events']],
               'qualifying_score_ids':[x['score_id'] for x in c['events']],
               'qualifying_transition_ids':[x['transition_id'] for x in c['events']],
               'original_submitted_at_et':c['unlocked_at'],'verified_at':now.astimezone(timezone.utc).isoformat(),
               'verification_method':'two_distinct_postcutover_approved_gold_takeovers_same_eastern_day'}
        result['awards'].append(award);added.append(award);holders.add(player);seen.add(award_id)
    result['awards'].sort(key=lambda a:(str(a.get('date','')),str(a.get('id',''))))
    return result,added
def main():
    if os.environ.get('DOUBLE_TROUBLE_AWARDS_ENABLED')!='1':
        print('DOUBLE TROUBLE activation OFF; no changes or notifications');return
    journal=json.loads(JOURNAL.read_text(encoding='utf-8'))
    history=json.loads(HISTORY.read_text(encoding='utf-8'))
    ledger=json.loads(LEDGER.read_text(encoding='utf-8'))
    updated,added=activate(journal,history,ledger,datetime.now(timezone.utc),enabled=True)
    if added:
        with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=LEDGER.parent,prefix='.double-trouble-',suffix='.json',delete=False) as tmp:
            json.dump(updated,tmp,indent=2,ensure_ascii=False);tmp.write('\n');path=Path(tmp.name)
        path.replace(LEDGER)
    print('DOUBLE TROUBLE lifetime awards:',len(added),'(NO notifications)')
if __name__=='__main__':main()
