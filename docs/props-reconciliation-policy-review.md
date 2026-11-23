# Stage 3 — Give Props reconciliation edge-case review

PR #76 adds **offline tests only**, using synthetic events. It does not
change reconciliation behavior, Supabase data, OneSignal, or any workflow
that sends notifications.

Current policy observed from `preview_props_reconciliation.reconcile`:

- Multiple changes to the same reaction identity during the previous
  Eastern day count once, using the last event of that day.
- Reactions removed or changed to negative **before midnight** are excluded.
- Reactions removed **after midnight but before the digest** are excluded
  because the current reaction row no longer exists.
- Reactions changed **after midnight** are excluded when their current
  emoji differs from yesterday's final event, even if the previous-day
  reaction was positive. This is a policy decision to confirm before launch.
- Removed-and-readded reactions have new row IDs; the old row's
  previous-day event is not counted if its row no longer exists.
- Unknown giver initials, score/giver mismatches, and unresolved scores
  are excluded.

Open questions before activation:
1. Should a positive reaction valid at yesterday's midnight still count
   if the user changes its emoji after midnight, or should it be excluded
   as current code does?
2. A removed reaction is excluded even if it was positive at midnight.
   Confirm whether that is desirable.
3. Read-history and current-reaction fetches are not an atomic snapshot.
   Changes between those reads and the send can alter eligibility. Exact
   cutoff semantics would require a different snapshot strategy.
4. The current event fetch is ordered by event ID, not explicitly by
   `occurred_at`. The tests assume increasing event IDs reflect event
   order. Consider strengthening ordering/validation before launch.

Do not activate community broadcasts until operator confirms policy.
