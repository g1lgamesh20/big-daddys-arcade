# Big Daddy's Arcade — Hall of Legends v1.3

## Changes
- Original `assets/arcade-logo.png` preserved byte-for-byte.
- Flickering green/pink CSS neon frame added around the logo.
- Subtle retro grid background and neon ENTER button.
- TODAY'S LEGENDS section is a placeholder, **not fabricated live rankings**.
- OVERALL PLAYER RANKINGS button links to the existing iScored public page. iScored exposes rankings as a column, not a confirmed deep-link target.
- Cache version bumped so installed PWAs can update.

## Publish to GitHub Pages
Upload **all contents** of this folder into the root of `g1lgamesh20/big-daddys-arcade`, replacing existing files, and commit. Do not upload the outer folder as a nested directory. Open https://g1lgamesh20.github.io/big-daddys-arcade/ and refresh after Pages deploys. On iPhone, close/reopen the Home Screen app; if stale, reload in Safari or clear website data.

## Important
The actual score form, photo requirement, uppercase validation, and approval are controlled by iScored. The PWA does not collect scores. Live daily rankings need an authorized data source and a defined meaning of 'today'.


## Version 1.4 — animated neon tracers
- The original `assets/arcade-logo.png` is copied byte-for-byte from v1.3 and has not been edited.
- SVG border tracers travel around the logo while the surrounding tubes gently pulse.
- The ENTER button has an animated perimeter highlight.
- `prefers-reduced-motion` disables moving effects.
- iScored submission and rankings links are unchanged.
- To update GitHub Pages, upload the *contents* of this folder into the repository root (including `index.html`, `style.css`, and `sw.js`), then commit.
- On iPhone, the service worker may retain the previous app briefly; close/reopen or reload the site in Safari.
