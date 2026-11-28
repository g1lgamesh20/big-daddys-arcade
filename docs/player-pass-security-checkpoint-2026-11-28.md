# Player Pass — predeployment security checkpoint (2026-11-28)

Status: **REVIEW ONLY**. No production deployment, admin grant, code issuance, or public UI wiring authorized by this document.

## Read-only checks completed

- Supabase Auth contains one GitHub identity reporting username `g1lgamesh20` (operator-confirmed account).
- The hosted database has no `arcade_private` Player Pass tables and no `arcade_*player_pass*` functions. This is expected while the migration files remain review-only.
- Supabase security advisor flags `public.rls_auto_enable()` as executable by `anon` and `authenticated`. Inspection shows it RETURNS `event_trigger`, is attached to enabled `ensure_rls` on `ddl_command_end`, and automatically enables RLS on newly created public tables. It cannot be treated as an ordinary callable RPC without additional evidence. **Do not modify this existing trigger during Player Pass rollout without separate review.**
- RLS-without-policy notices on existing server-only tables are not by themselves evidence of exposure. Review schema USAGE, table grants, and SECURITY DEFINER function grants separately.
- Supabase changelog reviewed on 2026-11-28. CLI v3 targets local by default; never assume a command changes hosted production. New public tables are not automatically Data API exposed; explicit grants are required.

## Remaining hard gates (not yet satisfied)

1. Run all four review-only migrations against an isolated PostgreSQL environment and confirm `tests/player_pass_postgres_smoke.sql` passes; do not treat static tests as equivalent to hosted verification.
2. Verify service-role-only EXECUTE grants on `arcade_redeem_player_pass_limited`, `arcade_issue_player_pass`, and `arcade_operator_is_active_admin`. Confirm `anon` and `authenticated` cannot access the private schema or privileged RPCs.
3. Review the Edge Function's JWT verification, exact DON Supabase Auth UUID allowlist, GitHub provider check, Turnstile siteverify, HMAC pepper, CORS, and rate-limit behavior. No secrets or Auth UUIDs in public source.
4. Confirm the iScored roster's DON handle is operator-verified before importing; the first-code bootstrap must refuse a missing roster entry.
5. Independently verify a successful DON redemption and active, nonrevoked device before the separate privileged admin grant.
6. Verify operator login, redemption, logout, revocation, replay, expiration, and role refresh end-to-end in a nonproduction client.
7. Obtain explicit operator authorization before applying any review-only migration or Edge Function to the hosted project. GitHub PR merge and production UI wiring require separate approval.

## Release invariants

Keep the GitHub Pages main branch and current iScored, OneSignal, Medal Club, Trash Talk, Arcade News, and hidden Test Lab behavior unchanged until approved. Never store plaintext activation codes or pepper in the repo, logs, or chat.
