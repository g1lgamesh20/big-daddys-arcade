#!/usr/bin/env python3
"""Fail-closed daily community digest sender. Disabled unless explicitly enabled.

Do not add an enabled workflow until operator approves production broadcast.
"""
import json
import os
import sys
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from dry_run_props_schedule import eligible_time
from preview_props_digest import target_window
from preview_props_onesignal_payload import build_payload, validate_payload
from preview_props_reconciliation import current_reactions, read_history, reconcile, score_index
from props_delivery_integration import plan_delivery, read_ledger
from verify_props_delivery_ledger import BASE

API_URL = "https://api.onesignal.com/notifications"
CONFIRMATION = "ENABLE COMMUNITY GIVE PROPS DIGEST"
RPC_BASE = BASE + "/rest/v1/rpc/"


def authorized(flag, confirmation, now):
    if flag != "true" or confirmation != CONFIRMATION:
        raise RuntimeError("Production sender disabled: explicit authorization required")
    if not eligible_time(now):
        raise RuntimeError("Outside 09:30–11:00 Eastern delivery window")


def rpc(key, name, body):
    req = Request(RPC_BASE + name, data=json.dumps(body).encode("utf-8"),
                  headers={"apikey": key, "Authorization": "Bearer " + key,
                           "Content-Type": "application/json", "Accept": "application/json"},
                  method="POST")
    with urlopen(req, timeout=20) as response:
        result = json.load(response)
    if type(result) is not bool:
        raise RuntimeError("Unexpected Supabase RPC result")
    return result


def reserve(key, day):
    return rpc(key, "arcade_reserve_props_digest", {"p_eastern_day": day})


def record(key, day, outcome, notification_id=None):
    return rpc(key, "arcade_record_props_digest_outcome",
               {"p_eastern_day": day, "p_outcome": outcome,
                "p_notification_id": notification_id})


def send_notification(api_key, payload):
    req = Request(API_URL, data=json.dumps(payload).encode("utf-8"),
                  headers={"Authorization": "Key " + api_key,
                           "Content-Type": "application/json",
                           "Accept": "application/json"}, method="POST")
    with urlopen(req, timeout=30) as response:
        result = json.load(response)
    if not isinstance(result, dict) or not isinstance(result.get("id"), str) or not result["id"].strip():
        raise RuntimeError("Ambiguous OneSignal response: missing notification ID")
    return result["id"]


def deliver(day, payload, key, api_key, reserve_fn=reserve,
            send_fn=send_notification, record_fn=record):
    """At most one send attempt, after an atomic claim. Never retry automatically."""
    if not reserve_fn(key, day):
        return "BLOCKED: reservation already exists; no push attempted"
    # After successful reservation, every failure is uncertain. The ledger
    # remains reserved if recording fails, which also blocks future sends.
    try:
        notification_id = send_fn(api_key, payload)
    except Exception:
        try:
            recorded = record_fn(key, day, "unknown")
            if not recorded:
                raise RuntimeError("Could not mark reserved delivery unknown")
        except Exception as exc:
            raise RuntimeError("Send outcome uncertain; ledger may remain reserved. Inspect manually.") from exc
        raise RuntimeError("OneSignal send outcome uncertain; marked unknown; NO RETRY") from None
    try:
        if not record_fn(key, day, "sent", notification_id):
            raise RuntimeError("Sent outcome transition refused")
    except Exception as exc:
        raise RuntimeError("OneSignal accepted push, but ledger confirmation failed; NO RETRY. Inspect manually.") from exc
    return "OneSignal accepted notification " + notification_id + "; ledger marked sent"


def main():
    now = datetime.now(timezone.utc)
    authorized(os.environ.get("ENABLE_PROPS_COMMUNITY_SEND", ""),
               os.environ.get("PROPS_SEND_CONFIRMATION", ""), now)
    day, start, end = target_window(now)
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    api_key = os.environ.get("ONESIGNAL_REST_API_KEY", "").strip()
    if not key or not api_key:
        raise RuntimeError("Missing required credentials; no send")
    history = read_history(key, start, end)
    ids = {int(e["reaction_id"]) for e in history if e.get("reaction_id") is not None}
    active = current_reactions(key, ids)
    scores, players, conflicts = score_index()
    entries, _, _ = reconcile(history, active, scores, players)
    entries.sort(key=lambda row: (row[0], row[1], row[2], row[3]))
    decision, payload = plan_delivery(day, entries, conflicts, read_ledger(key, day))
    if payload is None:
        print(decision)
        return
    validate_payload(payload, day)
    if payload["included_segments"] != ["All"]:
        raise RuntimeError("Unexpected digest audience")
    print("Community digest send authorized; target Eastern day:", day)
    print(deliver(day, payload, key, api_key))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("PRODUCTION DIGEST STOPPED:", str(exc), file=sys.stderr)
        sys.exit(1)
