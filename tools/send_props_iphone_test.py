#!/usr/bin/env python3
"""Manually authorized single-iPhone OneSignal test. Never a community broadcast."""
import json
import os
import sys
import uuid
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from preview_props_iphone_test import build_test_payload, validate_test_payload

# This UUID is the sole Test Subscription confirmed by the operator.
ALLOWED_SUBSCRIPTION = "157661cb-d87c-43b7-9dc9-fb9042da17ce"
CONFIRMATION = "SEND TEST TO MY IPHONE ONLY"
API_URL = "https://api.onesignal.com/notifications"


def prepare(subscription, confirmation, run_id):
    if confirmation != CONFIRMATION:
        raise ValueError("Explicit manual confirmation phrase required")
    if not run_id or not run_id.isdecimal():
        raise ValueError("GitHub run ID required")
    try:
        requested = str(uuid.UUID(subscription.strip()))
    except (ValueError, AttributeError) as exc:
        raise ValueError("Invalid subscription ID") from exc
    if requested != ALLOWED_SUBSCRIPTION:
        raise ValueError("Target is not the operator-approved iPhone subscription")
    payload = build_test_payload(requested)
    validate_test_payload(payload)
    if payload["include_subscription_ids"] != [ALLOWED_SUBSCRIPTION]:
        raise ValueError("Target mismatch")
    # Unique for each explicitly approved run; no collision with the prior
    # read-only preview or with production digest idempotency keys.
    payload["idempotency_key"] = str(uuid.uuid5(
        uuid.UUID("5bb8f638-218f-4fb5-8c51-1e32d1254058"),
        "give-props-iphone-manual-test:" + run_id,
    ))
    return payload


def main():
    payload = prepare(
        os.environ.get("TEST_SUBSCRIPTION_ID", ""),
        os.environ.get("SEND_CONFIRMATION", ""),
        os.environ.get("GITHUB_RUN_ID", ""),
    )
    api_key = os.environ.get("ONESIGNAL_REST_API_KEY", "").strip()
    if not api_key:
        raise ValueError("Missing ONESIGNAL_REST_API_KEY secret")
    print("AUTHORIZED SINGLE-IPHONE TEST — no schedule, no production ledger")
    print("Target: one allowlisted Test Subscription; no All audience.")
    request = Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": "Key " + api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=30) as response:
            result = json.load(response)
    except HTTPError as exc:
        # Don't expose provider response, credentials or full request.
        raise RuntimeError(f"OneSignal HTTP {exc.code}; inspect dashboard before retry") from None
    except (URLError, TimeoutError) as exc:
        raise RuntimeError("OneSignal outcome uncertain; inspect dashboard before retry") from None
    if not isinstance(result, dict) or not result.get("id"):
        raise RuntimeError("OneSignal response lacks notification ID; inspect dashboard before retry")
    print("OneSignal accepted targeted test; notification ID:", result["id"])
    print("Recipients reported:", result.get("recipients", "not reported"))
    print("Acceptance does not guarantee delivery; verify on iPhone.")
    print("No digest reservation or delivery ledger changed.")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, RuntimeError) as exc:
        print("Test not confirmed:", exc, file=sys.stderr)
        sys.exit(1)
