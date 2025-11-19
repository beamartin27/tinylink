# TinyLink+

Minimal URL shortener built with **FastAPI + SQLite** to serve as the base for a DevOps pipeline (Assignment 2).  
Includes a tiny UI (Jinja/HTML) and a REST API with CRUD, redirect, and QR generation.

> **Status at submission**: UI + API fully working for the required features.  
> Short links & QR codes use a configurable base URL (`APP_BASE_URL`), so you can point them to localhost, ngrok, or a deployed domain.

---

## Features

- Create short links with optional **expiry** (UTC ISO-8601).
- **Redirect** `/{code}` with click counter, **410** (JSON) if expired.
- **CRUD API**: create, list, detail, update (target/expiry), delete.
- **QR PNG** endpoint for each short code (`/api/links/{code}/qr`).
- Minimal **Web UI**:
  - Create / Edit / Delete
  - Long URLs wrap (no horizontal scroll)
  - Copy short URL
  - Auto-refresh to see click counts update
  - QR preview + zoom modal
  - Details modal
  - Consistent JSON error envelope + visible error bar

---

## Tech

- Python 3.11+ (tested on 3.12)
- FastAPI, Uvicorn
- Pydantic v2
- SQLite (file `app.db`)
- qrcode (PNG generation)
- Jinja2 (UI template)

Install everything from `requirements.txt`.

**Additional prerequisite** (for public testing of QR):

- **ngrok** — to expose your local server with a public HTTPS URL.
  - Download from [ngrok.com](https://ngrok.com) and install
  - Run once: `ngrok config add-authtoken <YOUR_TOKEN>`

---

## Project structure

```
tinylink/
├─ app/
│ ├─ main.py                   # FastAPI app factory, routers, UI route, health, handlers
│ ├─ models.py                 # Pydantic models (LinkCreate, LinkUpdate, LinkOut, ErrorOut)
│ ├─ settings.py               # Settings (APP_ENV, APP_DB_PATH, APP_BASE_URL, metrics toggle)
│ ├─ utils.py                  # error envelope helper
│ ├─ metrics.py                # Prometheus middleware + /metrics endpoint
│ ├─ deps.py                   # DI helpers (get_repo, get_service)
│ ├─ repositories/
│ │ ├─ base.py                 # LinkRepository protocol
│ │ └─ sqlite.py               # SqliteLinkRepository implementation
│ ├─ services/
│ │ ├─ codes.py                # low-level code generator
│ │ ├─ codes_strategy.py       # CodeStrategy abstraction + RandomCodeStrategy
│ │ ├─ link_service.py         # business logic (create/update/resolve/delete)
│ │ └─ qrcodes.py              # QR PNG generator
│ ├─ routers/
│ │ ├─ links.py                # /api/links[...] (CRUD + QR)
│ │ └─ redirect.py             # /{code} (302 or 410)
│ ├─ static/
│ │ ├─ css/index.css           # styling for frontend
│ │ └─ js/index.js             # frontend logic
│ └─ templates/
│ └─ index.html                # minimal UI
├─ docs/
│ ├─ PLANNING.md               # goals & phases
│ ├─ HLD.md                    # high-level design
│ ├─ LLD.md                    # low-level design
│ ├─ SRS.md                    # requirements
│ ├─ O&M.md                    # ops & maintenance
│ └─ REFACTOR_PLAN.md          # A2 refactor notes
├─ tests/
│ ├─ unit/
│ │ ├─ test_codes_strategy.py
│ │ └─ test_link_service.py
│ └─ integration/
│ └─ test_links_api.py
├─ requirements.txt
├─ dockerfile
├─ .dockerignore
└─ README.md
```

---

## Run (local) — Recommended with ngrok (public URL)

**Why**: QR codes need to point to a URL that's reachable from other devices. ngrok gives you a public HTTPS URL.

```bash
# 1) Clone
git clone https://github.com/beamartin27/tinylink
cd tinylink

# 2) Create / activate virtualenv and install deps
python -m venv .venv

# Windows PowerShell:
.\.venv\Scripts\Activate.ps1

# Windows Git Bash:
source .venv/Scripts/activate

# macOS / Linux:
# source .venv/bin/activate

pip install -r requirements.txt

# 3) Open TWO terminals

# Terminal A — start the tunnel
ngrok http 8000

# ngrok will show something like:
# Forwarding https://1e57f896e13.ngrok-free.app -> http://localhost:8000
# Copy that HTTPS URL (https://1e57f896e13.ngrok-free.app).

# Terminal B — Start the app with APP_BASE_URL

# Git bash / Linux / macOS
export APP_BASE_URL="https://<your-ngrok>.ngrok-free.app" 
uvicorn app.main:app --host 0.0.0.0 --port 8000

# PowerShell
$env:APP_BASE_URL = "https://<your-ngrok>.ngrok-free.app"
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

4) Use it

* Open the same HTTPS ngrok URL in your browser.
* Created short links / QR codes will embed that ngrok domain, so you can scan them from your phone.

  Note: if ngrok gives you a new URL (e.g. you restart it), you must:
    * stop uvicorn
    * update APP_BASE_URL
    * start uvicorn again

**Alternative** (local only, no ngrok):

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
# UI: http://127.0.0.1:8000
# API docs (Swagger): http://127.0.0.1:8000/docs
```

**Note**: Without ngrok, QR codes will embed `http://127.0.0.1:8000`, which only works on the same machine.

**Healthcheck**: `GET /health` → `{"status":"ok"}`

---

## 🐳 Run with Docker (optional)

Build the image (from repo root):

```bash
docker build -t tinylink:latest .
```

Run the container and persist the DB on your host:

**PowerShell (Windows)**:

```powershell
docker run --rm -p 8000:8000 -v "$PWD/app.db:/app/app.db" tinylink:latest
```

**Git Bash / WSL / macOS / Linux**:

```bash
docker run --rm -p 8000:8000 -v "$PWD/app.db:/app/app.db" tinylink:latest
```

Then start ngrok in a second terminal:

```bash
ngrok http 8000
```

Open the ngrok Forwarding URL.

**Environment variables** (optional):

- `APP_DB_PATH` — override the DB location (default: `/app/app.db`)
- `APP_BASE_URL` — public base URL for generated links/QRs
  (e.g. `https://your-ngrok.ngrok-free.app` or your deployed domain)

```bash
docker run --rm \
  -e APP_DB_PATH="/app/app.db" \
  -e APP_BASE_URL="https://<your-ngrok>.ngrok-free.app" \
  -p 8000:8000 tinylink:latest
```

---

## API quickstart

Replace `HOST` with your URL (ngrok recommended):

### Set HOST

```bash
# bash / zsh
HOST="https://abc123.ngrok-free.app"

# PowerShell
$env:HOST="https://abc123.ngrok-free.app"
```

### Create

```bash
curl -s -X POST "$HOST/api/links" \
  -H "Content-Type: application/json" \
  -d '{"target_url":"https://example.com","expires_at":"2025-12-31T23:59:00Z"}'
```

### List

```bash
curl -s "$HOST/api/links"
```

### Detail

```bash
curl -s "$HOST/api/links/<code>"
```

### Update (target and/or expiry)

```bash
curl -s -X PUT "$HOST/api/links/<code>" \
  -H "Content-Type: application/json" \
  -d '{"target_url":"https://new.example.com","expires_at":"2026-01-01T10:00:00Z"}'
```

### Delete

```bash
curl -s -X DELETE "$HOST/api/links/<code>"
```

### Redirect

```bash
GET <HOST>/<code>   → 302 to target (or 410 JSON if expired)
```

### QR PNG

```bash
GET <HOST>/api/links/<code>/qr   → image/png
```

---

## Running tests

Tests run fully in-process (no Uvicorn/ngrok needed) and use a temporary SQLite DB for integration tests, so your real application database is never touched.

### Layout

- `tests/unit/`
  - `test_codes_strategy.py` → tests `RandomCodeStrategy` and code generation behavior in isolation.
  - `test_link_service.py` → tests `LinkService` using a fake in-memory repository (no SQLite).
- `tests/integration/`
  - `test_links_api.py` → tests the FastAPI app end-to-end (create, list, update, delete, redirect, QR, expiry) against a temp SQLite DB.

**Install dev deps** (once):

```bash
pip install -r requirements.txt
# If needed: pip install pytest httpx
```

**Run tests with coverage**:

```bash
python -m pytest -q --cov=app --cov-report=xml --cov-fail-under=70
```

This will:
* Run all tests under tests/
* Measure coverage for the app package
* Fail the run if coverage drops below 70%
* Write coverage.xml for CI tooling

**Useful variants**:

```bash
pytest -vv                # more verbose output
pytest -k T5 -vv          # run tests matching "T5"
pytest -q --maxfail=1     # stop on first failure
```

**Linting**:

```bash
ruff check .
```

---

## Manual test plan

1. **Create** a link (with and without expiry) → appears in UI table.
2. **Click** short URL → redirects (302).
3. **Click** QR (small) → zoom modal; scan with phone.
4. **Edit** target/expiry → row updates; redirect honors new expiry.
5. **Set** expiry in past → badge "Expired"; redirect returns 410 JSON.
6. **Delete** → row removed.
7. **Auto-refresh** → click counts increment without reload.

---

## Monitoring with Prometheus (optional)

The app exposes Prometheus metrics at `GET /metrics`.

An example Prometheus config is provided at `docs/prometheus.example.yml`. Steps:

1. Install Prometheus from the official website (no binary is committed in this repo).
2. Start your app on port 8000 (see "Run" section).
3. Run Prometheus pointing to the example config, e.g. on Windows:

   ```powershell
   cd C:\prometheus
   .\prometheus.exe --config.file="C:\path\to\tinylink\docs\prometheus.example.yml"

---

## Troubleshooting

- **QR not working externally**: Ensure ngrok is running and you're using the ngrok HTTPS URL.
- **Port busy**: change to `--port 8001` (and `ngrok http 8001`).
- **Template error in Docker** ("jinja2 must be installed"): ensure jinja2 is in `requirements.txt` (it is).
- **httpx missing when running tests**: `pip install httpx`.
- **Windows volume paths**: prefer PowerShell and use `"$PWD"` in the `-v` argument.

---

## Notes

- The app reads `APP_BASE_URL` for the public base URL (default: `http://localhost:8000`).
  Set this to your ngrok URL or deployed domain so links/QRs are correct.
- The database path can be overridden with `APP_DB_PATH` (env var) if needed
- Metrics are exposed at /metrics when APP_ENABLE_METRICS=1 (default).
