#!/usr/bin/env python3
"""Additional Hall of Legends holiday awards from approved iScored score evidence.

Christmas and New Year's Day: any approved arcade score on that Eastern day.
MAR10 and May the Fourth: approved scores on explicitly eligible game IDs.
All trophies are once per player lifetime, with no notifications, no client claims.
The post-fix journal stores original submission time; subsequent approval is fine.
Thanksgiving remains in its existing separate evaluator, untouched.
"""
import copy
import json
import os
import re
import tempfile
from datetime import datetime, date, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from iscored_timestamp import parse_iscored_time

ROOT = Path(__file__).resolve().parents[1]
JOURNAL = ROOT / "secret-score-evidence.json"
LEDGER = ROOT / "verified-challenge-awards.json"
EASTERN = ZoneInfo("America/New_York")
PLAYER = re.compile(r"^[A-Z0-9 ]{1,3}$")
FIRST_ELIGIBLE_YEAR = 2026

# IDs from the existing iScored Hall of Legends game catalog, verified Nov 25 2026.
# Donkey Kong games are deliberately excluded from MAR10: these are Mario-titled
# arcade entries, not every game in which Mario makes a cameo.
MARIO_GAME_IDS = frozenset({
    "50350",  # Dr. Mario
    "50064",  # Mario Bros.
    "50347",  # Super Mario 1-1 Speed Run
    "50346",  # Super Mario Bros.
    "50348",  # Super Mario Bros. 3
})
STAR_WARS_GAME_IDS = frozenset({
    "50001",  # Star Wars
    "50002",  # The Empire Strikes Back
    "50003",  # Return of the Jedi
    "50406",  # Sega Star Wars Trilogy
})
# (month,day): (award type, public name, optional approved iScored game IDs).
HOLIDAYS = {
    (12, 25): ("holiday_christmas", "SANTA'S HIGH SCORE HELPER", None),
    (1, 1): ("holiday_new_years_day", "NEW YEAR, NEW HIGH SCORE!", None),
    (3, 10): ("holiday_mar10", "MAR10 DAY HERO", MARIO_GAME_IDS),
    (5, 4): ("holiday_may_the_fourth", "MAY THE FOURTH BE WITH YOU!", STAR_WARS_GAME_IDS),
}


def active_on(day, kind):
    # First actual calendar occurrence after feature activation.
    # January / March / May first qualify in 2027; Christmas first in 2026.
    if kind == "holiday_christmas":
        return day >= date(2026, 12, 25)
    return day >= date(2027, 1, 1)


def activate(journal, ledger, now, *, enabled=False):
    """Pure, fail-closed transformation; no live API calls or file mutations."""
    if not enabled:
        return copy.deepcopy(ledger), []
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("Timezone-aware now required")
    if journal.get("schema_version") != 1 or not isinstance(journal.get("scores"), dict):
        raise ValueError("Malformed post-fix score journal")
    if ledger.get("schema_version") != 1 or not isinstance(ledger.get("awards"), list) or not isinstance(ledger.get("verified_plays"), list):
        raise ValueError("Malformed permanent award ledger")
    result = copy.deepcopy(ledger)
    seen = set()
    awarded = set()
    for award in result["awards"]:
        if not isinstance(award, dict) or not isinstance(award.get("id"), str) or not award["id"] or award["id"] in seen:
            raise ValueError("Malformed or duplicate existing award")
        seen.add(award["id"])
        if award.get("type") in {config[0] for config in HOLIDAYS.values()}:
            awarded.add((award["type"], str(award.get("player") or "").upper()))
    now_et = now.astimezone(EASTERN)
    candidates = {}
    for sid, row in journal["scores"].items():
        if not isinstance(row, dict) or str(row.get("score_id")) != str(sid):
            raise ValueError("Malformed score evidence")
        player = row.get("name")
        if not isinstance(player, str) or not PLAYER.fullmatch(player) or not player.strip():
            continue
        timestamp = parse_iscored_time(row.get("date"))
        if timestamp is None or timestamp > now_et:
            continue
        day = timestamp.date()
        holiday = HOLIDAYS.get((day.month, day.day))
        if not holiday:
            continue
        kind, name, game_ids = holiday
        if not active_on(day, kind) or (kind, player) in awarded:
            continue
        gid = str(row.get("game") or "").strip()
        if not gid or (game_ids is not None and gid not in game_ids):
            continue
        if isinstance(row.get("score"), bool):
            continue
        try:
            numeric_score = int(row.get("score"))
        except (TypeError, ValueError):
            continue
        if numeric_score < 0:
            continue
        key = kind, player
        candidate = (timestamp, str(sid), row, numeric_score, name)
        if key not in candidates or candidate[:2] < candidates[key][:2]:
            candidates[key] = candidate
    new = []
    for (kind, player), (timestamp, sid, row, numeric_score, name) in sorted(candidates.items()):
        award_id = kind + ":" + player
        if award_id in seen:
            continue
        award = {
            "id": award_id,
            "event_key": kind + ":" + timestamp.date().isoformat() + ":" + player,
            "type": kind,
            "name": name,
            "player": player,
            "date": timestamp.date().isoformat(),
            "game": str(row.get("gameName") or "")[:100],
            "game_id": str(row["game"]),
            "score": numeric_score,
            "score_id": sid,
            "original_submitted_at_et": timestamp.isoformat(),
            "verified_at": now.astimezone(timezone.utc).isoformat(),
            "verification_method": "postfix_approved_iscored_original_submission_time_and_whitelisted_game_id",
        }
        result["awards"].append(award)
        new.append(award)
        awarded.add((kind, player))
        seen.add(award_id)
    result["awards"].sort(key=lambda award: (str(award.get("date", "")), str(award.get("id", ""))))
    return result, new


def main():
    if os.environ.get("SEASONAL_HOLIDAY_AWARDS_ENABLED") != "1":
        print("Seasonal holiday trophies disabled")
        return
    journal = json.loads(JOURNAL.read_text(encoding="utf-8"))
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    updated, new = activate(journal, ledger, datetime.now(timezone.utc), enabled=True)
    if new:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=LEDGER.parent,
            prefix=".seasonal-holidays-", suffix=".json", delete=False
        ) as temp:
            json.dump(updated, temp, ensure_ascii=False, indent=2)
            temp.write("\n")
            filename = Path(temp.name)
        filename.replace(LEDGER)
    print("Seasonal holiday trophies:", len(new), "new lifetime trophies (NO notifications)")


if __name__ == "__main__":
    main()
