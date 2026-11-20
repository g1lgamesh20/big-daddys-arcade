#!/usr/bin/env python3
"""Read-only refresh-backstop gate for GitHub Actions.

This does not refresh scores, change achievement files, or send notifications.
When the last successful refresh is older than 42 minutes, a separate GitHub
workflow may dispatch the EXISTING update-legends.yml workflow. The primary
workflow still owns medal notification deduplication and commit safety.
"""
import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from refresh_health import parse_utc

DEFAULT_MAX_AGE_MINUTES = 42

def should_dispatch(heartbeat, now, max_age_minutes=DEFAULT_MAX_AGE_MINUTES):
    if now.tzinfo is None:
        raise ValueError('Current time must be timezone-aware')
    if max_age_minutes <= 0:
        raise ValueError('Threshold must be positive')
    if not isinstance(heartbeat,dict) or heartbeat.get('schema_version') != 1:
        return True, 'missing_or_invalid_heartbeat'
    past=parse_utc(heartbeat.get('last_success_at'))
    if past is None:
        return True, 'missing_or_invalid_timestamp'
    delta=(now.astimezone(timezone.utc)-past).total_seconds()/60
    if delta < -5:
        return True, 'untrusted_future_heartbeat'
    if delta <= max_age_minutes:
        return False, 'fresh'
    return True, 'stale'

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--heartbeat',default='refresh-health.json')
    parser.add_argument('--github-output',default='')
    args=parser.parse_args()
    path=Path(args.heartbeat)
    try:
        data=json.loads(path.read_text(encoding='utf-8')) if path.exists() else None
    except (ValueError, OSError):
        data=None
    dispatch,reason=should_dispatch(data,datetime.now(timezone.utc))
    print('Score refresh backstop:',reason, '- dispatch needed:',str(dispatch).lower())
    if args.github_output:
        with open(args.github_output,'a',encoding='utf-8') as output:
            output.write('dispatch='+str(dispatch).lower()+'\n')
            output.write('reason='+reason+'\n')
    return dispatch

if __name__ == '__main__':
    main()
