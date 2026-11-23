import sys
import unittest
import uuid
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from preview_props_onesignal_payload import build_payload, validate_payload


class PayloadTests(unittest.TestCase):
    def test_no_props(self):
        self.assertIsNone(build_payload("2026-11-22", []))

    def test_expected_payload(self):
        day = "2026-11-22"
        entries = [("DON", "VJG", "Ikari Warriors", "joystick")]
        p = build_payload(day, entries)
        validate_payload(p, day)
        self.assertEqual(p["included_segments"], ["All"])
        self.assertEqual(p["contents"]["en"], "DON 🕹️ VJG — Ikari Warriors")
        self.assertEqual(p["data"]["eastern_day"], day)

    def test_stable_idempotency(self):
        entries = [("DON", "VJG", "Ikari Warriors", "joystick")]
        a = build_payload("2026-11-22", entries)
        b = build_payload("2026-11-22", entries)
        c = build_payload("2026-11-23", entries)
        self.assertEqual(a["idempotency_key"], b["idempotency_key"])
        self.assertNotEqual(a["idempotency_key"], c["idempotency_key"])
        self.assertEqual(uuid.UUID(a["idempotency_key"]).version, 5)

    def test_long_message_bounded(self):
        entries = [("DON", "VJG", "A" * 90, "joystick")] * 30
        p = build_payload("2026-11-22", entries)
        self.assertLessEqual(len(p["contents"]["en"]), 160)


if __name__ == "__main__":
    unittest.main()
