#!/usr/bin/env python3
"""Production digest delivery plan and fail-closed simulation. NO SEND.

No OneSignal credentials, no Supabase reservation RPC, no HTTP POST, no writes.
Production sending MUST be implemented in a separately reviewed change.
"""
import json
import os
from datetime import datetime, timezone

from preview_props_digest import target_window
from preview_props_onesignal_payload import build_payload, validate_payload
from preview_props_reconciliation import current_reactions, read_history, reconcile, score_index
from props_delivery_outcomes import after_reservation, record_result
from verify_props_delivery_ledger import classify, BASE, TABLE
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def read_ledger(key, day):
    if not key:
        raise RuntimeError("Missing SUPABASE_SERVICE_ROLE_KEY")
    query = urlencode({"select": "eastern_day,status,idempotency_key,sent_at",
                       "eastern_day": "eq." + day})
    req = Request(BASE + "/rest/v1/" + TABLE + "?" + query,
                  headers={"apikey": key, "Authorization": "Bearer " + key,
                           "Accept": "application/json"})
    with urlopen(req, timeout=20) as response:
        rows = json.load(response)
    if not isinstance(rows, list):
        raise RuntimeError("Unexpected delivery ledger response")
    return rows


def plan_delivery(day, entries, conflicts, ledger_rows):
    """Return a dry-run decision; never reserve or send."""
    state = classify(ledger_rows, day)
    if conflicts:
        return "BLOCKED: ambiguous iScored score IDs", None
    if not state.startswith("AVAILABLE"):
        return "BLOCKED: " + state, None
    payload = build_payload(day, entries)
    if payload is None:
        return "SKIP: no eligible arcade reactions", None
    validate_payload(payload, day)
    return "READY FOR FUTURE RESERVATION (NOT AUTHORIZED TO SEND)", payload


def simulate_outcome(outcome):
    """Test state decisions without calling Supabase or OneSignal."""
    if outcome == "confirmed":
        result = record_result("reserved", "confirmed", "simulated-provider-id")
    else:
        result = record_result("reserved", outcome)
    assert after_reservation(result).can_attempt_send is False
    return result


def main():
    day, start, end = target_window(datetime.now(timezone.utc))
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    history = read_history(key, start, end)
    ids = {int(e["reaction_id"]) for e in history if e.get("reaction_id") is not None}
    active = current_reactions(key, ids)
    scores, players, conflicts = score_index()
    entries, excluded, _ = reconcile(history, active, scores, players)
    entries.sort(key=lambda row: (row[0], row[1], row[2], row[3]))
    ledger = read_ledger(key, day)
    decision, payload = plan_delivery(day, entries, conflicts, ledger)
    print("STAGE 3 PRODUCTION INTEGRATION — READ-ONLY / NO SEND")
    print("Eastern day:", day, "| eligible Props:", len(entries),
          "| excluded:", sum(excluded.values()), "| conflicts:", conflicts)
    print("Decision:", decision)
    if payload:
        print("Heading:", payload["headings"]["en"])
        print("Message:", payload["contents"]["en"])
        print("UUIDv5 idempotency key:", payload["idempotency_key"])
        print("Audience:", payload["included_segments"])
    for scenario in ("confirmed", "timeout", "network_error",
                     "ambiguous_response", "provider_error"):
        print("SIMULATED", scenario, "=>", simulate_outcome(scenario),
              "(no retry)")
    print("NO OneSignal call, NO reservation RPC, NO ledger writes, NO schedule activation.")


if __name__ == "__main__":
    main()
