BIG DADDY'S ARCADE — FRIDAY 9 AM THURSDAY CHAMPION PUSH

Upload these TWO files to your GitHub repository:
1) tools/send_friday_champion_notification.py (new file)
2) .github/workflows/thursday-challenge.yml (REPLACE existing workflow)

Do not replace index.html, script.js, or existing medal notification files.
Do not remove your existing ONESIGNAL_REST_API_KEY GitHub Actions secret.

The existing Thursday workflow continues updating challenge data and sending the
Thursday 9 AM game announcement. The Friday addition checks at 9 AM New York time
(13:00 or 14:00 UTC, accounting for DST), and sends one champion notification
only when Thursday's challenge feed is FINAL and contains a winner.

Manual workflow runs outside Friday 9 AM Eastern will NOT send a winner push.
The Friday send deduplication state is committed as
friday-champion-notification-state.json after OneSignal confirms acceptance.
GitHub scheduled workflows can run late or fail, so delivery at exactly 9 AM
is not guaranteed. If the run occurs outside the 9 AM hour, it skips the send.

IMPORTANT: The current iScored timestamp semantics have not been verified.
The Friday announcement reflects APPROVED scores available by the workflow run.
Late approvals may change the true Thursday winner after the announcement.
Consider delaying the official announcement until submissions are approved, or
implementing a provisional result policy, if Friday 9 AM approvals are incomplete.

Testing: Actions > Thursday Challenge Announcement > Run workflow. This tests
workflow success but will NOT send a Friday push outside the Friday 9 AM hour.
