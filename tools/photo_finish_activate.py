#!/usr/bin/env python3
"""Issue one lifetime PHOTO FINISH trophy per player, without notifications."""
import copy,json,os,tempfile
from datetime import datetime,timezone
from pathlib import Path
from photo_finish_preview import preview
from personal_best_preview import JOURNAL,ROOT
from gold_holder_history import HISTORY
LEDGER=ROOT/'verified-challenge-awards.json'
def activate(journal,history,ledger,now,*,enabled=False):
    if not enabled:return copy.deepcopy(ledger),[]
    if now.tzinfo is None:raise ValueError('Timezone required')
    if not isinstance(ledger,dict) or ledger.get('schema_version')!=1 or not isinstance(ledger.get('awards'),list) or not isinstance(ledger.get('verified_plays'),list):raise ValueError('Invalid award ledger')
    candidates=preview(journal,history)['candidates'];result=copy.deepcopy(ledger)
    seen=set();awarded=set()
    for a in result['awards']:
        if not isinstance(a,dict) or not isinstance(a.get('id'),str) or not a['id'] or a['id'] in seen:raise ValueError('Invalid or duplicate award')
        seen.add(a['id'])
        if a.get('type')=='secret_photo_finish':awarded.add(a.get('player'))
    added=[]
    for c in candidates:
        player=c['player'];aid='secret_photo_finish:'+player
        if aid in seen or player in awarded:continue
        a={'id':aid,'type':'secret_photo_finish','name':'PHOTO FINISH','player':player,
           'date':c['submitted_at'][:10],'game':c['game'],'game_id':c['game_id'],
           'score_id':c['score_id'],'score':c['score'],'gold_score':c['gold_score'],
           'gold_observed_at':c['gold_observed_at'],'submitted_at':c['submitted_at'],
           'verified_at':now.astimezone(timezone.utc).isoformat(),
           'verification_method':'approved_near_miss_within_1pct_after_observed_gold_baseline'}
        result['awards'].append(a);added.append(a);seen.add(aid);awarded.add(player)
    result['awards'].sort(key=lambda a:(str(a.get('date','')),str(a.get('id',''))))
    return result,added
def main():
    if os.environ.get('PHOTO_FINISH_AWARDS_ENABLED')!='1':
        print('PHOTO FINISH activation OFF; no changes or notifications');return
    journal=json.loads(JOURNAL.read_text(encoding='utf-8'))
    history=json.loads(HISTORY.read_text(encoding='utf-8'))
    ledger=json.loads(LEDGER.read_text(encoding='utf-8'))
    updated,added=activate(journal,history,ledger,datetime.now(timezone.utc),enabled=True)
    if added:
        with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=LEDGER.parent,prefix='.photo-finish-',suffix='.json',delete=False) as tmp:
            json.dump(updated,tmp,indent=2,ensure_ascii=False);tmp.write('\n');path=Path(tmp.name)
        path.replace(LEDGER)
    print('PHOTO FINISH lifetime awards:',len(added),'(NO notifications)')
if __name__=='__main__':main()
