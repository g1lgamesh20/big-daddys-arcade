#!/usr/bin/env python3
"""Build and validate Give Props OneSignal payload. NO network send or writes."""
import json
import os
import uuid
from datetime import datetime, timezone
from urllib.parse import urlparse

from preview_props_digest import target_window
from preview_props_message import format_digest
from preview_props_reconciliation import (
    current_reactions, read_history, reconcile, score_index,
)
from verify_props_delivery_ledger import classify

APP_ID = "6aca5b1a-5845-489a-a739-4d979d7f7cb4"
SITE = "https://g1lgamesh20.github.io/big-daddys-arcade/"
NAMESPACE = uuid.UUID("28d1caae-9341-41d8-9576-79387c481ac8")


def build_payload(day, entries):
    message = format_digest(day, entries)
    if message is None:
        return None
    title, body = message
    if not body or len(body) > 160 or not title:
        raise ValueError("Unsafe digest copy")
    # OneSignal idempotency keys should be stable UUIDs, not arbitrary strings.
    key = str(uuid.uuid5(NAMESPACE, "big-daddys-arcade:give-props:" + day))
    return {
        "app_id": APP_ID,
        "included_segments": ["All"],
        "headings": {"en": title},
        "contents": {"en": body},
        "url": SITE,
        "idempotency_key": key,
        "data": {"kind": "daily_give_props_digest", "eastern_day": day},
    }


def validate_payload(payload, day):
    if payload is None:
        return
    assert payload["app_id"] == APP_ID
    assert payload["included_segments"] == ["All"]
    assert payload["data"] == {"kind": "daily_give_props_digest", "eastern_day": day}
    assert urlparse(payload["url"]).scheme == "https"
    assert uuid.UUID(payload["idempotency_key"]).version == 5
    assert len(payload["contents"]["en"]) <= 160


def main():
    day, start, end = target_window(datetime.now(timezone.utc))
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    history = read_history(key, start, end)
    ids = {int(e["reaction_id"]) for e in history if e.get("reaction_id") is not None}
    active = current_reactions(key, ids)
    scores, players, conflicts = score_index()
    if conflicts:
        raise RuntimeError("Conflicting score IDs; refuse payload")
    entries, excluded, _ = reconcile(history, active, scores, players)
    entries.sort(key=lambda row: (row[0], row[1], row[2], row[3]))
    payload = build_payload(day, entries)
    print("ONESIGNAL PAYLOAD PREVIEW — NO PUSH, NO RESERVATION, NO WRITES")
    print("Eastern day:", day, "eligible Props:", len(entries))
    if payload is None:
        print("NO ELIGIBLE PROPS — no notification payload.")
    else:
        validate_payload(payload, day)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        print("NOTE: This payload is illustrative; actual delivery requires a separate")
        print("atomic reservation, durable outcome handling, and explicit approval.")
    print("No OneSignal API call; no ledger state changed.")


if __name__ == "__main__":
    main()
