#!/usr/bin/env python3
"""Read-only, no-push Supabase Give Props event audit.

Never print device hashes, credentials, or raw event records. This is NOT a
notification sender and intentionally cannot invoke OneSignal.
"""
import json
import os
from datetime import datetime, timedelta, time, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")
POSITIVE = {"heart", "invader", "joystick", "gamepad", "quarter", "trophy"}
BASE = "https://jrqzwlowxofnyqpmjgkg.supabase.co"
PAGE_SIZE = 500


def target_window(now):
    local = now.astimezone(NY)
    day = local.date() - timedelta(days=1)
    start = datetime.combine(day, time.min, NY).astimezone(timezone.utc)
    end = datetime.combine(day + timedelta(days=1), time.min, NY).astimezone(timezone.utc)
    return day.isoformat(), start.isoformat(), end.isoformat()


def read_events(key, start, end):
    if not key:
        raise RuntimeError("Missing SUPABASE_SERVICE_ROLE_KEY")
    result = []
    offset = 0
    while True:
        query = urlencode({
            "select": "id,score_id,player_initials,old_reaction,new_reaction,event_action,occurred_at",
            "occurred_at": f"gte.{start}",
            "order": "id.asc",
            "limit": PAGE_SIZE,
            "offset": offset,
        })
        # PostgREST needs both range predicates for the same column; urlencode
        # cannot express repeated keys using a plain dict.
        query = query.replace("occurred_at=gte.", "occurred_at=gte.") + "&" + urlencode({"occurred_at": f"lt.{end}"})
        req = Request(BASE + "/rest/v1/arcade_reaction_events?" + query,
                      headers={"apikey": key, "Authorization": "Bearer " + key,
                               "Accept": "application/json"})
        with urlopen(req, timeout=30) as response:
            page = json.load(response)
        if not isinstance(page, list):
            raise RuntimeError("Unexpected Supabase event response")
        result.extend(page)
        if len(page) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
        if offset >= 10000:
            raise RuntimeError("Event pagination safety limit reached")
    return result


def main():
    day, start, end = target_window(datetime.now(timezone.utc))
    events = read_events(os.environ.get("SUPABASE_SERVICE_ROLE_KEY", ""), start, end)
    counts = {"added": 0, "changed": 0, "removed": 0}
    positive = 0
    for event in events:
        action = event.get("event_action")
        if action not in counts:
            raise RuntimeError("Unexpected reaction history action")
        counts[action] += 1
        if action != "removed" and event.get("new_reaction") in POSITIVE:
            positive += 1
    print(f"DRY RUN ONLY — no push sent. Eastern day: {day}")
    print(f"History events: {len(events)}; adds={counts['added']}; changes={counts['changed']}; removals={counts['removed']}")
    print(f"Positive add/change events (not deduplicated or score-resolved): {positive}")
    print("Recipient/game lookup and final active-reaction reconciliation are NOT implemented.")
    print("This preview does not send or award anything.")


if __name__ == "__main__":
    main()
