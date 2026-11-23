#!/usr/bin/env python3
"""Read-only iScored score lookup for Give Props. No notifications or writes."""
import json
import os
import re
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from preview_props_digest import POSITIVE, read_events, target_window

URL = os.environ.get("ISCORED_READ_URL", "https://www.iScored.info/api/G1LGAMESH/getAllScores")
INITIALS = re.compile(r"[A-Z]{3}\Z")


def score_index():
    req = Request(URL, headers={"User-Agent": "BigDaddysArcadePropsPreview/1.0", "Accept": "application/json"})
    with urlopen(req, timeout=45) as response:
        payload = json.load(response)
    if not isinstance(payload, dict) or not isinstance(payload.get("scores"), list):
        raise RuntimeError("Unexpected iScored scores response")
    result, conflicts, players = {}, set(), set()
    for row in payload["scores"]:
        if not isinstance(row, dict):
            continue
        player = str(row.get("name") or "").strip().upper()
        if INITIALS.fullmatch(player):
            players.add(player)
        if row.get("id") is None:
            continue
        game = str(row.get("gameName") or "").strip()
        if not INITIALS.fullmatch(player) or not game:
            continue
        sid = str(row["id"])
        value = (player, game)
        if sid in result and result[sid] != value:
            conflicts.add(sid)
        else:
            result[sid] = value
    for sid in conflicts:
        result.pop(sid, None)
    return result, players, len(conflicts)


def main():
    day, start, end = target_window(datetime.now(timezone.utc))
    events = read_events(os.environ.get("SUPABASE_SERVICE_ROLE_KEY", ""), start, end)
    scores, players, conflicts = score_index()
    positive = [e for e in events if e.get("event_action") != "removed"
                and e.get("new_reaction") in POSITIVE]
    resolved, invalid_giver, missing_score = [], 0, 0
    emoji = {"heart": "❤️", "invader": "👾", "joystick": "🕹️",
             "gamepad": "🎮", "quarter": "🪙", "trophy": "🏆"}
    for event in positive:
        giver = str(event.get("player_initials") or "").strip().upper()
        if not INITIALS.fullmatch(giver) or giver not in players:
            invalid_giver += 1
            continue
        match = scores.get(str(event.get("score_id")))
        if match is None:
            missing_score += 1
            continue
        resolved.append((giver, match[0], match[1], event["new_reaction"]))
    print(f"READ-ONLY SCORE LOOKUP — Eastern day: {day}; NO PUSH")
    print(f"Positive history events: {len(positive)}")
    print(f"Resolved with valid iScored initials: {len(resolved)}")
    print(f"Invalid/unknown giver initials: {invalid_giver}")
    print(f"Missing/ambiguous score IDs: {missing_score}; conflicting iScored IDs: {conflicts}")
    print("Illustrative event matches (NOT final digest entries):")
    for giver, recipient, game, reaction in resolved[:8]:
        print(f"  {giver} gave {emoji[reaction]} to {recipient} on {game[:80]}")
    if len(resolved) > 8:
        print(f"  ... plus {len(resolved) - 8} more")
    print("Not yet reconciled against removals, changes, or current reaction state.")
    print("This diagnostic never sends notifications or issues trophies.")


if __name__ == "__main__":
    main()
