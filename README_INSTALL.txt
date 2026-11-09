BIG DADDY'S ARCADE — THURSDAY NIGHT CHAMPION + 9 AM PUSH

INSTALL (GitHub repository root):
1. Replace index.html and script.js.
2. Upload BOTH supplied Python files into tools/.
3. Upload .github/workflows/thursday-challenge.yml into the same path.
4. Commit everything to main.
5. In GitHub Actions, run "Thursday Challenge Announcement" manually once to generate
   thursday-challenge.json and thursday-challenge-state.json. Manual runs outside
   Thursday 9 AM ET DO NOT send a notification.
6. Ensure existing ONESIGNAL_REST_API_KEY secret remains set.
7. Check that the challenge card loads; verify real iScored date formats before
   relying on Thursday winners. Date strings without offsets are assumed Eastern.
8. The workflow aims for Thursday 9 AM Eastern and accounts for daylight saving time.
   GitHub Actions schedules may run late.

RULES:
- Highest approved score SUBMITTED on Thursday 00:00–23:59:59 ET wins.
- A score approved later counts if iScored date reflects Thursday submission;
  confirm actual API timestamp semantics before treating as official.
- Ties: earliest submission timestamp wins, then alphabetical player name.
- This is separate from the all-time high score.
- Winner finalizes after Thursday ends and next successful sync.
- Existing scoreboard and medal workflow remains unchanged.
- OneSignal sends to segment All, at most once per Thursday in normal operation.

LIMITATIONS:
- Selection freezes when challenge workflow first runs that week.
- iScored date format and timestamp meaning have NOT been verified against live API.
- If selected game's dates are unparseable, winner is held for review.
- A GitHub scheduled workflow may be delayed or missed.
- If notification succeeds but state commit fails, a later retry may duplicate it.
