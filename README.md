# BIG DADDY'S ARCADE: HALL OF LEGENDS — PWA v1

A static, installable welcome screen for your existing iScored page.

## Try it locally

Run `python3 -m http.server 8000` from this folder and open `http://localhost:8000` on your computer. To install on phones, deploy this directory to an HTTPS host (GitHub Pages, Netlify, etc.). A local file:// URL is not sufficient for PWA installation.

## What it does

- Uses your approved neon logo and green/pink arcade styling.
- Links to `https://www.iScored.info/?mode=public&user=G1LGAMESH` in the device browser (better compatibility for photo upload than an iframe).
- Provides a return-to-start button for shared tablet use.
- Supports installable home-screen icons and offline access to the *welcome screen only*.

## Important limitations

- iScored requires internet access; this PWA does not store or submit scores itself.
- Photo requirements and admin approval are enforced by your iScored settings, not this app.
- Uppercase player names are a visible instruction only; we cannot force capitalization in the separately hosted iScored form. Ask iScored whether they offer uppercase validation if strict enforcement is required.
- External links may open in a new tab or browser depending on platform. For a shared tablet, users should return to the home-screen app after submitting.
- PWA installation: iPhone Safari Share > Add to Home Screen; Android Chrome menu > Install app/Add to Home screen.

## Next steps

Deploy to HTTPS, test the iScored photo upload on iPhone and Android, and optionally configure tablet kiosk mode. No app-store account is needed for the PWA.
