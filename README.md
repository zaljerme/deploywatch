# DeployWatch

DeployWatch records HTTP checks and opens an incident after three consecutive failures.
It tracks recovery so developers can see when an outage was observed and how long it lasted.

The implementation includes monitor CRUD, pause/resume, persistent checks, an incident engine,
an independent worker, Alembic migrations, authenticated API endpoints, and a controllable demo.
The React dashboard shows recent checks, response-time history, sample-based uptime, and incident
timelines. Optional GitHub activity adds commits and deployment records as investigation clues.

## Run locally

Install Docker Desktop with Compose. From the repository root in PowerShell:

```powershell
Copy-Item .env.example .env
docker compose up --build -d
Invoke-RestMethod http://localhost:8000/health/ready
Start-Process http://localhost:8080
```

The API documentation is at http://localhost:8000/docs. Use its Authorize control with
`local-development-token-change-me` as the bearer token if prompted. All `/api` routes require
`Authorization: Bearer <API_TOKEN>`. The health endpoints are public.
Enter the same token on the dashboard. It stays in tab memory and is cleared on reload or disconnect.
The browser sends API requests through the frontend's same-origin proxy; no CORS configuration
or token embedded in the JavaScript build is needed.

Configuration lives in `.env`: `DATABASE_URL`, `API_TOKEN`, `ENVIRONMENT`, `ALLOW_DEMO`,
`DEMO_HOST`, and optional `GITHUB_TOKEN`. Compose overrides the database hostname to `db`.
Keep `DEMO_HOST=demo` for Compose. The default database password and token are local examples.
The initial migration runs as a separate Compose job before API and worker startup.

## Demo

```powershell
$headers = @{ Authorization = 'Bearer local-development-token-change-me' }
$body = @{ name='Demo API'; url='http://demo:8001/health'; interval_seconds=5; timeout_seconds=2; expected_status=200 } | ConvertTo-Json
$monitor = Invoke-RestMethod http://localhost:8000/api/monitors -Method Post -Headers $headers -ContentType application/json -Body $body
Invoke-RestMethod http://localhost:8001/mode -Method Put -ContentType application/json -Body '{"mode":"failing"}'
Start-Sleep 20
Invoke-RestMethod "http://localhost:8000/api/monitors/$($monitor.id)/history" -Headers $headers
Invoke-RestMethod http://localhost:8001/mode -Method Put -ContentType application/json -Body '{"mode":"healthy"}'
Start-Sleep 7
Invoke-RestMethod "http://localhost:8000/api/monitors/$($monitor.id)/history" -Headers $headers
```

In the dashboard, select Demo API and watch its status become degraded after the first failure,
then down after the third. After switching back to healthy, the next check resolves the incident.
The dashboard polls every ten seconds, so the display can lag behind the stored result.
The incident start is the first observed failure; detection happens on the third failure.
An outage between checks can be missed. Do not present sampled duration as exact downtime.

Edit the monitor to set a real `owner/repository`, such as `fastapi/fastapi`, to exercise GitHub
activity. This example repository is unrelated to the demo endpoint; its activity is only an
integration demonstration. Use your own repository for meaningful investigation context.

Set the demo mode to `slow` to exercise a ten-second response against a two-second timeout.
The demo mode lives in memory and resets to healthy on restart. Monitor state lives in PostgreSQL.
`docker compose down` preserves data; `docker compose down -v` deletes it.

## Develop and test

Python 3.12+ is required (the container uses 3.13). These commands run from the root:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e './backend[dev]'
Set-Location backend
..\.venv\Scripts\python -m pytest
..\.venv\Scripts\ruff check .
..\.venv\Scripts\ruff format --check .
Set-Location ../frontend
npm ci
npm test
npm run build
```

Tests use in-memory SQLite for isolated state-machine and API checks. The production worker
requires PostgreSQL because SQLite does not implement `FOR UPDATE SKIP LOCKED`.
To include the PostgreSQL concurrency test, create an **expendable, separate test database** and set
`TEST_DATABASE_URL` before running pytest. That fixture creates and drops an isolated test schema;
never point it at a database containing useful data. GitHub Actions provisions a dedicated database
and runs the tests, Ruff checks, TypeScript build, frontend tests, and migration round trip.

For development without containers, provide PostgreSQL, set `DATABASE_URL`, and run these
commands from `backend` in separate terminals after installing the Python dependencies above:

```powershell
$env:DATABASE_URL = 'postgresql+psycopg://deploywatch:deploywatch@127.0.0.1:5432/deploywatch'
..\.venv\Scripts\alembic upgrade head
..\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

```powershell
$env:DATABASE_URL = 'postgresql+psycopg://deploywatch:deploywatch@127.0.0.1:5432/deploywatch'
$env:ALLOW_DEMO = 'true'
$env:DEMO_HOST = '127.0.0.1'
..\.venv\Scripts\python -m app.worker
```

```powershell
..\.venv\Scripts\python -m uvicorn app.demo:app --host 127.0.0.1 --port 8001
```

From `frontend`, run `npm ci` then `npm run dev` (Node 22.12+ or 24+). Open the printed Vite
URL. For this native setup, use `http://127.0.0.1:8001/health` in the monitor. Each process reads
environment variables and an optional `.env` in its own working directory; the root `.env` is
automatically used by Compose only. If you change the token, set the same value for API and UI login.

## Architecture and decisions

```text
Browser → Nginx (Compose) / Vite (development) → FastAPI → PostgreSQL
                                               ↓
                                           GitHub REST API
Worker → PostgreSQL row lock → bounded HTTP probe → check + incident transaction
                                    ↓
                              public API / local demo
```

The API manages monitors; it never performs a check inside a web request. A separate worker
polls for a due monitor, locks its row, performs a bounded HTTP request, and atomically stores
the result, failure count, incident change, and next due time. Other workers skip the locked row.
An unsuccessful transaction rolls back; a crashed worker leaves the monitor due for retry.
One worker processes one check at a time. Multiple worker processes can share PostgreSQL.
PostgreSQL's [locking clauses](https://www.postgresql.org/docs/17/sql-select.html#SQL-FOR-UPDATE-SHARE)
make `SKIP LOCKED` appropriate for this queue-like selection. The partial index remains a second
line of defense against duplicate open incidents.

Two failures leave the monitor in a degraded state. The third opens an incident whose
`started_at` is the first failure of that run and whose `detected_at` is the third.
The first successful check resolves it. A partial unique database index permits only one open
incident per monitor. Pausing preserves the failure count and any open incident; resuming
continues the sequence. Paused time cannot establish recovery. Changing the target or expected
status resets the failure count and is blocked while an incident is open. Delete cascades history.

Uptime is successful checks divided by all checks in the requested rolling window, multiplied
by 100. No checks means unknown (`null`), not 100%. Paused periods add no samples. This is a
sample-based measure, not an estimate of continuous availability. The history endpoint defaults
to 24 hours; its aggregate covers the full window even when displayed checks are paginated.

## Security and limits

Compose binds exposed ports to loopback. Development uses a shared bearer token, including reads;
change it in `.env`. Before public exposure, set `ENVIRONMENT=production`, disable `ALLOW_DEMO`,
set a unique random token of at least 32 characters, and place the app behind HTTPS and an
appropriate access gateway. There are no user accounts, tenant isolation, or token rotation UI.

The probe only accepts HTTP(S), restricts ports, rejects credentials and fragments, checks every
DNS address for public reachability, pins the connection to that snapshot, disables proxies and
redirects, and limits the body to 64 KiB. TLS verifies the original hostname. DNS is inside the
overall timeout (1–30 seconds). The only internal exception is exactly `http://<DEMO_HOST>:8001/health`,
where `DEMO_HOST` can only be `demo` or `127.0.0.1`, with development mode and `ALLOW_DEMO=true`.
Unsafe destinations can be saved but produce an
`unsafe_destination` check without connecting. An outbound firewall remains useful defense in depth.

There are no alerts or retention jobs yet. API lists are bounded (500 monitors, 100 incidents),
checks have cursor pagination, and old data is retained until a monitor is deleted. Holding a
transaction during a check is intentional and bounded; it costs one database connection per
active worker and can delay edits by up to the check timeout. Worker/database outages produce
missing samples; they are not recorded as target failures. Monitor interval is measured from
check completion, so cadence includes request duration. Health readiness checks database access,
not worker progress. Logs report monitor IDs, timing, and failure categories without URL secrets.

GitHub commits and deployment records come from separate REST resources. A deployment record
is a request to deploy, not evidence that deployment completed; statuses are not fetched.
See GitHub's [deployment model](https://docs.github.com/en/rest/deployments/deployments).
GitHub failures never modify check or incident state. Each activity stream has an eight-second
deadline, four-second request timeouts, a 1 MiB response limit, and at most three pages of twenty
records. Link URLs are not followed. The dashboard displays five entries per stream; the API
returns up to sixty and marks truncated results. Empty deployment data is valid.

Activity is cached in API-process memory for sixty seconds, with bounded rate-limit cooldowns
of sixty seconds to one hour. A failing stream can return older data marked stale while the other
stream remains available. The cache holds at most 128 repositories, resets on API restart, and is
not shared across API processes. It serializes refreshes, which is suitable for this small local app
but can delay requests across many repositories. Public repositories work without a token;
private repositories require a server-side fine-grained token with Contents and Deployments read
permissions. Never enter a GitHub token into the dashboard's API-token field.

The dashboard requests history per monitor and is intended for a small workspace, not hundreds
of monitors. Charts use at most the most recent 200 samples in the selected window; checks table
shows ten. Incident history is capped at 100 entries per monitor per request. No deployment status
verification, notifications, retention, distributed cache, or load benchmark is implemented.

## Verification and project handoff

[Verification notes](docs/verification.md) record actual local results and verification limits.
[GitHub handoff](docs/github-handoff.md) includes the two milestone branches, PR descriptions,
merge steps, achievement status, and an optional genuine documentation task.
[Interview notes](docs/interview.md) cover the design tradeoffs and resume wording.
