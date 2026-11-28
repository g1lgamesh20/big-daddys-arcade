# Player Pass browser integration — review-only activation checklist

**Status:** Development-only. Do not import `player-pass-integration.js` into `index.html` or merge PR #96 as an activation shortcut.

## Preconditions

1. Review all `*_REVIEW_ONLY.sql` migrations, SECURITY DEFINER grants, RLS, and RPC role permissions in a disposable database.
2. Verify the DON GitHub Auth UUID and GitHub provider using a fresh authenticated session; confirm operator allowlist server-side.
3. Review and deploy the two Edge Functions only after explicit production authorization, with the server-only HMAC pepper, Turnstile secret, and operator allowlist securely configured.
4. Configure a real Cloudflare Turnstile widget and token callback. Never substitute a static or mock token outside tests.
5. Build the approved iScored handle roster. Codes must be delivered privately and expire in seven days.
6. Test anonymous player enrollment and DON GitHub OAuth separately. The same Supabase Auth client must carry DON's GitHub session into redemption and role verification.
7. Preserve the existing 5-second Space Invader Test Lab and arcade features. The DON-only shortcut is appended at the bottom of the Control Panel.
8. Verify sign-out, admin grant revocation, device revocation, code replay, expired codes, and two-session redemption in a non-production environment.
9. Run the existing score, medal, push, challenge, marquee and Attract Mode regressions before requesting deployment approval.

## Development adapter contract

`mountArcadePlayerPass({ supabase, handles, endpoint, getTurnstileToken, redirectTo })`
expects the existing authenticated Supabase client, approved handles, the Edge Functions URL base, and a real Turnstile token callback. It mounts inside `#arcade-settings-panel > .arcade-settings-body`. Missing prerequisites must fail closed; no fallback credentials or implicit administrator privileges.

## Stop conditions

- No migrations, secrets, OAuth allowlists, or Edge Functions are deployed as part of this checklist.
- No live Player Pass UI is enabled until the operator bootstrap and browser tests are approved.
- Do not expose service-role credentials, HMAC pepper, OAuth secrets, or redemption codes in the repository or browser.
