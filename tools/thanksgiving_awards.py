#!/usr/bin/env python3
"""Award one lifetime TURKEY DAY GAMER trophy for an approved Thanksgiving submission.

Prospective, 2026 onward. The durable post-fix approved-score evidence journal
preserves the original iScored submission timestamp; later approvals still count.
No requirement to beat a score, no OneSignal push, no other holiday changes.
"""
import copy
import json
import os
import re
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from iscored_timestamp import parse_iscored_time

ROOT = Path(__file__).resolve().parents[1]
JOURNAL = ROOT / "secret-score-evidence.json"
LEDGER = ROOT / "verified-challenge-awards.json"
EASTERN = ZoneInfo("America/New_York")
CUTOVER = date(2026, 11, 26)
PLAYER_RE = re.compile(r"^[A-Z0-9 ]{1,3}$")
AWARD_TYPE = "holiday_thanksgiving"
AWARD_NAME = "TURKEY DAY GAMER"


def thanksgiving(year):
    """Fourth Thursday of November, in Eastern local calendar dates."""
    first = date(year, 11, 1)
    first_thursday = 1 + (3 - first.weekday()) % 7
    return date(year, 11, first_thursday + 21)


def activate(journal, ledger, now, *, enabled=False):
    """Return (ledger, new awards) without mutating either input."""
    if not enabled:
        return copy.deepcopy(ledger), []
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("Timezone-aware clock required")
    if journal.get("schema_version") != 1 or not isinstance(journal.get("scores"), dict):
        raise ValueError("Malformed approved-score journal")
    if ledger.get("schema_version") != 1 or not isinstance(ledger.get("awards"), list) or not isinstance(ledger.get("verified_plays"), list):
        raise ValueError("Malformed permanent award ledger")
    out = copy.deepcopy(ledger)
    existing = set()
    awarded_players = set()
    for entry in out["awards"]:
        if not isinstance(entry, dict) or not isinstance(entry.get("id"), str) or not entry["id"] or entry["id"] in existing:
            raise ValueError("Invalid or duplicate award in existing ledger")
        existing.add(entry["id"])
        if entry.get("type") == AWARD_TYPE:
            awarded_players.add(str(entry.get("player") or "").upper())
    candidates = {}
    now_et = now.astimezone(EASTERN)
    for sid, score in journal["scores"].items():
        if not isinstance(score, dict) or str(score.get("score_id")) != str(sid):
            raise ValueError("Invalid journal score record")
        player = score.get("name")
        if not isinstance(player, str) or not PLAYER_RE.fullmatch(player) or not player.strip():
            continue
        submitted = parse_iscored_time(score.get("date"))
        if submitted is None or submitted > now_et:
            continue
        day = submitted.date()
        if day < CUTOVER or day != thanksgiving(day.year) or player in awarded_players:
            continue
        if not str(score.get("game") or "").strip() or isinstance(score.get("score"), bool):
            continue
        try:
            score_value = int(score.get("score"))
        except (ValueError, TypeError):
            continue
        if score_value < 0:
            continue
        candidate = (submitted, str(sid), score, score_value)
        if player not in candidates or candidate[:2] < candidates[player][:2]:
            candidates[player] = candidate
    added = []
    for player, (submitted, sid, score, score_value) in sorted(candidates.items()):
        award_id = AWARD_TYPE + ":" + player
        if award_id in existing:
            continue
        award = {
            "id": award_id,
            "event_key": "thanksgiving:" + submitted.date().isoformat() + ":" + player,
            "type": AWARD_TYPE,
            "name": AWARD_NAME,
            "player": player,
            "date": submitted.date().isoformat(),
            "game": str(score.get("gameName") or "")[:100],
            "game_id": str(score["game"]),
            "score": score_value,
            "score_id": sid,
            "original_submitted_at_et": submitted.isoformat(),
            "verified_at": now.astimezone(timezone.utc).isoformat(),
            "verification_method": "postfix_approved_iscored_original_submission_time",
        }
        out["awards"].append(award)
        added.append(award)
        existing.add(award_id)
        awarded_players.add(player)
    out["awards"].sort(key=lambda a: (str(a.get("date", "")), str(a.get("id", ""))))
    return out, added


def main():
    if os.environ.get("THANKSGIVING_AWARDS_ENABLED") != "1":
        print("Thanksgiving award activation disabled")
        return
    journal = json.loads(JOURNAL.read_text(encoding="utf-8"))
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    updated, added = activate(journal, ledger, datetime.now(timezone.utc), enabled=True)
    if added:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=LEDGER.parent,
            prefix=".thanksgiving-", suffix=".json", delete=False
        ) as tmp:
            json.dump(updated, tmp, ensure_ascii=False, indent=2)
            tmp.write("\n")
            temp_path = Path(tmp.name)
        temp_path.replace(LEDGER)
    print("TURKEY DAY GAMER: ", len(added), "new lifetime trophies; no push")


if __name__ == "__main__":
    main()
