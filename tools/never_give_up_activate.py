#!/usr/bin/env python3
"""NEVER GIVE UP! verified lifetime awards; no pushes."""
import copy,json,os,tempfile
from datetime import datetime,timezone
from pathlib import Path
from never_give_up_preview import preview
from personal_best_preview import JOURNAL,ROOT
from gold_holder_history import HISTORY
LEDGER=ROOT/'verified-challenge-awards.json'
def activate(journal,history,ledger,now,*,enabled=False):
    if not enabled:return copy.deepcopy(ledger),[]
    if now.tzinfo is None:raise ValueError('Timezone required')
    if not isinstance(ledger,dict) or ledger.get('schema_version')!=1 or not isinstance(ledger.get('awards'),list) or not isinstance(ledger.get('verified_plays'),list):raise ValueError('Invalid ledger')
    candidates=preview(journal,history)['candidates']
    result=copy.deepcopy(ledger);seen=set();holders=set()
    for row in result['awards']:
        if not isinstance(row,dict) or not isinstance(row.get('id'),str) or not row['id'] or row['id'] in seen:raise ValueError('Duplicate or malformed award')
        seen.add(row['id'])
        if row.get('type')=='never_give_up':holders.add(row.get('player'))
    added=[]
    for item in candidates:
        if item['id'] in seen or item['player'] in holders:continue
        award={'id':item['id'],'event_key':'never_give_up:'+item['gold_transition_id'],'type':'never_give_up','name':'NEVER GIVE UP!','player':item['player'],'date':item['submitted_at'][:10],'game':item['game'],'game_id':item['game_id'],'score_id':item['gold_score_id'],'score':item['gold_score'],'gold_transition_id':item['gold_transition_id'],'prior_unsuccessful_score_ids':item['prior_unsuccessful_score_ids'],'qualifying_attempts':item['qualifying_attempts'],'original_submitted_at_et':item['submitted_at'],'verified_at':now.isoformat(),'verification_method':'postcutover_approved_scores_and_observed_gold_takeover'}
        result['awards'].append(award);added.append(award);seen.add(item['id']);holders.add(item['player'])
    result['awards'].sort(key=lambda a:(str(a.get('date','')),str(a.get('id',''))))
    return result,added
def main():
    if os.environ.get('NEVER_GIVE_UP_AWARDS_ENABLED')!='1':
        print('NEVER GIVE UP! activation OFF; no changes or notifications');return
    journal=json.loads(JOURNAL.read_text(encoding='utf-8'))
    history=json.loads(HISTORY.read_text(encoding='utf-8'))
    ledger=json.loads(LEDGER.read_text(encoding='utf-8'))
    updated,added=activate(journal,history,ledger,datetime.now(timezone.utc),enabled=True)
    if added:
        with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=LEDGER.parent,prefix='.never-give-up-',suffix='.json',delete=False) as tmp:
            json.dump(updated,tmp,indent=2,ensure_ascii=False);tmp.write('\n');path=Path(tmp.name)
        path.replace(LEDGER)
    print('NEVER GIVE UP! lifetime awards:',len(added),'(NO notifications)')
if __name__=='__main__':main()
