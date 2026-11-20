#!/usr/bin/env python3
"""Stage 4: safely audit and privately lock monthly benchmark.

No plaintext identity/record, awards, leaderboard, or notifications are published.
iScored confirmed Central server-local timestamps; historical approval-overwrite\nrecords may remain tainted. Baselines are still private and provisional.
"""
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from monthly_private_selection import ROOT, STATE, key_from_secret, read_json, seal, unseal
from iscored_timestamp import parse_iscored_time as parse_time

NY = ZoneInfo('America/New_York')
URL = os.environ.get('ISCORED_READ_URL', 'https://www.iScored.info/api/G1LGAMESH/getAllScores')


def bounds(month):
    if not re.fullmatch(r'20\d{2}-(0[1-9]|1[0-2])', month):
        raise ValueError('Month must be YYYY-MM')
    year, m = map(int, month.split('-'))
    start = datetime(year, m, 1, tzinfo=NY)
    end = datetime(year + (m == 12), m % 12 + 1, 1, tzinfo=NY)
    return start, end


def analyze(rows, game_id, month):
    """Use only pre-month scores for baseline; do not confuse them with monthly entrants."""
    start, end = bounds(month)
    record = None
    record_rows = 0
    month_entries = {}
    bad_dates = 0
    naive_dates = 0
    same_game_rows = 0
    for row in rows:
        if not isinstance(row, dict) or str(row.get('game')) != game_id:
            continue
        same_game_rows += 1
        original_date = str(row.get('date') or '').strip()
        parsed = parse_time(original_date)
        if parsed is None:
            bad_dates += 1
            continue
        if not re.search(r'(?:Z|[+-]\d{2}:?\d{2})$', original_date):
            naive_dates += 1
        score = row.get('score')
        if isinstance(score, bool):
            continue
        try:
            score = int(score)
        except (TypeError, ValueError):
            continue
        if score < 0:
            continue
        if parsed < start:
            record_rows += 1
            record = score if record is None else max(score, record)
        elif start <= parsed < end:
            player = str(row.get('name') or '').strip().upper()[:48]
            if not player:
                continue
            if player not in month_entries or score > month_entries[player]:
                month_entries[player] = score
    benchmark = (record * 3 + 3) // 4 if record is not None else None
    return {'starting_record_candidate': record, 'benchmark_candidate': benchmark,
            'premonth_score_rows': record_rows, 'monthly_player_count': len(month_entries),
            'selected_game_score_rows': same_game_rows,
            'unparseable_selected_game_dates': bad_dates,
            'selected_game_dates_without_timezone': naive_dates}


def get_scores():
    req = Request(URL, headers={'Accept':'application/json',
                               'User-Agent':'BigDaddysArcadeMonthlyBenchmark/1.0'})
    with urlopen(req, timeout=40) as response:
        raw = json.load(response)
    if not isinstance(raw, dict) or not isinstance(raw.get('scores'), list):
        raise ValueError('iScored feed has no scores array')
    return raw['scores']


def run(now=None, rows=None):
    now = (now or datetime.now(timezone.utc)).astimezone(NY)
    month = os.environ.get('MONTHLY_BENCHMARK_MONTH', '').strip()
    action = os.environ.get('MONTHLY_BENCHMARK_ACTION', 'audit').strip()
    if action not in {'audit', 'lock', 'verify'}:
        raise ValueError('Allowed actions: audit, lock, verify')
    start, end = bounds(month)
    packet = read_json(STATE)
    if packet.get('version') != 1 or not isinstance(packet.get('selections'), dict):
        raise ValueError('Invalid sealed monthly selection state')
    selected = packet['selections'].get(month)
    if selected is None:
        raise ValueError('No encrypted game selection for this month')
    aes = AESGCM(key_from_secret())
    payload = unseal(aes, selected)
    game_id = payload.get('game_id')
    if payload.get('month') != month or not isinstance(game_id, str) or not game_id:
        raise ValueError('Sealed game selection does not match requested month')
    catalog = read_json(ROOT / 'monthly-game-catalog.json').get('games', {})
    if game_id not in catalog:
        raise ValueError('Selected game is not found in catalog')

    if action == 'verify':
        locked = payload.get('benchmark_lock')
        if not isinstance(locked, dict) or locked.get('month_start') != start.isoformat():
            raise ValueError('Benchmark not locked or invalid')
        if type(locked.get('starting_record')) is not int or type(locked.get('benchmark')) is not int:
            raise ValueError('Invalid locked benchmark')
        if locked['benchmark'] != (locked['starting_record'] * 3 + 3) // 4:
            raise ValueError('Locked benchmark calculation mismatch')
        print('Encrypted benchmark verified for', month, '(game and scores concealed)')
        return {'status': 'verified'}

    # Idempotency: never change a locked record, even if scores later change.
    if action == 'lock' and 'benchmark_lock' in payload:
        print('Benchmark already locked for', month, '(unchanged)')
        return {'status':'already_locked'}
    if action == 'lock' and now < start:
        raise ValueError('Cannot lock benchmark before local midnight at start of month')
    if action == 'lock' and now >= end:
        raise ValueError('Cannot lock benchmark after end of month')
    if rows is None:
        rows = get_scores()
    stats = analyze(rows, game_id, month)
    if stats['unparseable_selected_game_dates']:
        raise ValueError('Unparseable dates for selected game; cannot lock benchmark')
    if stats['starting_record_candidate'] is None:
        raise ValueError('No historical score for the selected game; manual review required')

    if action == 'audit':
        print('PRIVATE monthly candidate reviewed for', month)
        print('Selected-game rows:', stats['selected_game_score_rows'])
        print('Historical rows:', stats['premonth_score_rows'])
        print('Dates without timezone:', stats['selected_game_dates_without_timezone'])
        print('No game name, ID, score, award, or announcement printed')
        return {'status':'audited', 'private':stats}

    # Lock is permitted only in its target month. Date/approval semantics remain
    # provisional: do NOT treat as verified achievement or publish standings.
    payload['benchmark_lock'] = {
        'month_start':start.isoformat(), 'month_end':end.isoformat(),
        'starting_record':stats['starting_record_candidate'],
        'benchmark':stats['benchmark_candidate'],
        'locked_at':now.isoformat(),
        'verification_status':'provisional_pending_iscored_review',
    }
    packet['selections'][month] = seal(aes, payload)
    STATE.write_text(json.dumps(packet, indent=2) + '\n', encoding='utf-8')
    print('Encrypted benchmark locked for', month, '(identity and scores concealed)')
    print('Older iScored scores may have approval-overwritten dates; benchmark remains provisional')
    return {'status':'locked'}


if __name__ == '__main__':
    run()
