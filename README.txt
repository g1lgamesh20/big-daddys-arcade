BIG DADDY’S ARCADE — v2.1 BUTTON LAYOUT ONLY

Upload ONLY these three files to the root of your existing GitHub repository:
- index.html
- style.css
- sw.js

Do NOT overwrite legends.json, medals.json, assets, scripts, tools, or .github.

Changes:
- Moves Enter the Hall of Legends button above Today's Legends.
- Places “TO SUBMIT & VIEW SCORES” inside the same button beneath its title.
- Keeps existing live leaderboard and medal features untouched.
- Bumps service-worker cache to v2.1 for installed app refresh; also corrects a malformed score-data fetch condition in the previous sw.js.

After commit, allow GitHub Pages to deploy, then close/reopen the installed app.
