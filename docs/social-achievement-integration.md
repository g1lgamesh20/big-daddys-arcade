# Social achievements — safe implementation boundary

## Status
The milestone rules and Hall of Achievements **COMING SOON** catalog are in this
pull request. **No live social trophies are granted**, no existing awards are
modified, and no score/medal/push logic is changed.

## Rules
- Separate tracks: Trash Talk and Give Props.
- For each track, at most **one credited day per verified player per
  America/New_York calendar day**. A hundred clicks or comments in one day = 1.
- Milestones stack permanently at **1, 5, 10, 25, 50 and 100** distinct days;
  higher milestones never replace lower ones.
- Trash Talk includes score-specific and arcade-wide comments. Deleting/invalid
  posts is not evidence; authoritative backend determines whether events remain active.
- Give Props counts only positive reactions (heart, invader, joystick, gamepad,
  quarter, trophy), never dislike/angry. No self-reactions. Switching reactions,
  retries and duplicates do not create additional credits.
- No new PAPA ranking points or per-award push notifications.

## What the existing app actually does
The browser sends initials, a device token, and Turnstile verification to
Supabase Edge Functions. Those mechanisms protect posting but **do not
authenticate a player identity**. No Edge Function source or authenticated
social event export is stored in this GitHub repo.

## Trusted integration required before enabling awards
1. **Registration codes and sign-in are on hold.** Continue to use the existing
   three-character arcade initials for social interactions. Browser-supplied
   initials are not verified player identity, so do not present their activity
   as verified official awards.
2. In Supabase server-side code, keep immutable event IDs, authenticated actor,
   score owner / target, created_at with timezone, event type, server-side active
   status, and any deletion/reaction replacement history.
3. Generate an **operator-authenticated or service-authenticated audit** from
   that backend. Only the trusted server may set `identity_verified` and
   `trusted_source=authenticated_social_audit`. Never accept these flags from
   player-submitted JSON or an anonymous endpoint.
4. Integrate `tools/social_achievement_rules.py:awards_due` into a protected
   job with reviewable, idempotent award-ledger writes and audit/revocation
   policy. Do **not** plug it into the current public score refresh Action.
5. Run end-to-end tests on iOS/Android and Supabase for identity spoofing,
   duplicate requests, self-props, deleting comments, toggled reactions, ET
   midnight/DST, pending verification, and trophy correction before enabling.
6. Historical posts should be credited **only if** actor identity and the
   individual event can be verified from retained trustworthy records. Never
   fabricate historical credit.

## Example input for **unit testing only**
```json
{
  "event_id": "server-event-id",
  "event_kind": "give_props",
  "actor_player": "DON",
  "target_player": "RDG",
  "reaction": "quarter",
  "created_at": "2026-11-19T16:01:00Z",
  "identity_verified": true,
  "active": true,
  "trusted_source": "authenticated_social_audit"
}
```
This JSON shape alone does **not** confer trust and is not a public award API.

## Current small-group decision — initials only

**No registration codes, account creation, device-linking setup, player PINs or
recurring sign-in.** Keep the arcade accessible to its small group of regulars
using the same 1–3 character iScored initials already used for Trash Talk and
Give Props. Do not change the existing social write endpoints or UI.

The social milestone catalogue and pure, fail-closed test engine are staged
for later use, but the trophies remain **COMING SOON**. Current social initials
can be imitated, so browser events cannot become permanent VERIFIED trophies
or influence Trophy Hunters without a separate approved trust model.
We are **not** imposing registration as a prerequisite on players now.

If revisited in the future, first discuss a low-friction approach with the
operator; do not automatically implement one-time codes. Continue to observe
one credited Trash Talk day and one credited positive Give Props day maximum
per player per America/New_York calendar day when eligible awarding is safely
introduced. Historical entries must not be treated as verified on initials alone.
