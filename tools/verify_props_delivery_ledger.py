#!/usr/bin/env python3
"""Read-only check for persistent digest ledger; no reservation or push."""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date

BASE = "https://jrqzwlowxofnyqpmjgkg.supabase.co"
TABLE = "arcade_props_digest_deliveries"


def classify(rows, day):
    if len(rows) > 1:
        raise RuntimeError("Duplicate ledger rows: refuse to proceed")
    if not rows:
        return "AVAILABLE (no reservation exists; NO WRITE performed)"
    row = rows[0]
    expected = "big-daddys-arcade:give-props:" + day
    if row.get("idempotency_key") != expected:
        raise RuntimeError("Unexpected idempotency key: refuse to proceed")
    status = row.get("status")
    if status == "sent":
        return "ALREADY SENT — must never send again"
    if status == "reserved":
        return "RESERVED — do not send; inspect before retry"
    if status == "unknown":
        return "UNKNOWN OUTCOME — do not send; manual reconciliation required"
    raise RuntimeError("Unrecognized delivery status: refuse to proceed")


def main():
    from preview_props_digest import target_window
    from datetime import datetime, timezone
    day, _, _ = target_window(datetime.now(timezone.utc))
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not key:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY missing")
    url = BASE + "/rest/v1/" + TABLE + "?" + urllib.parse.urlencode({
        "select": "eastern_day,status,idempotency_key,sent_at",
        "eastern_day": "eq." + day,
    })
    req = urllib.request.Request(url, headers={
        "apikey": key, "Authorization": "Bearer " + key,
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            rows = json.load(response)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(
            f"Ledger verification failed HTTP {exc.code}; table/permissions may not be configured"
        ) from exc
    print(f"READ-ONLY DELIVERY LEDGER CHECK — {day} Eastern")
    print(classify(rows, day))
    print("NO PUSH, NO LEDGER WRITE, NO TROPHIES, NO NEWS ENTRY.")
    print("IMPORTANT: This only verifies the ledger. Atomic reservation and sending are NOT enabled.")


if __name__ == "__main__":
    main()
