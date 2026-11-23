#!/usr/bin/env python3
"""Preview community Give Props digest copy. Read-only; never sends a push."""
import os
from datetime import datetime, timezone

from preview_props_digest import target_window
from preview_props_reconciliation import (
    EMOJI, current_reactions, read_history, reconcile, score_index
)

MAX_BODY = 160


def format_digest(day, entries):
    """Deterministic, bounded OneSignal-sized copy; no send side effects."""
    if not entries:
        return None
    title = "🏆 Yesterday's Give Props!"
    lines = [f"{giver} {EMOJI[reaction]} {recipient} — {game}"
             for giver, recipient, game, reaction in entries]
    body = ""
    shown = 0
    for line in lines:
        remaining = len(lines) - shown - 1
        suffix = f" (+{remaining} more)" if remaining else ""
        candidate = (body + "; " if body else "") + line
        if len(candidate) + len(suffix) > MAX_BODY:
            break
        body = candidate
        shown += 1
    if shown == 0:
        body = f"{len(lines)} Give Props shared yesterday! 🕹️"
    elif shown < len(lines):
        body += f" (+{len(lines) - shown} more)"
    return title, body


def main():
    day, start, end = target_window(datetime.now(timezone.utc))
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    history = read_history(key, start, end)
    ids = {int(event["reaction_id"]) for event in history
           if event.get("reaction_id") is not None}
    active = current_reactions(key, ids)
    scores, players, conflicts = score_index()
    entries, excluded, unique = reconcile(history, active, scores, players)
    # Stable order regardless of API ordering; one line per reconciled reaction.
    entries.sort(key=lambda row: (row[0], row[1], row[2], row[3]))
    print(f"DAILY GIVE PROPS MESSAGE PREVIEW — {day} Eastern; NO PUSH")
    print(f"History events: {len(history)}; unique reactions: {unique}")
    print(f"Eligible Props: {len(entries)}; excluded: {sum(excluded.values())}; score ID conflicts: {conflicts}")
    message = format_digest(day, entries)
    if message is None:
        print("NO ELIGIBLE PROPS — would skip notification.")
    else:
        heading, body = message
        print(f"HEADING: {heading}")
        print(f"MESSAGE: {body}")
        print(f"Message length: {len(body)} characters (max {MAX_BODY})")
    print("PREVIEW ONLY: no OneSignal request, no awards, no state changes.")
    print("Schedule, delivery idempotency and production send are not enabled.")


if __name__ == "__main__":
    main()
