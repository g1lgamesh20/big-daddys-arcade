#!/usr/bin/env python3
"""Offline-only decision model for delivery outcome handling; no network access."""
from dataclasses import dataclass


@dataclass(frozen=True)
class DeliveryDecision:
    next_status: str
    can_attempt_send: bool


def after_reservation(status):
    if status == "reserved":
        return DeliveryDecision("reserved", False)
    if status in ("sent", "unknown"):
        return DeliveryDecision(status, False)
    raise ValueError("Unexpected delivery state")


def record_result(current_status, outcome, notification_id=None):
    if current_status != "reserved":
        raise ValueError("Only reserved deliveries can transition automatically")
    if outcome == "confirmed":
        if not isinstance(notification_id, str) or not notification_id.strip():
            raise ValueError("Confirmed delivery requires OneSignal notification ID")
        return "sent"
    if outcome in ("timeout", "network_error", "ambiguous_response", "provider_error"):
        if notification_id is not None:
            raise ValueError("Uncertain delivery must not claim notification ID")
        return "unknown"
    raise ValueError("Unrecognized delivery outcome; fail closed")
