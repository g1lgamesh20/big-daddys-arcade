#!/usr/bin/env python3
"""Decide whether a missed automatic achievement run needs recovering.

Input is the JSON array from 'gh run list --workflow auto-challenge-awards.yml'.
This checks completed successful executions, never score timestamps or
unapproved candidate records. The actual awards stay in the existing, locked,
idempotent issuance workflow.
"""
import argparse
import json
from datetime import datetime, timezone

MAX_SUCCESS_AGE_MINUTES = 75

def parse_time(value):
    if not isinstance(value, str):
        return None
    try:
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return timestamp.astimezone(timezone.utc) if timestamp.tzinfo else None
    except ValueError:
        return None

def need_recovery(runs, now, max_age_minutes=MAX_SUCCESS_AGE_MINUTES):
    if now.tzinfo is None or max_age_minutes <= 0:
        raise ValueError("Need aware time and positive threshold")
    if not isinstance(runs, list):
        raise ValueError("Expected GitHub workflow run list")
    for run in runs:
        if not isinstance(run, dict):
            continue
        if run.get("status") in ("queued", "in_progress", "waiting", "pending", "requested"):
            return False, "award_run_already_pending"
    succeeded = [
        parse_time(run.get("createdAt"))
        for run in runs if isinstance(run, dict)
        and run.get("status") == "completed"
        and run.get("conclusion") == "success"
    ]
    succeeded = [item for item in succeeded if item is not None]
    if not succeeded:
        return True, "no_recent_success"
    age = (now.astimezone(timezone.utc) - max(succeeded)).total_seconds() / 60
    if age < -5:
        return True, "future_success_timestamp"
    return (age > max_age_minutes), ("stale" if age > max_age_minutes else "recent_success")

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--runs-json", required=True)
    parser.add_argument("--github-output", required=True)
    args=parser.parse_args()
    with open(args.runs_json, encoding="utf-8") as src:
        runs=json.load(src)
    needed, reason=need_recovery(runs, datetime.now(timezone.utc))
    print(f"Automatic award recovery: {reason}; dispatch={str(needed).lower()}")
    with open(args.github_output,"a",encoding="utf-8") as out:
        out.write(f"dispatch={str(needed).lower()}\nreason={reason}\n")

if __name__ == "__main__":
    main()
