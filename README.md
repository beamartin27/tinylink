# TinyLink+

Minimal URL shortener built with **FastAPI + SQLite** to serve as the base for a DevOps pipeline in Assignment 2.  
Includes a tiny UI (Jinja/HTML) and a REST API with CRUD, redirect and QR generation.

> Status at submission: UI + API fully working for the required features.  
> Host auto-detected (works locally, on LAN and via ngrok).  

---

## Features (current)

- Create short links with optional **expiry** (UTC ISO-8601).
- **Redirect** `/{code}` with click counter and **410** when expired.
- **CRUD API** for links: create, list, detail, update (target/expiry), delete.
- **QR PNG** endpoint for the short URL (`/api/links/{code}/qr`).
- Minimal **Web UI**:
  - Create / Edit / Delete
  - List with **wrapping** long URLs (no scroll horizontal)
  - **Copy** short URL to clipboard
  - **Auto-refresh** for clicks
  - **QR preview** + **zoom**
  - **Details modal**
  - Consistent error envelope in JSON (and visible error bar)

---

## Tech

- Python 3.11+ (tested 3.12)
- FastAPI, Uvicorn
- Pydantic v2
- SQLite (file `app.db`)
- qrcode (for PNG)
- Jinja2 (UI template)

Install all from `requirements.txt`.

**Prequisite appart from requirements.txt**
- **ngrok** (for a public HTTPS URL so QR codes work from any device)
    * Download & install from ngrok.com
    * Run once: 'ngrok config add-authtoken <YOUR_TOKEN>'

---

## Project structure

```
tinylink/
├─ app/
│ ├─ main.py              # FastAPI app factory, routers mount, UI route, health, validators
│ ├─ db.py                # SQLite schema + CRUD helpers
│ ├─ models.py            # Pydantic models (LinkCreate, LinkUpdate, LinkOut)
│ ├─ routers/
│ │ ├─ links.py           # /api/links[...] (CRUD + QR)
│ │ └─ redirect.py        # /{code} (302 or 410)
│ ├─ services/
│ │ ├─ codes.py           # short code generator (collision-safe)
│ │ └─ qrcodes.py         # QR PNG generator
│ ├─ templates/
│ │ └─ index.html         # minimal UI (dark mode)
│ └─ utils.py             # error envelope helper
├─ docs/
| ├─ HLD.md               # high-level design
| ├─ LLD.md               # low-level design
| ├─ PLANNING.md          # goals, definition
| └─ SRS.md               # requirement analysis
├─ tests/
| └─ test_links.py        # tests
├─ .gitignore
├─ app.db                 # SQLite DB (created on first run)
├─ requirements.txt
└─ README.md
```

---

## 🚀 Run (local)

Follow the **recommended** steps to deploy the web publicly, enabling access from **any device** for the QR scanning.

```bash
# 1) Clone
git clone <your-repo-url>
cd tinylink

# 2) Create venv & install
python -m venv .venv
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
# Git Bash / Linux / macOS:
source .venv/Scripts/activate  # (Windows Git Bash)
# or: source .venv/bin/activate
pip install -r requirements.txt

# 3) Start server, public URL via ngrok - RECOMMENDED

# Open two terminals
# Terminal A - start the app
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Terminal B - start the tunnel
ngrok http 8000

# Copy the Fowarding https URL from ngrok (eg. https://abc123.ngrok-free.app).
# Open the app UI at that URL. The API docs are at <ngrok-https>/docs.
# The app auto detects the request host, so short URLs & QR codes will use the ngrok domain (scannable from any phone)

# ALTERNATIVE - Local only (no ngrok)
uvicorn app.main:app --host 0.0.0.0 --port 8000
# UI: http://127.0.0.1:8000
# API docs: http://127.0.0.1:8000/docs
```
    Note: QR codes will embed http://127.0.0.1:8000, which only works on the same machine. Use ngrok for external devices

**Healthcheck**: `GET /health` → `{"status":"ok"}`

## API quickstart (replace `HOST` with your URL)

Here are some commands for testing the API in the **CLI** instead of the UI.
- Set a `HOST` variable so commands are copy-paste friendly.

### HOST varieble
```bash
HOST="https://abc123.ngrok-free.app"   # <= your ngrok HTTPS
```
```powershell
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
curl -s "$HOST/api/links/3aqPiV"
```

### Update (change target and/or expiry)
```bash
curl -s -X PUT "$HOST/api/links/3aqPiV" \
  -H "Content-Type: application/json" \
  -d '{"target_url":"https://new.example.com","expires_at":"2026-01-01T10:00:00Z"}'

```

### Delete
```bash
curl -s -X DELETE "$HOST/api/links/3aqPiV"
```

### Redirect
```bash
<HOST>/<code>
# e.g. https://abc123.ngrok-free.app/3aqPiV
# → 302 to target (or 410 JSON if expired)
```

### QR PNG (open in browser)
```bash
<HOST>/api/links/<code>/qr
# e.g. https://abc123.ngrok-free.app/api/links/3aqPiV/qr
# → image/png

```

## Manual test plan

1. **Create** a link (with and without expiry) → appears in UI table.
2. **Click** short URL → redirects (302).
3. **Click** QR (small) → zoom modal; scan with phone.
4. **Edit** target/expiry → row updates; redirect honors new expiry.
5. **Set** expiry in past → badge "Expired" and redirect returns 410 (JSON).
6. **Delete** → row removed.
7. **Auto-refresh** → clicks increment without reload.

## Troubleshooting

- **Port busy**: change to `--port 8001` (and `ngrok http 8001` if using ngrok).
- **Firewall**: on Windows, allow Python when prompted the first time.
- **QR doesn't work** on mobile locally: Make sure you’re using the ngrok HTTPS URL as HOST.
- **Errors**: UI shows a red bar with the message from the JSON error.
- **Datetime**: uses ISO-8601 (UTC recommended).