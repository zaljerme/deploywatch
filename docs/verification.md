# Verification record

Local verification on October 23, 2026 (America/Los_Angeles):

- Windows, Python 3.14.3, Node 24.13.1, temporary PostgreSQL 17.6 bound to loopback.
- Milestone one: 21 tests passed before dashboard implementation, including concurrent worker
  selection against PostgreSQL. Later shared fixes add a demo test and normalize UTC output.
- Final backend: 33 tests passed in 2.25 seconds, including the PostgreSQL concurrency test.
- Frontend: four interaction/state tests passed after component extraction.
- Ruff lint and formatting passed; TypeScript and Vite build passed.
- PostgreSQL Alembic upgrade, schema-drift check, downgrade, and upgrade passed.
- npm audit reported zero known vulnerabilities after updating Vite, its React plugin, and Vitest.
- Browser check at a narrow viewport: login, empty state, create monitor, live monitor results,
  incident timeline, chart, and GitHub activity.

The live demo used the actual API, separate worker, PostgreSQL, and controllable HTTP target.
At a five-second interval, its first failure occurred at 2026-10-24 01:13:20.960406 UTC,
incident detection at 01:13:31.113248 UTC, and recovery at 01:13:36.188126 UTC.
That run observed three consecutive failures, opened one incident about 10.15 seconds after
the first failure, and resolved it on the next successful check. The observed failure-to-recovery
interval was about 15.23 seconds. These are one demo's results, not a throughput benchmark or SLA.

A live read of `fastapi/fastapi` returned commits and deployment records independently.
The data is unrelated to the local demo target; no causal relationship is implied.
Most network behavior tests use mocked DNS, HTTP transports, or a controlled local HTTP server.

Docker and GitHub CLI were unavailable. The Compose stack has not been built or run here;
Nginx container behavior and the Python 3.13/Linux CI environment remain to be verified by
Docker/Actions. Source install was verified locally with `pip install -e './backend[dev]'`.
GitHub Actions configuration is included but has not run on GitHub. No PRs were pushed or merged.
Public badge status could not be confirmed. One upstream Starlette deprecation warning concerns
its TestClient HTTPX integration; all tests passed despite the warning.

No production deployment, public users, sustained load test, notification delivery, or measured
performance improvement is claimed. A desktop-width browser check and broader accessibility
audit remain useful follow-up validation.
