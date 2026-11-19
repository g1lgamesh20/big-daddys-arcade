#!/usr/bin/env python3
"""Bounded iScored read retries; never changes headers, identity or endpoint."""
import json
import time
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

RETRY_HTTP = {403, 408, 429, 500, 502, 503, 504}
DELAYS = (2, 5)

def read_scores(request, *, opener=None, sleeper=None):
    opener = opener or urlopen
    sleeper = sleeper or time.sleep
    for attempt in range(len(DELAYS)+1):
        try:
            with opener(request, timeout=25) as response:
                if getattr(response, 'status', 200) != 200:
                    raise RuntimeError('iScored returned HTTP '+str(response.status))
                # Never retry invalid payloads; do not publish partial scores.
                payload = json.load(response)
            if not isinstance(payload, dict) or not isinstance(payload.get('scores'), list):
                raise ValueError('Unexpected iScored response: missing scores array')
            return payload
        except HTTPError as err:
            if err.code not in RETRY_HTTP or attempt == len(DELAYS):
                print(f'iScored read failed HTTP {err.code} (attempt {attempt+1}/{len(DELAYS)+1}); preserving current feed')
                raise
            print(f'iScored temporarily rejected read HTTP {err.code}; retry {attempt+2}/{len(DELAYS)+1} after {DELAYS[attempt]} seconds')
        except (URLError, TimeoutError) as err:
            if attempt == len(DELAYS):
                print(f'iScored network read failed after {attempt+1} attempts; preserving current feed')
                raise
            print(f'iScored network read error ({type(err).__name__}); retry {attempt+2}/{len(DELAYS)+1} after {DELAYS[attempt]} seconds')
        sleeper(DELAYS[attempt])
    raise RuntimeError('Retry loop unexpectedly exhausted')
