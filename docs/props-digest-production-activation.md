# Give Props digest — production activation controls

**DO NOT ACTIVATE WITHOUT EXPLICIT OPERATOR APPROVAL.**

PR #75 installs a production workflow but does not enable it. The production
job requires repository Actions variable `PROPS_DIGEST_BROADCAST_ENABLED` to be
exactly `true`; absent, blank, or other values keep it locked. Do **not**
create or set that variable during installation or testing.

The production job also specifies GitHub Environment
`props-digest-production`. Before activation, the operator should configure
this environment with required reviewers and deployment branch restrictions
(where supported by their GitHub plan/repository). An environment alone is
not a lock unless protection rules are configured.

The job passes an internal authorization phrase to the existing sender,
which independently checks the 09:30–11:00 Eastern window and Supabase
atomic reservation. These safeguards do not guarantee exactly-once delivery
or delivery at precisely 09:30. GitHub cron can be late or skipped.

**Critical:** If the repository variable is set to `true`, BOTH manual and
scheduled workflow runs become eligible to broadcast. Do not set it until
the operator explicitly approves community-wide delivery. To disable future
runs, unset the variable or set it to `false`. Already-running jobs are not
necessarily stopped by changing the variable.

On ambiguous provider outcomes, the sender marks the date `unknown`
(or leaves it `reserved` if outcome recording fails). Do not reset/retry
without inspecting OneSignal and Supabase. The workflow has no automatic
rerun logic. Other existing OneSignal notifications are not modified.

Review outstanding reconciliation edge cases and confirm the environment
protection rules before enabling the variable.
