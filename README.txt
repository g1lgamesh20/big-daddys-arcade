BIG DADDY'S ARCADE — AUTOMATIC STARTUP SOUND

Replace index.html and script.js in GitHub repository root.

Changes:
- Attempts the original 8-bit startup jingle automatically when the page loads.
- Audio defaults ON for new visitors. Existing stored mute preference remains respected.
- Arcade Control Panel now uses a checked ENABLE ARCADE AUDIO checkbox. Unchecking mutes all supported sound effects.
- Secret Space Invader Test Lab includes PLAY STARTUP SOUND button.
- Existing secret 5-second hold, previews, Thursday features, sharing, scores and other sounds retained.

Browser caveat: iOS Safari and some Android/desktop configurations block audio without a user gesture. No unexpected delayed autoplay is attempted. Preview button works after a tap.

No workflow changes required. Test on actual devices.
