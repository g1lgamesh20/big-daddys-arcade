import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from send_props_digest import authorized, deliver, CONFIRMATION


DAY = "2026-11-22"
PAYLOAD = {"included_segments": ["All"]}


class SenderTests(unittest.TestCase):
    def test_default_disabled(self):
        with self.assertRaisesRegex(RuntimeError, "disabled"):
            authorized("", "", datetime(2026, 11, 23, 15, 0, tzinfo=timezone.utc))

    def test_wrong_confirmation_disabled(self):
        with self.assertRaises(RuntimeError):
            authorized("true", "wrong", datetime(2026, 11, 23, 15, 0, tzinfo=timezone.utc))

    def test_outside_window_disabled(self):
        with self.assertRaisesRegex(RuntimeError, "Outside"):
            authorized("true", CONFIRMATION, datetime(2026, 11, 23, 18, 0, tzinfo=timezone.utc))

    def test_existing_reservation_never_sends(self):
        calls = []
        result = deliver(DAY, PAYLOAD, "k", "a",
                         reserve_fn=lambda *_: False,
                         send_fn=lambda *_: calls.append("send"),
                         record_fn=lambda *_: calls.append("record"))
        self.assertIn("BLOCKED", result)
        self.assertEqual(calls, [])

    def test_success_order(self):
        calls = []
        def reserve(*_):
            calls.append("reserve")
            return True
        def send(*_):
            calls.append("send")
            return "provider-id"
        def record(*args):
            calls.append(("record", args[2], args[3] if len(args) > 3 else None))
            return True
        deliver(DAY, PAYLOAD, "k", "a", reserve, send, record)
        self.assertEqual(calls, ["reserve", "send", ("record", "sent", "provider-id")])

    def test_ambiguous_send_marks_unknown_and_never_retries(self):
        calls = []
        def send(*_):
            calls.append("send")
            raise TimeoutError("timeout")
        def record(*args):
            calls.append(("record", args[2]))
            return True
        with self.assertRaisesRegex(RuntimeError, "NO RETRY"):
            deliver(DAY, PAYLOAD, "k", "a", lambda *_: True, send, record)
        self.assertEqual(calls, ["send", ("record", "unknown")])

    def test_record_failure_after_send_never_retries(self):
        calls = []
        def send(*_):
            calls.append("send")
            return "provider-id"
        def record(*_):
            calls.append("record")
            raise TimeoutError()
        with self.assertRaisesRegex(RuntimeError, "NO RETRY"):
            deliver(DAY, PAYLOAD, "k", "a", lambda *_: True, send, record)
        self.assertEqual(calls, ["send", "record"])


if __name__ == "__main__":
    unittest.main()
