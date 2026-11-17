#!/usr/bin/env python3
"""Idempotently insert the monthly display script tag into the current index."""
from pathlib import Path
index=Path(__file__).resolve().parents[1]/'index.html'
html=index.read_text(encoding='utf-8')
tag='<script src="monthly-challenge-display.js" defer></script>'
if tag in html:
    print('Monthly display loader already present')
elif '</body></html>' in html:
    html=html.replace('</body></html>',tag+'</body></html>',1)
    index.write_text(html,encoding='utf-8')
    print('Monthly display loader installed; no other index content changed')
else:
    raise SystemExit('Unexpected index structure; not modifying')
