#!/usr/bin/env python3
"""One lifetime TREASURE HUNTER trophy per verified player, no push."""
import copy,json,os,tempfile
from datetime import datetime,timezone
from pathlib import Path
from treasure_hunter_preview import preview
from treasure_hunter_state import STATE
from personal_best_preview import JOURNAL,ROOT
LEDGER=ROOT/'verified-challenge-awards.json'
def activate(journal,state,ledger,now,*,enabled=False):
    if not enabled:return copy.deepcopy(ledger),[]
    if now.tzinfo is None:raise ValueError('Timezone required')
    if not isinstance(ledger,dict) or ledger.get('schema_version')!=1 or not isinstance(ledger.get('awards'),list) or not isinstance(ledger.get('verified_plays'),list):raise ValueError('Invalid award ledger')
    candidates=preview(journal,state)['candidates'];result=copy.deepcopy(ledger)
    seen=set();awarded=set()
    for a in result['awards']:
        if not isinstance(a,dict) or not isinstance(a.get('id'),str) or not a['id'] or a['id'] in seen:raise ValueError('Invalid or duplicate award')
        seen.add(a['id'])
        if a.get('type')=='secret_treasure_hunter':awarded.add(a.get('player'))
    added=[]
    for c in candidates:
        player=c['player'];aid='secret_treasure_hunter:'+player
        if player in awarded or aid in seen:continue
        award={'id':aid,'type':'secret_treasure_hunter','name':'TREASURE HUNTER','player':player,
            'date':c['submitted_at'][:10],'game':c['game'],'game_id':c['game_id'],
            'score_id':c['score_id'],'score':c['score'],
            'observed_empty_at':c['observed_empty_at'],'observed_gold_at':c['observed_gold_at'],
            'verified_at':now.astimezone(timezone.utc).isoformat(),
            'verification_method':'approved_first_gold_after_prospective_empty_game_observation'}
        result['awards'].append(award);added.append(award);seen.add(aid);awarded.add(player)
    result['awards'].sort(key=lambda a:(str(a.get('date','')),str(a.get('id',''))))
    return result,added
def main():
    if os.environ.get('TREASURE_HUNTER_AWARDS_ENABLED')!='1':
        print('TREASURE HUNTER activation OFF; no changes or notifications');return
    journal=json.loads(JOURNAL.read_text());state=json.loads(STATE.read_text());ledger=json.loads(LEDGER.read_text())
    updated,added=activate(journal,state,ledger,datetime.now(timezone.utc),enabled=True)
    if added:
        with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=LEDGER.parent,prefix='.treasure-hunter-',suffix='.json',delete=False) as tmp:
            json.dump(updated,tmp,indent=2,ensure_ascii=False);tmp.write('\n');path=Path(tmp.name)
        path.replace(LEDGER)
    print('TREASURE HUNTER lifetime awards:',len(added),'(NO notifications)')
if __name__=='__main__':main()
