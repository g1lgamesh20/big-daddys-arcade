# BIG DADDY’S ARCADE — HALL OF LEGENDS v1.6

Retains the v1.5 logo image byte-for-byte, neon tracer, buttons, grid and starfield. Adds a rotating **TODAY’S LEGENDS** panel.

## Important: score connection status

The scoreboard **does not yet fetch live iScored data**. The public iScored API endpoint, authorization and browser CORS permissions have not been verified. This release safely reads `legends.json` hosted on GitHub Pages. Empty entries show an honest placeholder, never fabricated scores.

To populate the panel, use verified, approved scores exported from iScored and edit `legends.json` as follows:

```json
{
  "updated_at": "2026-11-04T12:00:00Z",
  "source": "iScored approved scores",
  "entries": [
    {"player": "AAA", "game": "EXAMPLE GAME", "score": "123,450"}
  ]
}
```

The above record is **illustrative only**; do not publish it as a real score. Names are displayed in uppercase without modifying iScored records. Scores rotate every 8 seconds; previous/next controls are included. To automate, use a trusted server-side process or GitHub Actions with a documented read-only iScored endpoint and secret stored in GitHub Actions secrets; never embed API tokens in client files.

## Deploy

Upload the contents of this folder to the repository root, replacing existing files and adding `legends.json`. Keep the `assets` folder structure. GitHub Pages URL: https://g1lgamesh20.github.io/big-daddys-arcade/

## Existing iScored behavior

All score submissions, photo proof, and admin approvals continue on iScored. The Overall Player Rankings button still opens the public leaderboard, not a separate rankings URL.
