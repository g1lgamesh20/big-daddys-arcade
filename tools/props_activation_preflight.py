#!/usr/bin/env python3
"""Schedule activation preflight. Never imports or calls production sender.

No credentials, no network, no database, no notification delivery.
"""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from dry_run_props_schedule import eligible_time
from preview_props_digest import target_window

NY = ZoneInfo("America/New_York")


def schedule_decision(now, already_claimed=False):
    if not eligible_time(now):
        return "SKIP: outside 09:30–11:00 Eastern"
    if already_claimed:
        return "SKIP: existing reservation or delivery"
    return "PREVIEW ONLY: candidate delivery window; no send authorized"


def main():
    now = datetime.now(timezone.utc)
    day, _, _ = target_window(now)
    print("GIVE PROPS ACTIVATION PREFLIGHT — NO SEND / NO WRITES")
    print("Current Eastern:", now.astimezone(NY).isoformat())
    print("Previous Eastern day:", day)
    print("Current decision:", schedule_decision(now))
    print("Duplicate simulation:", schedule_decision(now, already_claimed=True))
    for label, moment in (
        ("EDT before", datetime(2026, 7, 15, 13, 29, tzinfo=timezone.utc)),
        ("EDT start", datetime(2026, 7, 15, 13, 30, tzinfo=timezone.utc)),
        ("EST before", datetime(2026, 11, 23, 14, 29, tzinfo=timezone.utc)),
        ("EST start", datetime(2026, 11, 23, 14, 30, tzinfo=timezone.utc)),
        ("delayed 60m", datetime(2026, 11, 23, 15, 30, tzinfo=timezone.utc)),
        ("delayed 91m", datetime(2026, 11, 23, 16, 1, tzinfo=timezone.utc)),
    ):
        print(label + ":", moment.astimezone(NY).isoformat(), "=>", schedule_decision(moment))
    print("GitHub scheduled runs may be delayed or skipped; this is NOT a guarantee of 09:30 delivery.")
    print("No production sender imported, no OneSignal, no Supabase, no credentials.")


if __name__ == "__main__":
    main()
