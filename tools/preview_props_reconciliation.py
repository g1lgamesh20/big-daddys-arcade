#!/usr/bin/env python3
"""Preview yesterday's active Give Props, with no writes or push delivery.

One row per reaction identity; read current arcade_reactions to exclude deleted,
subsequently changed Props. This is NOT a notification sender.
"""
import json
import os
from collections import Counter
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from preview_props_digest import BASE, PAGE_SIZE, POSITIVE, target_window

NEGATIVE = {"poop", "angry"}
ELIGIBLE = POSITIVE | NEGATIVE
from preview_props_score_lookup import INITIALS, score_index

EMOJI = {"heart": "❤️", "invader": "👾", "joystick": "🕹️",
         "gamepad": "🎮", "quarter": "🪙", "trophy": "🏆", "poop": "💩", "angry": "😡"}


def supabase_rows(key, table, params):
    if not key:
        raise RuntimeError("Missing SUPABASE_SERVICE_ROLE_KEY")
    req = Request(BASE + "/rest/v1/" + table + "?" + urlencode(params),
                  headers={"apikey": key, "Authorization": "Bearer " + key,
                           "Accept": "application/json"})
    with urlopen(req, timeout=30) as response:
        result = json.load(response)
    if not isinstance(result, list):
        raise RuntimeError("Unexpected Supabase response")
    return result


def read_history(key, start, end):
    rows, offset = [], 0
    while True:
        params = [
            ("select", "id,reaction_id,score_id,player_initials,new_reaction,event_action"),
            ("occurred_at", "gte." + start),
            ("occurred_at", "lt." + end),
            ("order", "id.asc"),
            ("limit", str(PAGE_SIZE)),
            ("offset", str(offset)),
        ]
        page = supabase_rows(key, "arcade_reaction_events", params)
        rows.extend(page)
        if len(page) < PAGE_SIZE:
            return rows
        offset += PAGE_SIZE
        if offset >= 10000:
            raise RuntimeError("Reaction event history exceeded preview safety limit")


def current_reactions(key, ids):
    found = {}
    identifiers = sorted(ids)
    for offset in range(0, len(identifiers), 100):
        group = identifiers[offset:offset + 100]
        params = [("select", "id,score_id,player_initials,reaction"),
                  ("id", "in.(" + ",".join(str(i) for i in group) + ")"),
                  ("limit", "101")]
        rows = supabase_rows(key, "arcade_reactions", params)
        if len(rows) > 100:
            raise RuntimeError("Unexpected reaction lookup size")
        for row in rows:
            rid = int(row["id"])
            if rid in found:
                raise RuntimeError("Duplicate reaction ID in current-state lookup")
            found[rid] = row
    return found


def reconcile(events, active, scores, players):
    latest = {}
    for event in events:
        rid = event.get("reaction_id")
        if rid is None:
            continue
        rid = int(rid)
        # Ordered by event ID; last change to each reaction wins.
        latest[rid] = event
    counts = Counter()
    entries = []
    for rid, event in latest.items():
        if event.get("event_action") == "removed" or event.get("new_reaction") not in ELIGIBLE:
            counts["not_eligible_at_day_end"] += 1
            continue
        row = active.get(rid)
        if row is None:
            counts["since_removed"] += 1
            continue
        if row.get("reaction") != event.get("new_reaction"):
            counts["since_changed"] += 1
            continue
        if str(row.get("score_id")) != str(event.get("score_id")):
            counts["score_mismatch"] += 1
            continue
        giver = str(event.get("player_initials") or "").strip().upper()
        if giver != str(row.get("player_initials") or "").strip().upper():
            counts["giver_mismatch"] += 1
            continue
        if not INITIALS.fullmatch(giver) or giver not in players:
            counts["invalid_giver"] += 1
            continue
        score = scores.get(str(row["score_id"]))
        if score is None:
            counts["unresolved_score"] += 1
            continue
        recipient, game = score
        entries.append((giver, recipient, game, event["new_reaction"]))
    return entries, counts, len(latest)


def main():
    day, start, end = target_window(datetime.now(timezone.utc))
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    history = read_history(key, start, end)
    ids = {int(e["reaction_id"]) for e in history if e.get("reaction_id") is not None}
    active = current_reactions(key, ids)
    scores, players, conflicts = score_index()
    entries, excluded, unique = reconcile(history, active, scores, players)
    print(f"READ-ONLY RECONCILIATION — Eastern day: {day}; NO PUSH")
    print(f"History events: {len(history)}; unique reaction identities: {unique}")
    print(f"Eligible active arcade reactions: {len(entries)}")
    print(f"Excluded: {dict(sorted(excluded.items()))}")
    print(f"Conflicting iScored IDs: {conflicts}")
    print("Preview only (not sent):")
    for giver, recipient, game, reaction in entries[:8]:
        print(f"  {giver} gave {EMOJI[reaction]} to {recipient} on {game[:80]}")
    if len(entries) > 8:
        print(f"  ... plus {len(entries) - 8} more")
    print("No notifications sent. Delivery schedule, state, and idempotency are NOT enabled.")


if __name__ == "__main__":
    main()
