# Player Pass integration contract — development only

## Deployment status
No migrations, functions, or UI are deployed. The current Player Pass module is deliberately NOT imported into the live index.html.

## Required server configuration
- Supabase Anonymous Sign-Ins enabled only after reviewing existing RLS.
- `PLAYER_PASS_PEPPER`: independently generated, high-entropy server secret, at least 32 characters.
- `TURNSTILE_SECRET_KEY`: existing Cloudflare server secret (must match the widget site key).
- `PLAYER_PASS_OPERATOR_USER_ID`: UUID of the operator's **non-anonymous**, server-verified Supabase Auth account.
- Standard Supabase environment variables: `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`.
- Never put pepper, service-role key, or Turnstile secret in GitHub Pages assets.

## Frontend integration
`player-pass-ui.js` exports `mountPlayerPass({ host, supabase, handles, endpoint, operatorHost, operatorEnabled, operatorSupabase, getTurnstileToken })`.

- `host`: player activation mount node.
- `supabase`: browser Supabase client for player device anonymous Auth, with persistent session.
- `handles`: current verified iScored initials, not a hand-entered guess.
- `endpoint`: `https://<project-ref>.supabase.co/functions/v1`.
- `getTurnstileToken`: async callback obtaining a fresh Cloudflare Turnstile response token for every activation attempt. The callback must render/reset a real widget; never use a hard-coded token.
- `operatorHost`: element **inside the double-hidden robot Developer Control Room**.
- `operatorEnabled`: display-only flag; must be set only after operator verification.
- `operatorSupabase`: distinct authenticated operator client. Do not call `signInAnonymously` on the operator session.
- Both functions require valid Supabase JWTs and independent backend authorization.

## IMPORTANT unresolved integration work
1. Operator Auth enrollment/login flow (the hidden menu alone is not authorization).
2. Verified iScored handle provisioning; ensure no untrusted handle can be assigned.
3. Review private-schema grants, exposed RPCs, and PostgREST permissions.
4. Review current frontend Supabase client and Turnstile widget lifecycle.
5. Implement operator revoke/reissue, device status and player session restore UI.
6. Add server-side account-creation abuse protection and deployment verification.
7. Test on iPhone and Android; do not merge until operator signs off.

## Short-code safety
The 4-character suffix uses a 32-symbol unambiguous alphabet: 32^4 = 1,048,576 suffixes per prefix. A prefix is public, not a secret. A valid Turnstile challenge and DB-backed attempt limits (5 per auth user/hour; 20 per IP/hour) are mandatory, but **not sufficient proof against distributed attacks**. Before production, consider per-code or global attempt monitoring and rate limits across IPs and anonymous accounts.

## Validation
- Run syntax/lint checks on Edge Functions and UI before deployment.
- Test replay, expiry, wrong player, parallel redemption, IP/account rate limits, and captcha bypass.
- Test that an unverified user cannot call operator issuance even by bypassing the UI.
- Confirm all previous public features remain usable without Player Pass.

## Approved operator UX: DON admin (Nov 27)
- DON is the designated administrator. The Player Pass identity must be verified and bound to an active, non-revoked device before operator privileges are recognized.
- Add a one-tap 🤖 Developer Control Room entry at the **bottom of the Arcade Control Panel**, visible only for an authenticated DON account with a server-confirmed admin role.
- Keep the Developer Control Room contents in their existing location; replace the second five-second robot hold for DON with direct tap access after authentication is enabled.
- Hide the control for all other players. Hiding a control is not authorization: every operator API must independently verify the authenticated identity, active device binding, and admin role.
- Preserve the Space Invader five-second Test Lab shortcut and fun demos. Do not expose developer tools through it to other players.
- Do not activate this behavior before the role model and authentication are deployed and tested. The existing hidden robot path remains unchanged on the live site in the meantime.
- Avoid using a hardcoded string comparison with initials DON as sole proof of administrator identity; use a server-assigned role tied to verified player ID.
