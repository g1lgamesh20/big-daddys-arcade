#!/usr/bin/env python3
"""Preview a single-subscription iPhone test push. NO SEND and NO DB writes.

The OneSignal dashboard's Test Subscriptions list does not automatically limit
API requests. Use the exact verified subscription ID and include_subscription_ids.
"""
import json
import os
import uuid

from preview_props_onesignal_payload import APP_ID, SITE

TEST_TITLE = "🧪 Give Props — Test Notification"
TEST_BODY = "DON 🕹️ VJG — Ikari Warriors"


def build_test_payload(subscription_id):
    try:
        subscription_id = str(uuid.UUID(subscription_id.strip()))
    except (ValueError, AttributeError) as exc:
        raise ValueError("Provide a valid OneSignal subscription UUID") from exc
    return {
        "app_id": APP_ID,
        "include_subscription_ids": [subscription_id],
        "headings": {"en": TEST_TITLE},
        "contents": {"en": TEST_BODY},
        "url": SITE,
        "data": {"kind": "give_props_iphone_test"},
        "idempotency_key": str(uuid.uuid5(
            uuid.UUID("91d0f1ab-0e94-48a7-b7e1-46c16a2e882b"),
            "give-props-iphone-test:" + subscription_id,
        )),
    }


def validate_test_payload(payload):
    assert payload["app_id"] == APP_ID
    assert "included_segments" not in payload
    assert "include_aliases" not in payload
    assert "filters" not in payload
    assert len(payload["include_subscription_ids"]) == 1
    assert uuid.UUID(payload["include_subscription_ids"][0])
    assert payload["data"]["kind"] == "give_props_iphone_test"


def main():
    subscription_id = os.environ.get("TEST_SUBSCRIPTION_ID", "")
    payload = build_test_payload(subscription_id)
    validate_test_payload(payload)
    print("IPHONE TARGETED TEST PAYLOAD — NO SEND, NO DATABASE WRITES")
    print("Target subscription: " + payload["include_subscription_ids"][0])
    print("Title: " + TEST_TITLE)
    print("Message: " + TEST_BODY)
    print("Targeting: include_subscription_ids (exactly one); no All segment.")
    print("Payload keys: " + ", ".join(sorted(payload.keys())))
    print("OneSignal API NOT CALLED. No API key loaded. No production ledger touched.")
    print("Operator must verify UUID against their sole Test Subscription in dashboard.")
    print("A separate, explicitly approved sender is required before any live test.")


if __name__ == "__main__":
    main()
