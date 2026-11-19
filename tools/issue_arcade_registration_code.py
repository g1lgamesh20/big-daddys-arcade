#!/usr/bin/env python3
"""Create a random one-use, short-lived arcade registration code.

Run locally by operator; never commit output or send code through public chat.
Print code privately and copy INSERT into authenticated Supabase SQL Editor.
The public repo includes no live codes and no operator secrets.
"""
import argparse
import base64
import hashlib
import re
import secrets
from datetime import datetime, timedelta, timezone

def generate(player,days=7,random_bytes=None,now=None):
    player=player.strip().upper()
    if not re.fullmatch(r'[A-Z0-9 ]{1,3}',player) or not player.strip():
        raise ValueError('Use exactly your existing 1–3 character iScored initials')
    if not isinstance(days,int) or not 1<=days<=30:
        raise ValueError('Code lifetime must be 1–30 days')
    value=secrets.token_bytes(16) if random_bytes is None else random_bytes
    if len(value)!=16:
        raise ValueError('Registration codes must have 128-bit entropy')
    code=base64.b32encode(value).decode('ascii').rstrip('=')
    digest=hashlib.sha256(code.encode('ascii')).hexdigest()
    expires=(now or datetime.now(timezone.utc))+timedelta(days=days)
    expires=expires.astimezone(timezone.utc).isoformat()
    return code, ('insert into public.arcade_registration_codes'
                  '(code_digest,player_initials,expires_at) values '
                  f"('{digest}','{player}','{expires}');")

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('player',help='Existing iScored initials (1–3 characters)')
    p.add_argument('--days',type=int,default=7,help='Valid for 1–30 days')
    args=p.parse_args()
    code,statement=generate(args.player,args.days)
    print('PLAYER CODE (give privately to player; never commit this):',code)
    print('RUN ONCE IN AUTHENTICATED SUPABASE SQL EDITOR:\n'+statement)

if __name__=='__main__':
    main()
