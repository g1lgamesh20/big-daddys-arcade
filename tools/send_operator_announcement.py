#!/usr/bin/env python3
"""Manually triggered OneSignal announcement. Secret stays in GitHub Actions."""
import json,os,sys,uuid
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError

def main():
 title=os.environ.get('ANNOUNCEMENT_TITLE','').strip()
 body=os.environ.get('ANNOUNCEMENT_MESSAGE','').strip()
 key=os.environ.get('ONESIGNAL_REST_API_KEY','').strip()
 app_id='6aca5b1a-5845-489a-a739-4d979d7f7cb4'
 if not title or not body or len(title)>80 or len(body)>240:
  raise ValueError('Title required (max 80 characters), message required (max 240 characters).')
 if not key: raise ValueError('Missing ONESIGNAL_REST_API_KEY secret')
 payload={'app_id':app_id,'included_segments':['All'],'headings':{'en':title},'contents':{'en':body},'url':'https://g1lgamesh20.github.io/big-daddys-arcade/','idempotency_key':str(uuid.uuid4()),'data':{'kind':'operator_announcement'}}
 req=Request('https://api.onesignal.com/notifications',data=json.dumps(payload).encode(),headers={'Authorization':'Key '+key,'Content-Type':'application/json','Accept':'application/json'},method='POST')
 try:
  with urlopen(req,timeout=30) as r:
   result=json.load(r)
   if not result.get('id'): raise RuntimeError('OneSignal did not return a notification ID')
   print('Announcement accepted by OneSignal; notification ID:',result['id'],'recipients:',result.get('recipients','not reported'))
 except HTTPError as e: raise RuntimeError('OneSignal HTTP error '+str(e.code)) from None
 except URLError: raise RuntimeError('Could not connect to OneSignal') from None
if __name__=='__main__':
 try: main()
 except (ValueError,RuntimeError) as e:
  print('Announcement failed:',e,file=sys.stderr);sys.exit(1)
