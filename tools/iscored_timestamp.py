#!/usr/bin/env python3
"""Interpret iScored public score timestamps using developer-confirmed server timezone.

Dan (iScored) confirmed 2026-11-19 that the API uses Central Time for
timezone-free dates, and that an approval-time-overwrite bug is now fixed.
Pre-fix records might retain an approval-altered timestamp; parsing a date
cannot establish its historical provenance or guarantee its eligibility.
No score updates, awards, or notifications are performed by this helper.
"""
from datetime import datetime
from zoneinfo import ZoneInfo

SOURCE = ZoneInfo('America/Chicago')
EASTERN = ZoneInfo('America/New_York')
FORMATS = (
    '%m/%d/%Y %I:%M:%S %p',
    '%m/%d/%Y %I:%M %p',
    '%m/%d/%Y %H:%M:%S',
    '%Y-%m-%d %H:%M:%S',
    '%Y-%m-%d %H:%M',
)

def parse_iscored_time(value):
    """Return aware Eastern datetime, or None for missing/malformed timestamps.

    Explicit UTC/offset values retain their explicit offset. Naive timestamps
    are Central local wall clock, including automatic DST rules.
    """
    if value is None or value == '':
        return None
    s = str(value).strip()
    if not s:
        return None
    try:
        d = datetime.fromisoformat(s.replace('Z', '+00:00'))
    except ValueError:
        d = None
        for fmt in FORMATS:
            try:
                d = datetime.strptime(s,fmt)
                break
            except ValueError:
                pass
    if d is None:
        return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=SOURCE)
    return d.astimezone(EASTERN)
