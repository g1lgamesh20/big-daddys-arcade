# Secure Player Pass — Stage 1 implementation contract

Status: DEVELOPMENT BRANCH ONLY — no production authentication changes yet.

## Approved player experience
- Existing iScored initials are the public display identity.
- No player email, password, or recurring login.
- Operator privately issues a cryptographically random, single-use, short-lived device activation code from the double-hidden Developer Control Room.
- Player selects their iScored handle, enters code once, and stays signed in on that device.
- Additional/replacement device: "Ask Big Daddy for a New Code". Operator can revoke old devices.
- Viewing scores and existing social features must remain available without registration.

## Security boundary
- Never accept a selected initials string as proof of identity.
- Each device must have a real Supabase Auth session (anonymous Auth user may be suitable), then redeem a code server-side to bind auth.uid() to an operator-approved player ID.
- An anonymous Supabase Auth user is *authenticated* in Postgres, but not yet a claimed arcade player. Every privileged RLS policy must require an active player-device binding.
- Store only a strong salted/keyed hash of each code; never put raw codes, service_role secrets, or privileged operator tokens in public HTML/JS.
- Code redemption must be atomic and one-use; enforce expiration, rate limits, revocation, and player-handle match.
- Multiple device auth user IDs may map to one player; separate player ID from device session ID.
- Operator privileges must be validated server-side, not by the visibility of the hidden menu.
- Public and private trophies must have separate authorization rules; never expose unrevealed secret awards through public JS or APIs.
- Duels: only challenger may issue/cancel their own challenge and only challenged player may accept/decline; admin overrides are auditable.
- Existing unverified social records must not be silently reattributed as verified ownership.

## Recommended implementation sequence
1. Inspect current Supabase Auth settings, database grants/RLS and existing app initialization; check current Supabase docs and changelog.
2. Add minimal private player/device/code tables, RLS and a carefully scoped server-side redemption endpoint. Test code replay, expiry, wrong player, wrong device, revoked device, and public access denial.
3. Add operator code-issue/revoke actions to Developer Control Room; ensure operator authorization.
4. Add one-time Player Pass activation UI and persistent session handling; keep the rest of the site usable.
5. Test iPhone, Android, same-player multi-device, lost-device recovery, and existing score/social regression.
6. Only after identity verification, implement Duel issuance/acceptance and targeted push subscription linking.

## Duel rules already approved
- Thursday callouts allowed. Explicit decline may earn Chicken; Thursday silence alone never earns automatic Chicken.
- Properly noticed unanswered Monday–Wednesday callouts may earn Chicken; sent push alone does not prove notice.
- Ghost: accepted, then no qualifying submission. Valiant Warrior shield: verified loser. Gladiator swords: winner.
- Operator can reverse unfair penalties.
- Friday submissions strictly before 9 AM Eastern; operator approval target 8:59 AM; announce verified results at 9 AM, hold unresolved pending approvals. No Saturday grace period.

## Open design items before Duel penalty automation
- Fair-notice evidence and reasonable response window; Thursday play start; ties; score-direction edge cases.
