# Hall of Legends — GitHub-only 30-minute refresh experiment

**Start:** when this PR is merged. **Evaluation:** after 24–48 hours.

GitHub Actions `.github/workflows/update-legends.yml` schedules the existing score refresh at **:13 and :43 UTC every hour** (twice per hour). These are cron trigger targets, not guaranteed starts. No external scheduler or new provider is involved.

## What we measure

The existing workflow still updates iScored scoreboards and delivers new-medal OneSignal messages. After successful score and notification processing, it writes `refresh-health.json` to the repository:

- `last_success_at` — successful job timestamp UTC.
- `last_trigger` — `schedule` or `workflow_dispatch`.
- `last_scheduled_success_at` — remains unchanged when someone runs a manual refresh.
- `previous_success_gap_minutes` — elapsed time from previous successful refresh.
- `estimated_missed_intervals_since_previous_success` — rough count of missed 30-minute windows, **not proof each schedule event was dropped**.

The workflow summary also records the gap and warns if it exceeds 65 minutes. To check the *current* freshness during a period when GitHub never triggers a workflow, compare `last_success_at` against current UTC time. Since GitHub never started the missing job, it cannot alert itself about that omission: this is a heartbeat, not an independent monitor.

## Interpreting results

After 24–48 hours, visit the [workflow history](https://github.com/g1lgamesh20/big-daddys-arcade/actions/workflows/update-legends.yml) and compare `schedule` events against two attempts per hour. Separate results into:

1. Missing entirely (GitHub did not create a run).
2. Run created but failed (check whether it got HTTP 403 from iScored).
3. Successful scheduled refresh.
4. Successful manual refresh (does **not** count as scheduler success).

The score-fetch retry makes at most three identical requests, sleeping 2 and 5 seconds on HTTP 403, 408, 429, or 5xx, and transient connection errors. It does not change credentials, bypass blocks, retry invalid payloads, or write partial scores. On a persistent 403, the job fails safely and the prior scoreboard remains. Lower frequency may reduce traffic; it cannot force GitHub's scheduler to fire.

## Rollback

Revert the workflow cron to `7,22,37,52 * * * *` for 15-minute scheduling, after reviewing the experiment. The health file and retry helper may be retained independently. No medal, trophy, daily or monthly award semantics were changed.
