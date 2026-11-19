#!/usr/bin/env python3
"""OneSignal monthly event pushes. Never sends speculative or premature results.

Reveal push: only after 9 AM ET on the 1st, only after the published GitHub Pages
feed confirms the already-revealed game. From January onward it also reminds
players the previous month's results are scheduled for the 2nd.
Results push: only on the 2nd after 9 AM ET and only from an independently
finalized, original-submission-time-verified monthly results record. Until such
a record exists, no winners push is sent. No new accounts or award issuance.
"""
import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
NY = ZoneInfo('America/New_York')
SITE = 'https://g1lgamesh20.github.io/big-daddys-arcade/'
PUBLIC_FEED = SITE + 'monthly-challenge-live.json'
APP_ID = '6aca5b1a-5845-489a-a739-4d979d7f7cb4'
STATE = 'monthly-notification-state.json'
LIVE = 'monthly-challenge-live.json'
FINAL = 'monthly-final-results.json'
ARCHIVE = 'published-monthly-challenge-history.json'


def load(path, default=None):
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else default


def previous_month(month):
    date = datetime.strptime(month + '-01', '%Y-%m-%d')
    previous = date - timedelta(days=1)
    return previous.strftime('%Y-%m')


def month_title(month):
    return datetime.strptime(month + '-01', '%Y-%m-%d').strftime('%B %Y')


def safe_result(data, previous, now, archive):
    """Require final audited source; refuse provisional/assumed timestamps."""
    if not isinstance(data, dict) or data.get('schema_version') != 1:
        return None
    item = data.get('months', {}).get(previous) if isinstance(data.get('months'), dict) else None
    published = archive.get('months', {}).get(previous) if isinstance(archive, dict) else None
    if not isinstance(item, dict) or not isinstance(published, dict):
        return None
    if (item.get('status') != 'final_verified' or
        item.get('eligibility_source') != 'original_submission_timestamps_verified' or
        item.get('all_pending_resolved') is not True or
        str(item.get('game_id')) != str(published.get('game_id'))):
        return None
    try:
        finalized = datetime.fromisoformat(item['finalized_at'])
        if finalized.tzinfo is None or finalized > now:
            return None
        # Cannot finalize the December contest until after Jan 2 at 00:00 ET.
        cutoff = datetime.strptime(previous + '-01', '%Y-%m-%d')
        y, m = cutoff.year, cutoff.month
        close = datetime(y + (m == 12), m % 12 + 1, 2, tzinfo=NY)
        if finalized < close:
            return None
    except (KeyError, ValueError, TypeError):
        return None
    podium = item.get('podium')
    if item.get('no_verified_entrants') is True:
        return 'no_entrants' if podium == [] else None
    if not isinstance(podium, list) or not podium or len(podium) > 20:
        return None
    ranks = []
    seen = set()
    for p in podium:
        if not isinstance(p, dict):
            return None
        player = p.get('player')
        score = p.get('score')
        rank = p.get('rank')
        if not isinstance(player, str) or not (1 <= len(player) <= 3) or not all(c.isupper() or c.isdigit() or c == ' ' for c in player):
            return None
        if player in seen or type(score) is not int or score < 0 or type(rank) is not int or rank < 1 or rank > 3:
            return None
        seen.add(player)
        ranks.append(rank)
    ranks.sort()
    if ranks[0] != 1 or any(ranks[i] not in (ranks[i-1], i+1) for i in range(1,len(ranks))):
        return None
    if max(ranks) > 3:
        return None
    return sorted(podium, key=lambda p:(p['rank'],-p['score'],p['player']))


def build(kind, now, root=ROOT, public_fetch=None):
    now = now.astimezone(NY)
    month = now.strftime('%Y-%m')
    if kind == 'reveal':
        if now.day != 1 or now.hour < 9 or month < '2026-12':
            return None
        published = load(root / LIVE)
        if not isinstance(published, dict) or published.get('status') != 'provisional' or published.get('month') != month:
            return None
        game = published.get('game')
        if not isinstance(game, str) or not game.strip() or len(game)>100 or not str(published.get('game_id','')).isdigit():
            return None
        if type(published.get('starting_record')) is not int or type(published.get('benchmark')) is not int:
            return None
        if published['benchmark'] != (published['starting_record']*3+3)//4:
            return None
        try:
            released = datetime.fromisoformat(published['reveal_at'])
            if released.tzinfo is None or released > now or released.astimezone(NY).strftime('%Y-%m-%d %H') != month+'-01 09':
                return None
        except (ValueError, KeyError, TypeError):
            return None
        # Do not push until the actual public Pages feed is deployed, not just
        # committed in GitHub. Retry later if Pages is delayed.
        try:
            if public_fetch is None:
                with urlopen(Request(PUBLIC_FEED,headers={'Cache-Control':'no-cache'}),timeout=12) as response:
                    remote = json.load(response)
            else:
                remote = public_fetch()
        except Exception:
            print('Public Pages reveal not available yet; retry later.')
            return None
        if (not isinstance(remote, dict) or remote.get('month') != month
            or remote.get('status') != 'provisional'
            or str(remote.get('game_id')) != str(published['game_id'])
            or remote.get('benchmark') != published['benchmark']):
            print('Public Pages reveal not yet confirmed; retry later.')
            return None
        reminder = (' 🏆 '+month_title(previous_month(month))+
                    ' winners and awards are scheduled for TOMORROW, the 2nd, at 9 AM Eastern!'
                    if month >= '2027-01' else '')
        message = (month_title(month)+': '+game.strip()[:55]+
                   '! Play the new challenge in the Hall of Legends.'+reminder)
        return month, '🎮 GAME OF THE MONTH REVEALED!', message[:240]
    if kind == 'results':
        if now.day != 2 or now.hour < 9 or month < '2027-01':
            return None
        prev = previous_month(month)
        result = safe_result(load(root / FINAL),prev,now,load(root / ARCHIVE))
        if result is None:
            print('No independently verified finalized monthly results; hold push safely.')
            return None
        if result == 'no_entrants':
            print('No verified entrants; monthly results are archived without a push.')
            return None
        gold = [p['player'] for p in result if p['rank']==1]
        if not gold:
            return None
        top = ', '.join(gold)
        if len(top) > 65:
            top = top[:62].rsplit(', ',1)[0]+'…'
        message = ('🏆 '+month_title(prev)+' champion'+('s' if len(gold)>1 else '')+
                   ': '+top+'! View the finalized podium and verified achievements in the Hall of Legends.')
        return prev, '🏆 GAME OF THE MONTH WINNERS!', message[:240]
    raise ValueError('Unknown monthly notification type')


def run(kind, now=None, root=ROOT, sender=None, public_fetch=None):
    now = (now or datetime.now(timezone.utc)).astimezone(NY)
    candidate = build(kind,now,root,public_fetch=public_fetch)
    if candidate is None:
        return 'not_ready'
    event_month,heading,message = candidate
    state_path = root / STATE
    state = load(state_path, {'schema_version':1,'sent':{}})
    if not isinstance(state,dict) or state.get('schema_version')!=1 or not isinstance(state.get('sent'),dict):
        raise ValueError('Invalid monthly notification state')
    event_id = kind+':'+event_month
    if event_id in state['sent']:
        print('Already sent:',event_id)
        return 'already_sent'
    key = str(uuid.uuid5(uuid.NAMESPACE_URL,'big-daddys-arcade:monthly:'+event_id))
    payload = {
        'app_id': APP_ID, 'included_segments':['All'],
        'headings':{'en':heading},'contents':{'en':message},'url':SITE,
        'idempotency_key':key, 'data':{'kind':'monthly_'+kind,'event_month':event_month}
    }
    if sender is None:
        secret = os.environ.get('ONESIGNAL_REST_API_KEY','').strip()
        if not secret:
            raise RuntimeError('Missing ONESIGNAL_REST_API_KEY')
        request = Request('https://api.onesignal.com/notifications',
            data=json.dumps(payload).encode('utf-8'),
            headers={'Authorization':'Key '+secret,'Content-Type':'application/json',
                     'Accept':'application/json'},method='POST')
        with urlopen(request,timeout=25) as response:
            result = json.load(response)
    else:
        result = sender(payload)
    if not isinstance(result,dict) or not result.get('id') or result.get('errors'):
        raise RuntimeError('OneSignal did not confirm monthly announcement')
    state['sent'][event_id] = {'accepted_at':now.isoformat(),'notification_id':str(result['id'])}
    state_path.write_text(json.dumps(state,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print('OneSignal accepted monthly announcement:',event_id)
    return 'sent'


if __name__=='__main__':
    import sys
    if len(sys.argv)!=2 or sys.argv[1] not in ('reveal','results'):
        raise SystemExit('Usage: python tools/send_monthly_notification.py reveal|results')
    run(sys.argv[1])
