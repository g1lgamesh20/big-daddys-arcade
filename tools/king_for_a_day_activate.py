#!/usr/bin/env python3
"""KING FOR A DAY: simple 24h observed Gold tenure, no additional monitoring."""
import copy,json,os,tempfile
from datetime import datetime,timezone
from pathlib import Path
from gold_history_secret_preview import preview,parsed
from gold_holder_history import HISTORY
from personal_best_preview import ROOT
LEDGER=ROOT/'verified-challenge-awards.json'
def activate(history,ledger,now,*,enabled=False):
    if not enabled:return copy.deepcopy(ledger),[]
    if now.tzinfo is None:raise ValueError('Timezone required')
    if not isinstance(ledger,dict) or ledger.get('schema_version')!=1 or not isinstance(ledger.get('awards'),list) or not isinstance(ledger.get('verified_plays'),list):raise ValueError('Invalid awards ledger')
    report=preview(history,now)
    result=copy.deepcopy(ledger);seen=set();awarded=set()
    for award in result['awards']:
        if not isinstance(award,dict) or not isinstance(award.get('id'),str) or not award['id'] or award['id'] in seen:raise ValueError('Invalid/duplicate award ID')
        seen.add(award['id'])
        if award.get('type')=='secret_king_for_a_day':awarded.add(award.get('player'))
    added=[]
    for item in sorted(report['king_day_candidates'],key=lambda x:(parsed(x['first_observed_at']),x['game_id'],x['player'])):
        player=item['player'];gid=item['game_id']
        if not isinstance(player,str) or not player or player!=player.strip().upper():raise ValueError('Invalid player')
        if item['game'].strip().casefold()=='test game':continue
        award_id='secret_king_for_a_day:'+player
        if award_id in seen or player in awarded:continue
        first=parsed(item['first_observed_at'])
        award={'id':award_id,'type':'secret_king_for_a_day','name':'KING FOR A DAY','player':player,'game_id':gid,'game':item['game'],'date':now.astimezone(timezone.utc).date().isoformat(),'first_observed_at':first.isoformat(),'verified_at':now.astimezone(timezone.utc).isoformat(),'verification_method':'gold_observed_24h_apart_no_recorded_loss','time_policy':'two_observations_not_continuous_monitoring'}
        result['awards'].append(award);added.append(award);seen.add(award_id);awarded.add(player)
    result['awards'].sort(key=lambda a:(str(a.get('date','')),str(a.get('id',''))))
    return result,added
def main():
    if os.environ.get('KING_FOR_A_DAY_AWARDS_ENABLED')!='1':
        print('KING FOR A DAY activation OFF; no changes or notifications');return
    history=json.loads(HISTORY.read_text(encoding='utf-8'))
    ledger=json.loads(LEDGER.read_text(encoding='utf-8'))
    updated,added=activate(history,ledger,datetime.now(timezone.utc),enabled=True)
    if added:
        with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=LEDGER.parent,prefix='.king-for-a-day-',suffix='.json',delete=False) as tmp:
            json.dump(updated,tmp,indent=2,ensure_ascii=False);tmp.write('\n');temp=Path(tmp.name)
        temp.replace(LEDGER)
    print('KING FOR A DAY lifetime awards:',len(added),'(NO notifications)')
if __name__=='__main__':main()
