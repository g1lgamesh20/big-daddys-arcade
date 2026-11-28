# Player Pass — minimal activation gate (review only)

Status: **NOT DEPLOYED**. This document is a go/no-go checklist, not an instruction to deploy to the live arcade.

## Already demonstrated in disposable GitHub Actions
- PostgreSQL schema/RPC tests: permissions, one-use codes, expiry, wrong handles, anonymous DON denial, revocation, concurrency, and rate-limit paths.
- Mocked Edge Function tests: authentication, DON allowlist, Turnstile hostname/rejection, fail-closed DB handling, and operator issuance authorization.
- Browser DOM tests: adapter rollback and server-verified administrator shortcut.
- Existing arcade marquee and Attract Mode checks.

These tests do **not** prove real Supabase Auth, Cloudflare Turnstile, iScored roster provisioning, or PWA OAuth redirects work.

## Minimum remaining steps, in order
1. **Operator-approved non-production environment:** obtain a separate disposable Supabase test project and Turnstile test widget, or explicit authorization to test in the existing project. Do not create billable resources or modify the existing production project without approval.
2. **Real provider configuration:** use non-production Auth settings, GitHub OAuth callback/redirect allowlist, anonymous sign-in, Turnstile site key/secret, and secure Edge Function environment variables. Never commit any secret.
3. **Bootstrap test:** provision a verified test roster; confirm the DON GitHub Auth UUID; issue DON's first code from a trusted server-side bootstrap; redeem under that same GitHub session; grant administrator access only after device binding.
4. **Real request path:** validate successful ordinary-player activation, wrong-player denial, code replay, expiry, Turnstile failure, operator issuance, revoked-device denial, and sign-out.
5. **Frontend wiring:** provide a real Turnstile token callback, ensure DON code issuance UI is mounted only after server role verification, and disable the legacy robot route to privileged tools while retaining Test Lab demos. The current adapter is NOT imported by index.html and is not yet a complete production rollout.
6. **Device verification:** test PWA OAuth return and session persistence on iPhone and Android; check scores, OneSignal push, medals, challenges and arcade visuals remain unaffected.
7. **Production approval:** separately authorize the reviewed migrations, secrets, Edge Functions, roster import and UI enablement. Deploy in a coordinated change with rollback instructions; never merge PR #96 as an activation shortcut.

## Go/no-go rule
**No-go** until steps 1–6 are evidenced and the operator explicitly approves step 7. Passing mock CI alone is insufficient. Keep the public arcade usable without Player Pass throughout.
