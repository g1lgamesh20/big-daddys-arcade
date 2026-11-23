import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from send_props_iphone_test import ALLOWED_SUBSCRIPTION, CONFIRMATION, prepare


class LiveTestGuards(unittest.TestCase):
    def test_correct_target_requires_confirmation(self):
        p = prepare(ALLOWED_SUBSCRIPTION, CONFIRMATION, "12345")
        self.assertEqual(p["include_subscription_ids"], [ALLOWED_SUBSCRIPTION])
        self.assertNotIn("included_segments", p)
        self.assertNotIn("filters", p)
        self.assertNotIn("include_aliases", p)

    def test_wrong_target_refused(self):
        with self.assertRaises(ValueError):
            prepare("6aca5b1a-5845-489a-a739-4d979d7f7cb4", CONFIRMATION, "12345")

    def test_missing_confirmation_refused(self):
        for phrase in ("", "yes", "SEND TEST"):
            with self.assertRaises(ValueError):
                prepare(ALLOWED_SUBSCRIPTION, phrase, "12345")

    def test_invalid_run_id_refused(self):
        with self.assertRaises(ValueError):
            prepare(ALLOWED_SUBSCRIPTION, CONFIRMATION, "")

    def test_idempotency_stable_per_run(self):
        a = prepare(ALLOWED_SUBSCRIPTION, CONFIRMATION, "12345")
        b = prepare(ALLOWED_SUBSCRIPTION, CONFIRMATION, "12345")
        c = prepare(ALLOWED_SUBSCRIPTION, CONFIRMATION, "12346")
        self.assertEqual(a["idempotency_key"], b["idempotency_key"])
        self.assertNotEqual(a["idempotency_key"], c["idempotency_key"])


if __name__ == "__main__":
    unittest.main()
