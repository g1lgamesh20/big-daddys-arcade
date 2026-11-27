#!/usr/bin/env python3
"""Prepare a one-time DON Player Pass code locally. REVIEW ONLY; no database writes.

Requires PLAYER_PASS_PEPPER in environment (at least 32 characters).
The secret and plaintext code are never written to files or sent to GitHub.
The printed digest must be inserted by a trusted operator into the private
database only AFTER migrations and backend security review.
"""
import hashlib
import hmac
import os
import secrets
import sys
from datetime import datetime, timedelta, timezone

ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

def generate(pepper: str):
    if len(pepper.encode("utf-8")) < 32:
        raise ValueError("PLAYER_PASS_PEPPER must be at least 32 UTF-8 bytes")
    code = "PACMAN-" + "".join(secrets.choice(ALPHABET) for _ in range(4))
    digest = hmac.new(pepper.encode(), code.encode(), hashlib.sha256).hexdigest()
    expires = datetime.now(timezone.utc) + timedelta(days=7)
    return code, digest, expires

def main():
    pepper = os.environ.get("PLAYER_PASS_PEPPER")
    if not pepper:
        sys.exit("Missing PLAYER_PASS_PEPPER. Generate and store the secret server-side first.")
    try:
        code, digest, expires = generate(pepper)
    except ValueError as exc:
        sys.exit(str(exc))
    print("ONE-TIME PRIVATE CODE (do not paste into GitHub or chat):", code)
    print("SERVER-ONLY HMAC DIGEST:", digest)
    print("EXPIRES UTC:", expires.isoformat())
    print("Next: trusted operator verifies DON's GitHub Auth identity and")
    print("inserts the digest in arcade_private.player_pass_codes.")
    print("This tool NEVER writes to Supabase or grants admin rights.")

if __name__ == "__main__":
    main()
