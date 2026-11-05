#!/usr/bin/env python3
"""Send only new medal-feed entries to OneSignal, with persistent deduplication.

First run deliberately baselines the existing medal feed without sending it.
Never print the OneSignal REST API key. Store it only in GitHub Actions secrets.
"""
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
FEED = ROOT / 'medals.json'
STATE = ROOT / 'medal-notification-state.json'
APP_ID = '6aca5b1a-5845-489a-a739-4d979d7f7cb4'
ARCADE_URL = 'https://g1lgamesh20.github.io/big-daddys-arcade/'
API_URL = 'https://api.onesignal.com/notifications'
MEDALS = {'gold': ('🥇', 'GOLD', 1), 'silver': ('🥈', 'SILVER', 2), 'bronze': ('🥉', 'BRONZE', 3)}


def valid_alert(a):
    if not isinstance(a, dict) or a.get('medal') not in MEDALS:
        return False
    try:
        return (str(a.get('id', '')).strip() != '' and
                str(a.get('player', '')).strip() != '' and
                str(a.get('game', '')).strip() != '' and
                int(a.get('rank', 0)) == MEDALS[a['medal']][2] and
                not isinstance(a.get('score'), bool) and
                int(a['score']) >= 0)
    except (ValueError, TypeError):
        return False


def make_payload(a):
    emoji, medal, rank = MEDALS[a['medal']]
    player = str(a['player']).strip()[:48]
    game = str(a['game']).strip()[:100]
    score = int(a['score'])
    # Stable idempotency key for retries (OneSignal's deduplication window is finite).
    key = str(uuid.uuid5(uuid.NAMESPACE_URL, f'big-daddys-arcade:medal:{a["id"]}'))
    return {
        'app_id': APP_ID,
        'included_segments': ['Subscribed Users'],
        'headings': {'en': f'{emoji} NEW {medal} MEDAL!'},
        'contents': {'en': f'{player} earned {rank}{"st" if rank == 1 else "nd" if rank == 2 else "rd"} place in {game} with {score:,} points!'},
        'url': ARCADE_URL,
        'idempotency_key': key,
        'data': {'medal_score_id': str(a['id']), 'medal': a['medal']},
    }


def save_state(sent):
    obj = {'sent_ids': sorted(sent), 'updated_at': datetime.now(timezone.utc).isoformat()}
    STATE.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def send(payload, key):
    req = Request(API_URL, data=json.dumps(payload).encode('utf-8'),
                  headers={'Authorization': f'Key {key}', 'Content-Type': 'application/json',
                           'Accept': 'application/json'}, method='POST')
    try:
        with urlopen(req, timeout=25) as response:
            result = json.load(response)
            if response.status not in (200, 201) or not result.get('id'):
                raise RuntimeError('OneSignal did not confirm a notification ID')
    except HTTPError as e:
        # Don't echo response bodies: service responses might include sensitive details.
        raise RuntimeError(f'OneSignal returned HTTP {e.code}') from None
    except URLError as e:
        raise RuntimeError('Unable to connect to OneSignal') from None


def main():
    if not FEED.exists():
        raise RuntimeError('medals.json missing; cannot send notifications')
    data = json.loads(FEED.read_text(encoding='utf-8'))
    alerts = data.get('alerts')
    if not isinstance(alerts, list):
        raise RuntimeError('Invalid medal feed: alerts must be an array')
    ids = {str(a['id']) for a in alerts if valid_alert(a)}
    if not STATE.exists():
        save_state(ids)
        print(f'Initialized notification baseline for {len(ids)} existing medals; sent 0 notifications.')
        return
    state = json.loads(STATE.read_text(encoding='utf-8'))
    sent = set(map(str, state.get('sent_ids', [])))
    pending = [a for a in reversed(alerts) if valid_alert(a) and str(a['id']) not in sent]
    if not pending:
        print('No new medal notifications to send.')
        return
    key = os.environ.get('ONESIGNAL_REST_API_KEY', '').strip()
    if not key:
        raise RuntimeError('ONESIGNAL_REST_API_KEY GitHub Actions secret is missing')
    count = 0
    for a in pending:
        send(make_payload(a), key)
        sent.add(str(a['id']))
        save_state(sent)  # Persist each confirmed send, even if a later send fails.
        count += 1
    print(f'Sent {count} new medal notification(s).')


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, ValueError, OSError, json.JSONDecodeError) as error:
        print(f'Notification sync failed: {error}', file=sys.stderr)
        sys.exit(1)
