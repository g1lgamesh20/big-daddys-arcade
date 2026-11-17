#!/usr/bin/env python3
"""Private pre-reveal Monthly Challenge game selection.

The public repository contains only authenticated ciphertext; the decryption key
must be stored as a GitHub Actions secret. No scores, awards, or push are changed.
"""
import base64
import json
import os
import re
import secrets
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / 'monthly-game-catalog.json'
POOL = ROOT / 'monthly-game-pool.json'
STATE = ROOT / 'monthly-selection-sealed.json'
NY = ZoneInfo('America/New_York')


def month_after(d):
    return f'{d.year + (d.month == 12):04d}-{(d.month % 12) + 1:02d}'


def key_from_secret():
    raw = os.environ.get('MONTHLY_SELECTION_KEY', '').strip()
    if len(raw) != 64 or not re.fullmatch(r'[0-9a-fA-F]{64}', raw):
        raise ValueError('Set MONTHLY_SELECTION_KEY to 64 hex characters in GitHub Actions secrets. No changes made.')
    return bytes.fromhex(raw)


def month_arg(now):
    value = os.environ.get('MONTHLY_MONTH', '').strip() or month_after(now)
    if not re.fullmatch(r'20\d{2}-(0[1-9]|1[0-2])', value):
        raise ValueError('MONTHLY_MONTH must be a valid YYYY-MM date.')
    return value


def read_json(path):
    data = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(data, dict):
        raise ValueError(f'Invalid JSON object in {path.name}')
    return data


def eligible_ids():
    games = read_json(CATALOG).get('games')
    excluded = read_json(POOL).get('excluded_game_ids')
    if not isinstance(games, dict) or not isinstance(excluded, list):
        raise ValueError('Game catalog/pool has an invalid structure')
    if not all(isinstance(gid, str) and isinstance(name, str) for gid, name in games.items()):
        raise ValueError('Invalid game identifiers in catalog')
    if not all(isinstance(gid, str) for gid in excluded):
        raise ValueError('Invalid exclusion IDs')
    permitted = sorted(set(games) - set(excluded))
    if not permitted:
        raise ValueError('No eligible games. Selection aborted.')
    return games, permitted


def seal(aes, payload):
    nonce = os.urandom(12)
    plaintext = json.dumps(payload, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    ciphertext = aes.encrypt(nonce, plaintext, b'BIG-DADDYS-MONTHLY-V1')
    return {'v': 1, 'nonce': base64.b64encode(nonce).decode('ascii'),
            'ciphertext': base64.b64encode(ciphertext).decode('ascii')}


def unseal(aes, packet):
    if not isinstance(packet, dict) or packet.get('v') != 1:
        raise ValueError('Unknown sealed selection format')
    nonce = base64.b64decode(packet['nonce'], validate=True)
    ciphertext = base64.b64decode(packet['ciphertext'], validate=True)
    if len(nonce) != 12:
        raise ValueError('Invalid sealed nonce')
    return json.loads(aes.decrypt(nonce, ciphertext, b'BIG-DADDYS-MONTHLY-V1'))


def main(now=None):
    now = (now or datetime.now(NY)).astimezone(NY)
    month = month_arg(now)
    action = os.environ.get('MONTHLY_ACTION', 'prepare').strip()
    if action not in ('prepare', 'replace', 'verify'):
        raise ValueError('Choose prepare, replace, or verify')
    aes = AESGCM(key_from_secret())
    data = read_json(STATE) if STATE.exists() else {'version': 1, 'selections': {}}
    if data.get('version') != 1 or not isinstance(data.get('selections'), dict):
        raise ValueError('Invalid sealed state; refusing to overwrite')
    stored = data['selections']
    if action == 'verify':
        if month not in stored:
            raise ValueError('No private selection for this month')
        payload = unseal(aes, stored[month])
        if payload.get('month') != month or not payload.get('game_id'):
            raise ValueError('Mismatched private selection')
        print('Private selection verified for', month, '(game identity not logged)')
        return
    # Never allow a routine workflow to rewrite a game after its month begins.
    if month <= now.strftime('%Y-%m'):
        raise ValueError('Only future months can be prepared/replaced. Emergency post-launch override is separate.')
    if action == 'prepare' and month in stored:
        # Verify ciphertext rather than silently trusting corrupted state.
        payload = unseal(aes, stored[month])
        if payload.get('month') != month:
            raise ValueError('Invalid existing selection')
        print('Future month already privately selected. No change.')
        return
    if action == 'replace' and os.environ.get('CONFIRM_REPLACE', '').lower() != 'true':
        raise ValueError('Replace requires explicit confirmation')
    if action == 'replace' and month not in stored:
        raise ValueError('No prior selection to replace; use prepare')
    # Read the operator preference ONLY from an Actions secret, never from workflow
    # dispatch inputs (those can show up in publicly accessible run metadata).
    games, permitted = eligible_ids()
    override_month = os.environ.get('MONTHLY_OVERRIDE_MONTH', '').strip()
    override = os.environ.get('MONTHLY_OVERRIDE_GAME_ID', '').strip() if override_month == month else ''
    if override:
        if override not in games:
            raise ValueError('Operator secret references unknown game ID')
        chosen = override
        method = 'operator'
    else:
        chosen = secrets.choice(permitted)
        method = 'random'
    # No plaintext game ID/name is written to the repository or the Actions log.
    stored[month] = seal(aes, {'month': month, 'game_id': chosen, 'method': method,
                               'selected_at': now.isoformat()})
    STATE.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    print('Private selection securely sealed for', month, 'using', method, 'method.')
    print('No game revealed; no scores, awards, or push notifications changed.')


if __name__ == '__main__':
    main()
