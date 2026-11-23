#!/usr/bin/env python3
"""Isolated live Postgres uniqueness test. No real ledger writes, no push.

20 concurrent REST upserts race to insert the same random probe key.
Exactly one should insert; remaining requests should return empty arrays.
Finally removes only this run's probe row.
"""
import json
import os
import secrets
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

BASE = "https://jrqzwlowxofnyqpmjgkg.supabase.co/rest/v1/arcade_props_concurrency_probe"


def request(method, key, token, body=None, prefer=None):
    url = BASE + "?probe_key=eq." + urllib.parse.quote(key, safe="")
    headers = {
        "apikey": token,
        "Authorization": "Bearer " + token,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if prefer:
        headers["Prefer"] = prefer
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else []
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Probe HTTP {exc.code}: {exc.read().decode()[:400]}") from exc


def main():
    token = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not token:
        raise RuntimeError("Missing SUPABASE_SERVICE_ROLE_KEY")
    key = "props-concurrency-" + secrets.token_hex(16)
    print("LIVE ISOLATED CONCURRENCY PROBE — no notifications or delivery ledger writes")
    try:
        def contender(_):
            return request(
                "POST", key, token,
                body={"probe_key": key},
                prefer="resolution=ignore-duplicates,return=representation",
            )
        with ThreadPoolExecutor(max_workers=20) as pool:
            responses = list(pool.map(contender, range(20)))
        inserted = sum(len(rows) for rows in responses)
        if inserted != 1:
            raise RuntimeError(f"Expected exactly one successful insert; got {inserted}")
        rows = request("GET", key, token)
        if len(rows) != 1:
            raise RuntimeError(f"Expected exactly one row in database; got {len(rows)}")
        print("PASS: 20 concurrent claims; exactly one row inserted.")
        print("PASS: database unique constraint prevented 19 duplicate inserts.")
    finally:
        request("DELETE", key, token, prefer="return=representation")
        remaining = request("GET", key, token)
        if remaining:
            raise RuntimeError("Probe cleanup failed; test row still exists")
        print("PASS: isolated probe row cleaned up.")
    print("NO real delivery reservations, OneSignal pushes, trophies, or news.")


if __name__ == "__main__":
    main()
