# Player Pass live-database isolated preflight — 2026-11-27

This is a **limited real PostgreSQL test**, not Player Pass deployment or authentication activation.

## Environment
Existing Supabase project `jrqzwlowxofnyqpmjgkg`. The isolated `arcade_pass_test` schema was created by approved migrations `prepare_isolated_player_pass_test_schema` and `isolated_player_pass_redemption_probe`. Existing public arcade tables and Edge Functions were not modified.

## Verified results
- `arcade_pass_test.redemption_probe` has RLS enabled and no direct grants to `anon` or `authenticated`.
- `arcade_pass_test.redeem_probe` is a private-schema, security-invoker synthetic test function.
- Transactional synthetic-code test returned: first valid redemption = `true`, replay = `false`, expired code = `false`.
- A separate privilege check returned: anonymous schema USAGE = `false`; authenticated schema USAGE = `false`; anonymous table SELECT = `false`; authenticated probe function EXECUTE = `false`.
- Synthetic test insertions and redemption changes were rolled back. The test schema, empty probe table and function remain installed for repeatable preflight testing.

## NOT tested or enabled
No production Player Pass migrations, real activation codes, player roster, GitHub OAuth login, Turnstile verification, Player Pass Edge Functions, DON administrator grants, or public UI integration have been deployed or validated.

## Next gate
Complete a separate real authentication and Turnstile end-to-end test, then mobile PWA validation and explicit production rollout approval. Never treat this synthetic probe as sufficient to activate the live arcade.
