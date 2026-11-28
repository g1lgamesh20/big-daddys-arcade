"""Static regression checks for Player Pass bootstrap and Edge Function boundaries.

These do NOT execute SQL or replace PostgreSQL integration tests.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PlayerPassBootstrapGuards(unittest.TestCase):
    def test_first_code_fails_closed_and_never_creates_roster_entry(self):
        s = (ROOT / "supabase/bootstrap/player-pass-don-first-code_REVIEW_ONLY.sql").read_text()
        self.assertIn("REPLACE_WITH_PRIVATE_64_CHAR_HMAC_DIGEST", s)
        self.assertIn("v_expires_at timestamptz := null", s)
        self.assertIn("v_digest !~ '^[a-f0-9]{64}$'", s)
        self.assertIn("v_expires_at <= now()", s)
        self.assertIn("v_expires_at > now() + interval '7 days'", s)
        self.assertIn("where p.iscored_handle = 'DON'", s)
        self.assertIn("from arcade_private.player_pass_codes", s)
        self.assertIn("from arcade_private.player_pass_devices", s)
        self.assertNotRegex(s.lower(), r"insert\s+into\s+arcade_private\.player_pass_players")

    def test_admin_grant_requires_verified_bound_device(self):
        s = (ROOT / "supabase/bootstrap/player-pass-don-admin-grant_REVIEW_ONLY.sql").read_text()
        self.assertIn("00000000-0000-0000-0000-000000000000", s)
        self.assertIn("u.is_anonymous is false", s)
        self.assertIn("u.raw_app_meta_data->'providers' ? 'github'", s)
        self.assertIn("d.auth_user_id = v_operator", s)
        self.assertIn("d.revoked_at is null", s)
        self.assertIn("where a.player_id = v_player", s)
        self.assertIn("'admin_granted'", s)

    def test_player_ui_does_not_reuse_operator_oauth_session(self):
        s = (ROOT / "player-pass-ui.js").read_text()
        self.assertIn('if (!current.session.user?.is_anonymous)', s)
        self.assertIn('Sign out of the GitHub operator account', s)
        self.assertIn('supabase.auth.signInAnonymously()', s)

    def test_operator_issuer_clears_on_auth_change(self):
        s = (ROOT / "player-pass-integration.js").read_text()
        self.assertIn("supabase.auth.onAuthStateChange?.(", s)
        self.assertIn("operatorHost.replaceChildren()", s)
        self.assertIn("authSubscription?.unsubscribe()", s)
        self.assertIn("if (current === operatorGeneration)", s)

    def test_operator_login_ignores_stale_role_verification(self):
        s = (ROOT / "player-pass-github-operator.js").read_text()
        self.assertIn("const current = ++generation", s)
        self.assertIn("if (current !== generation) return false", s)
        self.assertIn("button.hidden = true", s)

    def test_redemption_accepts_full_turnstile_token(self):
        s = (ROOT / "supabase/functions/player-pass-redeem/index.ts").read_text()
        raw = re.search(r"if \(raw\.length > (\d+)\)", s)
        token = re.search(r"challenge\.length > (\d+)", s)
        self.assertIsNotNone(raw)
        self.assertIsNotNone(token)
        self.assertGreaterEqual(int(raw.group(1)), int(token.group(1)) + 256)
        self.assertIn("result.hostname !== \"g1lgamesh20.github.io\"", s)
        self.assertIn("PLAYER_PASS_OPERATOR_USER_ID", s)


if __name__ == "__main__":
    unittest.main()
