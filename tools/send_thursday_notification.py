#!/usr/bin/env python3
"""OneSignal Thursday 9 AM ET announcement, deduplicated via committed state.
Run only in the scheduled workflow; avoid sending until the correct local hour.
"""
import json,os
from datetime import datetime,timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from urllib.request import Request,urlopen
ROOT=Path(__file__).resolve().parents[1]
STATE=ROOT/'thursday-notification-state.json'
DATA=ROOT/'thursday-challenge.json'

def main():
    now=datetime.now(timezone.utc).astimezone(ZoneInfo('America/New_York'))
    if now.weekday()!=3 or now.hour!=9:
        print('Outside Thursday 9 AM Eastern window; skipping');return
    data=json.loads(DATA.read_text())
    if data['week']!=now.date().isoformat():raise RuntimeError('Challenge week mismatch; not sending')
    sent=json.loads(STATE.read_text()) if STATE.exists() else {'announced_weeks':[]}
    if data['week'] in sent['announced_weeks']:
        print('Already announced');return
    key=os.environ.get('ONESIGNAL_REST_API_KEY')
    app=os.environ.get('ONESIGNAL_APP_ID','6aca5b1a-5845-489a-a739-4d979d7f7cb4')
    if not key:raise RuntimeError('Missing ONESIGNAL_REST_API_KEY secret')
    payload={'app_id':app,'included_segments':['All'],
             'headings':{'en':'🕹️ THURSDAY ARCADE CHALLENGE!'},
             'contents':{'en':f'This week: {data["game"]}! Highest Thursday score wins the crown. 🏆'},
             'url':'https://g1lgamesh20.github.io/big-daddys-arcade/'}
    req=Request('https://api.onesignal.com/notifications',data=json.dumps(payload).encode(),
                headers={'Authorization':'Key '+key,'Content-Type':'application/json'},method='POST')
    with urlopen(req,timeout=25) as r:response=json.load(r)
    if not response.get('id') or response.get('errors'):
        raise RuntimeError('OneSignal did not confirm notification: '+str(response))
    sent['announced_weeks']=sorted(set(sent['announced_weeks']+[data['week']]))[-52:]
    STATE.write_text(json.dumps(sent,indent=2)+'\n')
    print('Announcement accepted for',data['week'])
if __name__=='__main__':main()
