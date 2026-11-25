#!/usr/bin/env python3
"""Merge permanent, anonymous Easter Egg claims into the verified arcade award ledger.

No push notifications. One lifetime award per initials; no player authentication
is claimed. Fail closed on an unavailable or malformed public claim feed.
"""
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "verified-challenge-awards.json"
CLAIMS_URL = "https://jrqzwlowxofnyqpmjgkg.supabase.co/functions/v1/arcade-easter-egg"


def merge(ledger, claims):
    if ledger.get("schema_version") != 1 or not isinstance(ledger.get("awards"), list):
        raise ValueError("Invalid permanent award ledger")
    if claims.get("schema_version") != 1 or not isinstance(claims.get("claims"), list):
        raise ValueError("Invalid Easter Egg claim response")
    updated = json.loads(json.dumps(ledger))
    existing = {a.get("id") for a in updated["awards"] if isinstance(a, dict)}
    added = []
    for item in claims["claims"]:
        if not isinstance(item, dict):
            raise ValueError("Invalid claim record")
        player = item.get("player_initials")
        when = item.get("claimed_at")
        if not isinstance(player, str) or not 1 <= len(player) <= 3 or not player.strip() or any(c not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 " for c in player):
            raise ValueError("Invalid claimed initials")
        if not isinstance(when, str):
            raise ValueError("Missing claim timestamp")
        dt = datetime.fromisoformat(when.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            raise ValueError("Naive claim timestamp")
        identifier = "easter_egg:" + player
        if identifier in existing:
            continue
        award = {"id": identifier, "event_key": "easter_egg:" + player,
                 "type": "easter_egg", "name": "Easter Egg", "player": player,
                 "date": dt.astimezone(timezone.utc).date().isoformat(),
                 "verified_at": dt.isoformat(),
                 "verification_method": "player_claimed_secret_discovery_no_identity_verification"}
        updated["awards"].append(award)
        existing.add(identifier)
        added.append(award)
    return updated, added


def main():
    response = urlopen(Request(CLAIMS_URL, headers={"Accept": "application/json",
                                                    "User-Agent": "BigDaddysArcadeEasterEggSync/1.0"}), timeout=12)
    if response.status != 200:
        raise RuntimeError("Claim endpoint unavailable")
    claims = json.load(response)
    current = json.loads(LEDGER.read_text(encoding="utf-8"))
    next_ledger, added = merge(current, claims)
    if added:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=LEDGER.parent,
                                         prefix=".easter-egg-", suffix=".json", delete=False) as temp:
            json.dump(next_ledger, temp, ensure_ascii=False, indent=2)
            temp.write("\n")
            tmp_path = Path(temp.name)
        tmp_path.replace(LEDGER)
    print("Easter Egg claims synchronized:", len(added), "new permanent awards (no notifications)")


if __name__ == "__main__":
    main()
