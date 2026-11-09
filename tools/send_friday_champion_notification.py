#!/usr/bin/env python3
"""Announce a finalized Thursday champion on Friday at 9 AM New York time.
Uses existing Thursday challenge feed and a separate committed deduplication state.
"""
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
FEED = ROOT / 'thursday-challenge.json'
STATE = ROOT / 'friday-champion-notification-state.json'
NY = ZoneInfo('America/New_York')
URL = 'https://g1lgamesh20.github.io/big-daddys-arcade/'


def run(now=None, sender=None):
    now = (now or datetime.now(timezone.utc)).astimezone(NY)
    if now.weekday() != 4 or now.hour != 9:
        print('Not Friday 9 AM Eastern; no champion notification sent')
        return 'outside_window'

    expected_thursday = (now.date() - timedelta(days=1)).isoformat()
    if not FEED.exists():
        print('Challenge feed missing; skipping safely')
        return 'missing_feed'
    data = json.loads(FEED.read_text(encoding='utf-8'))
    if data.get('week') != expected_thursday or data.get('status') != 'final':
        print('Thursday results not finalized; skipping rather than announcing a premature winner')
        return 'not_final'
    winner = data.get('winner')
    if not isinstance(winner, dict) or not winner.get('player') or winner.get('score') is None:
        print('No verified qualifying Thursday champion; no announcement')
        return 'no_winner'
    if data.get('unparseable_game_dates', 0):
        print('Unverified score dates; not announcing')
        return 'unverified_dates'

    state = json.loads(STATE.read_text(encoding='utf-8')) if STATE.exists() else {'announced_weeks': []}
    announced = state.get('announced_weeks', [])
    if expected_thursday in announced:
        print('Friday winner already announced for', expected_thursday)
        return 'already_sent'

    key = os.environ.get('ONESIGNAL_REST_API_KEY')
    if not key and sender is None:
        raise RuntimeError('Missing ONESIGNAL_REST_API_KEY')
    app_id = os.environ.get('ONESIGNAL_APP_ID', '6aca5b1a-5845-489a-a739-4d979d7f7cb4')
    player = str(winner['player']).strip()[:48]
    game = str(data.get('game') or '').strip()[:100]
    if not player or not game:
        print('Missing champion or game name; skipping')
        return 'incomplete'
    score = int(winner['score'])
    payload = {
        'app_id': app_id,
        'included_segments': ['All'],
        'headings': {'en': '🏆 THURSDAY NIGHT CHAMPION!'},
        'contents': {'en': f'{player} conquered {game} with {score:,} points! Think you can take the crown next Thursday? 👾'},
        'url': URL,
    }
    if sender is None:
        req = Request('https://api.onesignal.com/notifications',
                      data=json.dumps(payload).encode('utf-8'),
                      headers={'Authorization': 'Key ' + key, 'Content-Type': 'application/json'},
                      method='POST')
        with urlopen(req, timeout=25) as response:
            result = json.load(response)
    else:
        result = sender(payload)
    if not result.get('id') or result.get('errors'):
        raise RuntimeError('OneSignal did not confirm winner notification: ' + str(result))
    state['announced_weeks'] = sorted(set(announced + [expected_thursday]))[-52:]
    STATE.write_text(json.dumps(state, indent=2) + '\n', encoding='utf-8')
    print('Friday champion notification accepted for', expected_thursday)
    return 'sent'


if __name__ == '__main__':
    run()
