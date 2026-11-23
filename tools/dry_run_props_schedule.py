#!/usr/bin/env python3
"""Scheduled Give Props dry run. Absolutely no notifications or writes.

Cron uses UTC slots across both DST offsets; Eastern local-time gate ensures
the digest is never considered before 09:30 America/New_York.
"""
import argparse
import json
from datetime import datetime, time, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from preview_props_message import format_digest
from preview_props_reconciliation import (
    current_reactions, read_history, reconcile, score_index
)
from preview_props_digest import target_window
import os

NY = ZoneInfo("America/New_York")
STATE_PATH = Path(__file__).resolve().parents[1] / "props-digest-state.json"


def eligible_time(now):
    local = now.astimezone(NY)
    return time(9, 30) <= local.time().replace(tzinfo=None) < time(11, 0)


def already_sent(day, path=STATE_PATH):
    if not path.exists():
        return False
    state = json.loads(path.read_text(encoding="utf-8"))
    if state.get("schema_version") != 1 or not isinstance(state.get("sent_days"), dict):
        raise RuntimeError("Invalid digest state; refusing to proceed")
    return day in state["sent_days"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manual-preview", action="store_true",
                        help="Allow preview outside 09:30–11:00 ET; never sends")
    args = parser.parse_args()
    now = datetime.now(timezone.utc)
    day, start, end = target_window(now)
    print(f"GIVE PROPS SCHEDULER DRY RUN — target {day} ET")
    print(f"Current ET: {now.astimezone(NY).isoformat()}")
    if not eligible_time(now) and not args.manual_preview:
        print("OUTSIDE DELIVERY WINDOW — skipping safely.")
        return
    if already_sent(day):
        print("ALREADY MARKED SENT — would skip duplicate.")
        return
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    history = read_history(key, start, end)
    ids = {int(e["reaction_id"]) for e in history if e.get("reaction_id") is not None}
    active = current_reactions(key, ids)
    scores, players, conflicts = score_index()
    entries, excluded, _ = reconcile(history, active, scores, players)
    entries.sort(key=lambda row: (row[0], row[1], row[2], row[3]))
    if conflicts:
        raise RuntimeError("Ambiguous iScored IDs; refusing to build digest")
    message = format_digest(day, entries)
    if message is None:
        print("NO ELIGIBLE PROPS — would skip sending.")
    else:
        print(f"WOULD SEND for {day} ET (not actually sent):")
        print("HEADING: " + message[0])
        print("MESSAGE: " + message[1])
        print("Idempotency identifier: big-daddys-arcade:give-props:" + day)
    print("DRY RUN ONLY — no OneSignal call, state write, trophies, or news entry.")
    print("NOTE: persistent send-state and atomic delivery still require implementation.")


if __name__ == "__main__":
    main()
