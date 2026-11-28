"""Static security regression checks for REVIEW_ONLY Player Pass SQL.

Run: python3 -m unittest discover -s tests -p 'test_player_pass_sql_guards.py'
These checks do NOT replace PostgreSQL integration tests.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
MIG = ROOT / "supabase" / "migrations"


def sql(name):
    return (MIG / name).read_text(encoding="utf-8")


class PlayerPassSqlGuards(unittest.TestCase):
    def test_handle_limit_is_account_independent(self):
        s = sql("20261127_player_pass_limited_redeem_REVIEW_ONLY.sql")
        self.assertIn("('user','ip','handle')", s)
        self.assertIn("v_handle_hash := md5(upper(trim(p_iscored_handle)))", s)
        self.assertIn("pass-handle:", s)
        self.assertIn("values('handle',v_handle_hash,v_window,1)", s)
        self.assertIn("returning attempts into v_handle_attempts", s)
        self.assertRegex(s, r"if v_user_attempts > 5 or v_ip_attempts > 20 or v_handle_attempts > 10 then return; end if;")

    def test_code_redemption_is_atomic_and_one_use(self):
        s = sql("20261127_player_pass_limited_redeem_REVIEW_ONLY.sql")
        self.assertIn("for update", s.lower())
        self.assertIn("v_code.redeemed_at is not null", s)
        self.assertIn("v_code.revoked_at is not null", s)
        self.assertIn("v_code.expires_at <= now()", s)
        self.assertIn("set redeemed_at=now(),redeemed_by=p_auth_user_id", s)

    def test_redeem_rpc_is_service_only(self):
        s = sql("20261127_player_pass_limited_redeem_REVIEW_ONLY.sql")
        self.assertIn("revoke all on function public.arcade_redeem_player_pass_limited(uuid,text,text,text) from public,anon,authenticated", s)
        self.assertIn("grant execute on function public.arcade_redeem_player_pass_limited(uuid,text,text,text) to service_role", s)

    def test_issue_rpc_rechecks_admin_role(self):
        s = sql("20261127_player_pass_issue_REVIEW_ONLY.sql")
        self.assertIn("public.arcade_operator_is_active_admin(p_operator_id)", s)
        self.assertIn("grant execute on function public.arcade_issue_player_pass(text,text,timestamptz,uuid)", s)
        self.assertIn("to service_role", s)

    def test_admin_role_requires_active_device_and_github(self):
        s = sql("20261127_player_pass_admin_role_REVIEW_ONLY.sql")
        self.assertIn("d.revoked_at is null", s)
        self.assertIn("a.revoked_at is null", s)
        self.assertIn("u.is_anonymous is false", s)
        self.assertIn("u.raw_app_meta_data->'providers' ? 'github'", s)


if __name__ == "__main__":
    unittest.main()
