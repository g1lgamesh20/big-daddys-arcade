# Player Pass — Stage 1 verification checklist

**Current state:** schema proposal committed to draft PR only. Do not run on production until Edge Function redemption, operator authorization and end-to-end tests are ready.

## Architecture decisions
- Codes: arcade-themed prefix (PACMAN, GALAGA, FROGGER, DIGDUG) + exactly 4 cryptographically random uppercase alphanumeric characters (A–Z, 0–9); examples are never valid codes.
- 7-day expiry, single use; issue a new code for every additional device. HMAC-SHA256 with server-side pepper; strictly rate-limit redemption by account/device and IP; use low attempt caps, temporary lockouts and operator reissue to mitigate the small 4-character search space.
- Operator code issuance requires a server-verified operator credential. A hidden UI button is not authentication.
- Auth: Supabase anonymous session for each device; redemption binds `auth.uid()` to existing player ID. Anonymous auth sessions are NOT automatically verified Player Passes.
- Redemption must be one transaction: verify digest, player match, unexpired/unused/unrevoked; lock row; link device; mark redeemed; append audit. Repeated redemption fails.
- Revocation must take effect in all privileged APIs even if the Supabase session remains cached.
- Player list sourced from authoritative iScored data; handle matching is case normalized.
- Keep legacy social activity and public score viewing unchanged.

## Tests before enabling any UI
- Unauthenticated request cannot read private tables or redeem.
- Anonymous auth user without redeemed pass cannot act as player.
- Valid code for matching player works once, including on iOS/Android PWA.
- Reusing code, wrong player, expired code, revoked code and guessed code all fail.
- Two simultaneous requests for same code result in exactly one activation.
- Revoking one device does not revoke other devices for same player.
- Player A cannot accept/decline Player B's challenge.
- Non-operator cannot generate/revoke codes by invoking the API directly.
- Rate-limit and abuse responses do not leak whether a code or handle exists.
- No raw code, HMAC pepper, service-role key or secret award trigger appears in frontend bundles/logs.
- Existing public scores, Trash Talk All, OneSignal, and iScored submission remain functional.

## Deployment gate
1. Review schema and Auth settings.
2. Implement and deploy authenticated server-side issuance/redemption/revocation endpoints.
3. Apply reviewed migration.
4. Run database permission and concurrency tests.
5. Add client UI on feature branch; test PWA on real devices.
6. Merge only after user confirms results.
