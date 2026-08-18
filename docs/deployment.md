# Deployment

## Configuration

Every setting is read from the environment (`backend/app/core/config.py`); nothing
is hardcoded. Copy `backend/.env.example` to `.env` and fill it in.

| Variable | Default | Notes |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./fleet.db` | Use `postgresql+psycopg://…` in production |
| `JWT_SECRET_KEY` | insecure dev value | **Must** be overridden; `openssl rand -hex 32` |
| `JWT_ALGORITHM` | `HS256` | |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `30` | |
| `CORS_ORIGINS` | `*` | Comma-separated list; narrow this in production |
| `ENVIRONMENT` | `development` | Surfaced by `/health` |
| `DEBUG` | `true` | Set `false` in production |
| `MAINTENANCE_DUE_WINDOW_DAYS` | `14` | Lookahead for "due for service" |
| `DOCUMENT_EXPIRY_WINDOW_DAYS` | `30` | Lookahead for expiring documents |

`.env` is gitignored. Only `.env.example` — which holds no real secrets — is
committed. On a hosted platform set the variables in the dashboard rather than
shipping a file.

## Option 1 — Render (blueprint)

`render.yaml` at the repo root provisions a Docker web service and a managed
PostgreSQL instance, wires `DATABASE_URL` between them, and generates
`JWT_SECRET_KEY`.

1. Push the repository to GitHub.
2. In Render: **New → Blueprint**, point it at the repo, apply.
3. Wait for the first deploy. Migrations run at container start, so the schema is
   created automatically.
4. Check `https://<service>.onrender.com/health`.

To load demo data once, from the Render shell:

```bash
python -m app.seed
```

## Option 2 — Docker anywhere

```bash
cd backend
docker build -t fleet-api .
docker run -p 8000:8000 \
  -e DATABASE_URL="postgresql+psycopg://user:pass@host:5432/fleet" \
  -e JWT_SECRET_KEY="$(openssl rand -hex 32)" \
  -e ENVIRONMENT=production -e DEBUG=false \
  fleet-api
```

The image runs as a non-root user, declares a `HEALTHCHECK`, and applies
migrations before starting uvicorn.

## Option 3 — Docker Compose (local PostgreSQL)

```bash
cd backend
docker compose up --build
```

Brings up PostgreSQL 16 and the API, waiting for the database health check
before starting the API.

## Option 4 — Bare metal / VM

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL="postgresql+psycopg://user:pass@localhost:5432/fleet"
export JWT_SECRET_KEY="$(openssl rand -hex 32)"
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

Put nginx or a load balancer in front for TLS. Note that with more than one
worker the in-process WebSocket hub only reaches clients on the same worker —
see *Known limitations* in the README.

## Database migrations

The schema is managed by Alembic; it is never created implicitly at boot in
production.

```bash
alembic upgrade head          # apply
alembic downgrade -1          # roll back one
alembic revision --autogenerate -m "describe the change"
alembic current               # what is applied
```

Autogenerate compares `app/models` against the live database. Always read the
generated file before committing it — it cannot infer data migrations, and on
SQLite it needs the batch mode already configured in `alembic/env.py`.

## iOS build

The app has no third-party dependencies, so there is nothing to install first.

```bash
cd ios/FleetManager
open FleetManager.xcodeproj
```

Select an iPhone simulator and run (⌘R). To build from the command line:

```bash
xcodebuild -project FleetManager.xcodeproj -scheme FleetManager \
  -destination 'platform=iOS Simulator,name=iPhone 16' build
```

### Pointing the app at a deployed backend

`AppConfig.apiBaseURL` reads the `API_BASE_URL` Info.plist key when present and
otherwise falls back to `http://127.0.0.1:8000/api/v1`. To target a deployed
server, add a user-defined build setting and reference it from the Info.plist
section of the target's build settings:

```
API_BASE_URL = https://your-service.onrender.com/api/v1
```

Two caveats when testing on a physical device:

- `127.0.0.1` is the phone itself. Use your Mac's LAN address
  (`ipconfig getifaddr en0`) and run uvicorn with `--host 0.0.0.0`.
- App Transport Security blocks plain HTTP. Deploy behind HTTPS, or add a
  temporary ATS exception for the local address while developing.

### Producing a distributable build

An `.ipa` requires an Apple Developer account and a signing identity:

```bash
xcodebuild -project FleetManager.xcodeproj -scheme FleetManager \
  -configuration Release -archivePath build/FleetManager.xcarchive archive

xcodebuild -exportArchive -archivePath build/FleetManager.xcarchive \
  -exportOptionsPlist ExportOptions.plist -exportPath build/ipa
```

Without a paid account, the reviewable artefact is the simulator build produced
by the command above, which is what the CI workflow verifies on every push.

## Continuous integration

`.github/workflows/backend.yml` installs dependencies, applies migrations to an
empty database (so a broken migration fails the build), and runs the test suite.
`.github/workflows/ios.yml` builds the app for the simulator with code signing
disabled.
