# TinyLink+

Minimal URL shortener built with **FastAPI + SQLite** to serve as the base for a DevOps pipeline (Assignment 2).  
Includes a tiny UI (Jinja/HTML) and a REST API with CRUD, redirect, and QR generation.

> **Status at submission**: UI + API fully working for the required features.  
> The service auto-detects the request host, so short links & QR codes work locally and via ngrok without extra config.

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
│  ├─ main.py              # FastAPI app factory, routers mount, UI route, health, handlers
│  ├─ db.py                # SQLite schema + CRUD helpers (single DB path; tests use temp DBs)
│  ├─ models.py            # Pydantic models (LinkCreate, LinkUpdate, LinkOut)
│  ├─ routers/
│  │  ├─ links.py          # /api/links[...] (CRUD + QR)
│  │  └─ redirect.py       # /{code} (302 or 410)
│  ├─ services/
│  │  ├─ codes.py          # short code generator (collision-safe)
│  │  └─ qrcodes.py        # QR PNG generator
|  ├─ static
|  |  ├─ css/
|  |  |  └─ index.css      # styling for frontend
|  |  └─ js
|  |     └─ index.js       # frontend logic
│  ├─ templates/
│  │  └─ index.html        # minimal UI (html)
│  └─ utils.py             # error envelope helper
├─ docs/
│  ├─ HLD.md               # high-level design
│  ├─ LLD.md               # low-level design
│  ├─ PLANNING.md          # goals & phases
│  └─ SRS.md               # requirements
├─ tests/
│  └─ test_links.py        # unit/integration/system tests
├─ .gitignore
├─ app.db                  # SQLite DB (created on first run)
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

# Terminal A — start the app
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Terminal B — start the tunnel
ngrok http 8000

# 4) Open the HTTPS "Forwarding" URL from ngrok in the browser.
#    The app auto-detects the public host, so short links & QR codes
#    will use that ngrok domain (scannable from any phone).
```

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

- `DB_PATH` — override the DB location (default: `/app/app.db`)

```bash
docker run --rm -e DB_PATH=/app/data/app.db -v "$PWD/data:/app/data" -p 8000:8000 tinylink:latest
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

Tests run fully in-process (no Uvicorn/ngrok needed) and use a temporary SQLite DB per test, so your real `app.db` is untouched.

**Install dev deps** (once):

```bash
pip install -r requirements.txt
# If needed: pip install pytest httpx
```

**Run tests**:

```bash
python -m pytest -q
```

**Tips**:

```bash
pytest -vv                # more output
pytest -k T5 -vv          # run tests matching "T5"
pytest -q --maxfail=1     # stop on first failure
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

## Troubleshooting

- **QR not working externally**: Ensure ngrok is running and you're using the ngrok HTTPS URL.
- **Port busy**: change to `--port 8001` (and `ngrok http 8001`).
- **Template error in Docker** ("jinja2 must be installed"): ensure jinja2 is in `requirements.txt` (it is).
- **httpx missing when running tests**: `pip install httpx`.
- **Windows volume paths**: prefer PowerShell and use `"$PWD"` in the `-v` argument.

---

## Notes

- The app derives the base URL from the incoming request, so you don't need to set `BASE_URL`. This makes QR codes/links correct for local, LAN, or ngrok usage automatically.
- The database path can be overridden with `DB_PATH` (env var) if needed
