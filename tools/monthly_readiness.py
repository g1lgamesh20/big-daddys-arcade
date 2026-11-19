#!/usr/bin/env python3
"""Private monthly launch readiness audit; NEVER reveals the mystery game.

Use GitHub Actions secret MONTHLY_SELECTION_KEY. No changes to the selection,
awards, OneSignal, or public feeds. Scheduled audits check next month's game
before rollover; a late run does not create or revise a benchmark.
"""
import json
import os
import re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from monthly_private_selection import (ROOT, STATE, CATALOG, POOL,
    key_from_secret, read_json, unseal, month_after)
from monthly_benchmark import analyze, get_scores, bounds

NY=ZoneInfo('America/New_York')

def check(month, state, catalog, pool, key, rows, now):
    if not re.fullmatch(r'20\d{2}-(0[1-9]|1[0-2])',month):
        raise ValueError('Invalid monthly audit period')
    if not isinstance(state,dict) or state.get('version')!=1:
        raise ValueError('Missing or invalid sealed state')
    packet=state.get('selections',{}).get(month)
    if packet is None:
        raise ValueError('No encrypted selection prepared for upcoming month')
    secret=unseal(AESGCM(key),packet)
    if not isinstance(secret,dict) or secret.get('month')!=month:
        raise ValueError('Sealed selection does not match month')
    game=secret.get('game_id')
    if not isinstance(game,str) or not game:
        raise ValueError('Encrypted selection game ID missing')
    if game not in catalog.get('games',{}):
        raise ValueError('Mystery game is no longer in the game catalog')
    excluded=pool.get('excluded_game_ids')
    if not isinstance(excluded,list):
        raise ValueError('Invalid game exclusion settings')
    if secret.get('method')!='operator' and game in excluded:
        raise ValueError('Randomly selected mystery game is currently excluded')
    start,end=bounds(month)
    locked=secret.get('benchmark_lock')
    if locked:
        if not isinstance(locked,dict) or locked.get('month_start')!=start.isoformat():
            raise ValueError('Encrypted benchmark has invalid start date')
        val=locked.get('starting_record')
        target=locked.get('benchmark')
        if type(val)!=int or val<0 or type(target)!=int or target!=(val*3+3)//4:
            raise ValueError('Encrypted benchmark arithmetic is invalid')
        print('PRIVATE READINESS: sealed game and locked benchmark validated; no identity disclosed')
        return 'locked'
    if now.astimezone(NY)>=start:
        raise ValueError('Month has started without a sealed benchmark; use existing safe lock workflow')
    stats=analyze(rows,game,month)
    if stats['unparseable_selected_game_dates']:
        raise ValueError('Mystery game has unparseable score timestamps')
    if stats['premonth_score_rows']<1 or stats['starting_record_candidate'] is None:
        raise ValueError('Mystery game has no usable pre-month record; benchmark lock would fail')
    if stats['selected_game_dates_without_timezone']:
        print('PRIVATE CAUTION: timestamps have no explicit timezone; benchmark provisional')
    print('PRIVATE READINESS: encrypted game exists and has usable pre-month scores; game concealed')
    print('PRIVATE READINESS: benchmark will only lock at/after midnight ET, not in this audit')
    return 'ready'

def main(now=None, rows=None):
    now=(now or datetime.now(timezone.utc)).astimezone(NY)
    month=os.environ.get('MONTHLY_READINESS_MONTH','').strip() or month_after(now)
    # Before any iScored fetch, validate key and encrypted selection.
    key=key_from_secret()
    state=read_json(STATE)
    catalog=read_json(CATALOG)
    pool=read_json(POOL)
    if rows is None:
        rows=get_scores()
    result=check(month,state,catalog,pool,key,rows,now)
    print('Monthly private readiness:',result,'for',month)
    print('No game identity, score, future award or push was disclosed or changed')
    return result

if __name__=='__main__':
    main()
