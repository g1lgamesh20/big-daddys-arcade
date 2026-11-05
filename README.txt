BIG DADDY'S ARCADE — v2.2 Medal Club Reliability Patch

WHAT CHANGED
- Keeps the full history of previously observed iScored score IDs, even if a score temporarily disappears from an API response. This prevents re-announcing a restored score as a new medal.
- Retains the existing quiet first-run baseline, Gold/Silver/Bronze detection, and last 100 medal announcements.
- Includes an offline regression test for first-run baseline, Bronze achievement, repeat sync, non-medal scores, and temporary API omissions.

INSTALL
1. Back up your existing tools/update_legends.py from GitHub.
2. Upload ONLY tools/update_legends.py from this ZIP to the same location in your GitHub repository. Do not create an extra nested tools folder.
3. Commit to main.
4. In Actions, run the existing Refresh Hall of Legends scores workflow once. Confirm the green checkmark.
5. Do NOT replace index.html, style.css, script.js, sw.js, legends.json, medals.json, medal-state.json, or .github/workflows/update-legends.yml.

OPTIONAL TEST
Run: python tools/test_medals.py (requires test_medals.py beside update_legends.py). This test uses simulated data, not your live iScored feed.

IMPORTANT
This is a detection reliability update, not phone push notifications. Alerts appear in the app after GitHub Actions refreshes scores, currently scheduled every two hours. The system only detects new medal winners visible at sync time; a podium result displaced before the next sync may not be captured. It does not modify existing medal history.
