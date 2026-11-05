BIG DADDY’S ARCADE — CONSOLIDATED MEDAL CLUB RELEASE

This is a CLEAN CONSOLIDATED CODE PACKAGE based on the repository ZIP you uploaded.
It preserves the original logo, HTML/CSS/JS interface and service worker.
The medal-aware score processor is now at tools/update_legends.py and the
single workflow is at .github/workflows/update-legends.yml.

IMPORTANT — DATA PRESERVATION
The ZIP intentionally DOES NOT contain legends.json, medals.json, or
medal-state.json. These are generated data files. Keep them on GitHub!
Do not delete your repository or delete any of those files.

INSTALL — RECOMMENDED METHOD
1. Make a backup of your current GitHub repository (Code > Download ZIP).
2. In the repository root, use Add file > Upload files.
3. Upload the ordinary root files and assets from this ZIP.
4. IMPORTANT: GitHub's web uploader may skip hidden .github folders.
   Open the existing .github/workflows/update-legends.yml file in GitHub,
   click Edit, and replace its entire contents with the YAML from this ZIP.
5. Open the existing tools/update_legends.py file in GitHub, click Edit,
   replace its entire contents with the file in this ZIP.
6. Do the same for tools/test_medals.py, or create it inside tools.
7. Verify paths are EXACTLY .github/workflows/update-legends.yml,
   tools/update_legends.py and tools/test_medals.py (no duplicate folders).
8. Commit changes to main, then run Refresh Hall of Legends scores.
9. Check that legends.json, medals.json and medal-state.json exist.

If using Git locally instead of the web uploader, copying the ZIP contents
into your checked-out repo preserves hidden folders automatically.

No phone push notifications are included yet. This is the reliable medal
sync foundation needed before adding a secure push provider.
