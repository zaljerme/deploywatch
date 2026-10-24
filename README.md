# DeployWatch

DeployWatch records HTTP checks and opens an incident after three consecutive failures.
It tracks recovery so developers can see when an outage was observed and how long it lasted.

Milestone 1 includes monitor CRUD, pause/resume, persistent checks, an incident engine,
an independent worker, Alembic migrations, authenticated API endpoints, and a controllable demo.

## Run locally

Install Docker Desktop with Compose. From the repository root in PowerShell:

```powershell
Copy-Item .env.example .env
docker compose up --build -d
Invoke-RestMethod http://localhost:8000/health/ready
```

The API documentation is at http://localhost:8000/docs. Use its Authorize control with
`local-development-token-change-me` as the bearer token if prompted. All `/api` routes require
`Authorization: Bearer <API_TOKEN>`. The health endpoints are public.

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
```

Tests use in-memory SQLite for isolated state-machine and API checks. The production worker
requires PostgreSQL because SQLite does not implement `FOR UPDATE SKIP LOCKED`.

## Architecture and decisions

The API manages monitors; it never performs a check inside a web request. A separate worker
polls for a due monitor, locks its row, performs a bounded HTTP request, and atomically stores
the result, failure count, incident change, and next due time. Other workers skip the locked row.
An unsuccessful transaction rolls back; a crashed worker leaves the monitor due for retry.
One worker processes one check at a time. Multiple worker processes can share PostgreSQL.

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
overall timeout (1–30 seconds). The only internal exception is exactly `http://demo:8001/health`
with development mode and `ALLOW_DEMO=true`. Unsafe destinations can be saved but produce an
`unsafe_destination` check without connecting. An outbound firewall remains useful defense in depth.

There are no alerts or retention jobs yet. API lists are bounded (500 monitors, 100 incidents),
checks have cursor pagination, and old data is retained until a monitor is deleted. Holding a
transaction during a check is intentional and bounded; it costs one database connection per
active worker and can delay edits by up to the check timeout. Worker/database outages produce
missing samples; they are not recorded as target failures. Monitor interval is measured from
check completion, so cadence includes request duration. Health readiness checks database access,
not worker progress. Logs report check IDs, timing, and failure categories without URL secrets.
