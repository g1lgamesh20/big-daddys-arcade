# BIG DADDY’S ARCADE — v2.0 Medal Club (Stage 1)

## What works
- Preserves the v1.9 layout and original `assets/arcade-logo.png`.
- Existing rotating legends and overall leaders remain.
- The existing scheduled GitHub Actions workflow now also generates `medals.json` and `medal-state.json`.
- A medal activity feed shows newly detected top-three per-game scores only.
- Gold = 1st, Silver = 2nd, Bronze = 3rd. Tied scores share competition rank.
- The **first run silently establishes a baseline** and does not publish historic achievements.
- Read-only public feed: no emails, no user-generated comments, no API credentials.

## IMPORTANT installation
Upload only these files to your GitHub repo, retaining their paths:
- `index.html`, `style.css`, `script.js`, `sw.js`
- `tools/update_legends.py`
- `.github/workflows/update-legends.yml`

**DO NOT upload `legends.json` or replace your logo/assets.** Run the workflow manually once after committing to establish the baseline. It will create `medals.json` and `medal-state.json`. Subsequent workflow runs will record newly observed top-three achievements.

## Limitations / roadmap
- GitHub Actions checks every ~2 hours; alerts are not instant.
- The medal feed is **in-app only**. Phone push notifications, likes and comments are not included yet; those require a secure push backend/database, opt-in and moderation.
- This uses best score per player per game and competition ranking for ties. Confirm these rules against iScored if necessary.
- A newly approved score that has fallen outside the top 3 before the next sync won't alert.
- No historical medals are backfilled by design.
- Score-ID tracking is persisted in `medal-state.json`; do not delete it after the first sync.
- Check that the GitHub workflow has permission to commit generated files.
