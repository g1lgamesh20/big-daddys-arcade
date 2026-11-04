# BIG DADDY’S ARCADE — Hall of Legends v1.7

This version preserves the original logo (`assets/arcade-logo.png`) and the v1.6 space/neon design.

## Enable automatic scores

1. In iScored enable **Allow Read Access through the iScored API** only. Leave write access and public edit/delete OFF.
2. Upload **all contents** of this ZIP to the root of your existing GitHub repository, including the hidden `.github` folder and `tools` folder. GitHub's web upload supports dragging the unzipped folder contents; verify `.github/workflows/update-legends.yml` exists afterward.
3. In GitHub open **Actions → Refresh Hall of Legends scores → Run workflow**. Wait for success. It will write `legends.json` with sanitized scores. Scheduled runs occur approximately every two hours (GitHub may delay scheduled jobs).
4. Refresh the GitHub Pages app. The PWA checks the published feed every 10 minutes while open; the published data updates when GitHub Actions runs and Pages deploys.

The app does NOT expose email fields, API credentials, raw records, or IDs in the published JSON. Only public player names, game titles, scores, dates, and estimated PAPA standings are published. The API itself may expose additional fields to anyone with read access; consult iScored privacy settings.

## PAPA scoring

Per game, each player's highest score is ranked, then 1st=100, 2nd=90, 3rd=85, each later rank one point less (floored at zero); sum the player's best 1000 game placements. Competition ranking is used for ties (e.g. 1,1,3). **This is a local estimate, not a guarantee of an exact match with iScored's own overall rankings**: their tie handling, scoring options, and hidden/invalid score policies may differ. Use the iScored site as official source.

The UI shows up to 120 alphabetical game champions and 12 latest scores. Game champions are based on the best recorded score for each player/game. Scores are pulled by GitHub Actions (server-side) because direct browser requests may fail due to CORS. The initial `legends.json` is intentionally empty until the first successful sync. No demo scores are fabricated.


## v1.8 changes
- Removed redundant Overall Player Rankings external button and explanatory text.
- Renamed Overall PAPA Leaders to Overall Leaders.
- Tap the leaderboard heading to view all available standings in an accessible, scrollable dialog.
- Added Best Game (PAPA) scoring explanation and estimate disclaimer.
- Original arcade logo binary unchanged.
