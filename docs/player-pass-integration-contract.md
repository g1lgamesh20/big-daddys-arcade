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

## DON shortcut implementation status
- Added `player-pass-admin-shortcut.js`: one-tap Control Room button appended to the supplied Arcade Control Panel container, visible only after the `arcade_my_player_pass_role` RPC reports DON and is_admin=true.
- Added review-only admin-role migration. No DON role has been assigned in the live database.
- **Critical before rollout:** disable the old robot long-press path as a route to developer tools for non-admin users. Merely hiding the new shortcut does not restrict the legacy route.
- **Critical before rollout:** reconcile the operator Edge Function's `PLAYER_PASS_OPERATOR_USER_ID` check with the server-backed admin role and active device binding; every privileged endpoint must enforce it. The existing operator function is not yet ready for this new role model.
- **Critical before rollout:** mount the shortcut only after Player Pass activation and existing Control Panel integration have been tested. Existing template and Test Lab scripts must not conflict with the new placement.

## First-administrator bootstrap (DON)
The operator issuance endpoint deliberately requires an already-active administrator device. Therefore it **cannot issue DON's very first code**. This is a bootstrap dependency, not an error.

Safe one-time bootstrap sequence:
1. Deploy and validate the private schema and RPCs in a staging environment first; verify all privileges.
2. Independently verify DON's existing iScored identity. Provision DON's `player_pass_players` record from the verified roster (not public user input).
3. Using a trusted server-side operator process, generate a cryptographically random one-use code, compute its HMAC with `PLAYER_PASS_PEPPER`, and insert the digest with a seven-day expiry through the service-only issuance RPC. Do not put raw codes or secrets in SQL migration files, GitHub, or browser source.
4. DON redeems the code on his device. Verify active device mapping in the database.
5. Assign the DON player ID an administrator grant through a trusted, audited service-only operation.
6. Configure `PLAYER_PASS_OPERATOR_USER_ID` to a **non-anonymous Supabase Auth account** bound to DON's active Player Pass. A purely anonymous device session does NOT satisfy the current operator Edge Function's operator login requirement.
7. Confirm the role-check RPC, operator issuance endpoint, and one-tap shortcut all succeed for DON and fail for a second non-admin player.
8. Remove legacy robot access to privileged controls only after the new path is verified; preserve public Test Lab demos.

**Unresolved design decision:** The current player activation creates an anonymous Supabase Auth account, but the operator Edge Function requires a permanent, non-anonymous Auth account. Decide whether DON should use a separate permanent operator sign-in or upgrade DON's Player Pass Auth identity. Do not claim the first-login path is complete until this is resolved.

## Approved administrator authentication decision (2026-11-27)
DON selected GitHub OAuth for administrator authentication. The GitHub OAuth application was created and the Supabase GitHub provider configured by the operator. This does NOT install Player Pass schema or authorize DON yet.

**Identity model:** Regular players redeem codes into anonymous Supabase Auth sessions. DON must use a **GitHub-authenticated Supabase user** as his Player Pass device identity, rather than redeeming DON's pass into an anonymous account and separately signing into GitHub with a second Auth user. Both the role RPC and operator issuance RPC look up the **same** `auth.users.id` in `player_pass_devices`; two separate identities cannot pass both checks.

**Implementation requirement:** For DON, run `signInWithOAuth({ provider: "github" })` first, then redeem his operator-provisioned one-time DON code **using that GitHub session bearer**. The redemption API must verify the caller is the server-approved GitHub operator user before allowing the DON handle. This operator allowlist check MUST be enforced on the server, not inferred from client initials or GitHub username. Provision the initial trusted operator UUID only after verifying GitHub identity. Other players continue anonymous sign-in.

**Fail closed:** The current UI automatically calls `signInAnonymously()` when no session; it must not do that for DON. The operator login module and Player Pass activation UI must share one Auth client/session for DON. Do not enable DON redemption or claim first login works until the frontend integration and backend DON allowlist gate are implemented and tested.

**OAuth provider:** Supabase GitHub provider enabled by operator; redirect allowlist must include the GitHub Pages app URL, and GitHub OAuth App callback must point to Supabase `/auth/v1/callback`. Do not store OAuth secrets in repository.

**Operator shortcut:** Hide by default and show only for the server-confirmed DON admin session; disable legacy robot privileged path once integrated. Every privileged Edge Function must independently verify role and active device. OAuth authentication alone is not authorization.

## Pre-deployment acceptance gates (do not skip)
1. **Identity:** DON signs into GitHub first and redeems DON code under the same Supabase Auth UUID. Verify OAuth `app_metadata.providers` includes `github`; check `PLAYER_PASS_OPERATOR_USER_ID` matches that Auth UUID server-side. No client-controlled initials may grant a role.
2. **Bootstrap:** Issue the first DON code via trusted operator-only provisioning; the regular operator endpoint cannot issue it before the DON role exists. No bootstrap secret, token, or code belongs in Git.
3. **Security:** Review all migration functions and private-schema privileges, verify service-only redemption RPC, audit rate limiting for distributed anonymous users, and check Cloudflare Turnstile site key, secret and hostname.
4. **Frontend:** Mount GitHub login, Player Pass UI, and role-checked Developer Control Room shortcut with a single DON Supabase client/session. Existing hidden robot route must not bypass authorization; ordinary players keep the Test Lab demos.
5. **Tests:** Verify anonymous player redeem, DON GitHub redeem, replayed/expired/wrong-player codes, unauthorized DON claim, revoked admin, unauthorized operator issue, logout and session changes, mobile PWA OAuth return, and preservation of existing scores, push and social functionality.
6. **Rollout:** Do not apply migrations or deploy Edge Functions into the production project until security and staging tests pass. Keep the live arcade public and operational during review.
