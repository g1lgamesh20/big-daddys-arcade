BIG DADDY'S ARCADE — v2.3 Medal Sync Foundation

IMPORTANT DISCOVERY
The uploaded repository has TWO score processors:
- tools/update_legends.py (old scoreboard-only version)
- update_legends.py (new medal-aware version)
GitHub Actions was running the OLD tools version and only committing legends.json.
This patch places the tested medal-aware script at the actual workflow path and
updates the workflow to commit legends.json, medals.json and medal-state.json.

INSTALL
Upload only:
  tools/update_legends.py
  tools/test_medals.py
  .github/workflows/update-legends.yml
Preserve their folder paths. Do NOT upload/replace legends.json or your website files.
Commit, then manually run Refresh Hall of Legends scores.

FIRST RUN
If medal-state.json does not yet exist, this run quietly baselines existing scores.
Future newly observed top-3 score IDs are announced after the scheduled sync.
No historical medal flood.

NOT YET INCLUDED
Phone push delivery is NOT enabled by this patch. GitHub Pages alone cannot securely
store subscriptions or send Web Push. That requires a push provider/backend,
subscription storage, credentials kept in secrets, and opt-in permission UI.
This fix makes the medal feed reliable before connecting push delivery.

Original logo and all website styling remain untouched.
