import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from preview_props_iphone_test import build_test_payload, validate_test_payload


class TestIphonePayload(unittest.TestCase):
    def test_single_target_and_no_broadcast(self):
        p = build_test_payload("6aca5b1a-5845-489a-a739-4d979d7f7cb4")
        validate_test_payload(p)
        self.assertEqual(len(p["include_subscription_ids"]), 1)
        self.assertNotIn("included_segments", p)
        self.assertNotIn("filters", p)
        self.assertNotIn("include_aliases", p)

    def test_invalid_target_rejected(self):
        for value in ("", "All", "test", "not-a-uuid"):
            with self.assertRaises(ValueError):
                build_test_payload(value)

    def test_idempotency_stable(self):
        sid = "6aca5b1a-5845-489a-a739-4d979d7f7cb4"
        self.assertEqual(build_test_payload(sid)["idempotency_key"],
                         build_test_payload(sid)["idempotency_key"])


if __name__ == "__main__":
    unittest.main()
