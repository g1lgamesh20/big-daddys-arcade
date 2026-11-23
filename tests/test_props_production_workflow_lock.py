import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/props-production-broadcast.yml"


class LockTests(unittest.TestCase):
    def test_lock_is_explicit(self):
        content = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("vars.PROPS_DIGEST_BROADCAST_ENABLED == 'true'", content)
        self.assertIn("needs: activation-status", content)
        self.assertIn("environment: props-digest-production", content)

    def test_no_activation_variable_created_by_workflow(self):
        content = WORKFLOW.read_text(encoding="utf-8")
        self.assertNotIn("gh variable set", content)
        self.assertNotIn("actions/github-script", content)

    def test_sender_still_has_internal_lock(self):
        content = (ROOT / "tools/send_props_digest.py").read_text(encoding="utf-8")
        self.assertIn("ENABLE_PROPS_COMMUNITY_SEND", content)
        self.assertIn("PROPS_SEND_CONFIRMATION", content)
        self.assertIn("eligible_time(now)", content)

    def test_no_manual_input_bypasses_lock(self):
        content = WORKFLOW.read_text(encoding="utf-8")
        self.assertNotIn("inputs.", content)
        self.assertNotIn("github.event.inputs", content)


if __name__ == "__main__":
    unittest.main()
