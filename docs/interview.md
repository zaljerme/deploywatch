# Explaining DeployWatch

“DeployWatch monitors HTTP endpoints and records incident timelines. I separated scheduled
checks from FastAPI requests so slow targets do not hold up the dashboard. A worker locks a due
monitor in PostgreSQL and stores its result and incident transition in one transaction. Three
consecutive failures open an incident; a successful check resolves it. A partial unique index
prevents two open incidents for the same monitor. The React UI shows sampled availability and
recent GitHub activity, with commits and deployment records labeled separately. GitHub errors
affect investigation context, never monitoring state.”

Be ready to walk through `backend/app/worker.py`, `engine.py`, `probe.py`, and `github.py`.
Explain why sampled availability is different from continuous uptime and why timing alone
cannot identify an outage's cause.

The worker holds a database connection and row lock while making its bounded HTTP call.
This is simple to reason about and tested against PostgreSQL. For larger workloads, a lease
with fencing would avoid holding transactions over network calls but introduces expiry and
stale-worker correctness problems. Do not claim this implementation includes that system.

Useful resume bullets, after you have reviewed and can explain the code:

- Built an HTTP monitoring application with FastAPI, PostgreSQL, a separate worker, and a
  React/TypeScript dashboard; implemented three-failure incident detection and automatic recovery.
- Used row locks, transactions, and a partial unique index to prevent overlapping checks and
  duplicate open incidents; verified worker contention against PostgreSQL.
- Added SSRF restrictions with DNS validation and pinned connections, bounded HTTP requests,
  and GitHub activity handling for pagination, rate limits, stale data, and partial failures.
- Verified 33 backend tests and four frontend tests locally; configured GitHub Actions for
  backend checks, frontend tests/build, and migration validation.

Do not say CI passed until the hosted workflow passes. Do not infer production reliability,
user adoption, throughput, or performance gains from the test count or one demo run.
