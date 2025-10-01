# Operations & Maintenance (O&M) — TinyLink+

TinyLink+ — operations, monitoring, and continuous improvement notes.

---

## 1. Current Ops Baseline

- **Runtime**: FastAPI on Uvicorn.
- **DB**: SQLite file `app.db` (single-node, lightweight; good for coursework/dev).
- **Health**: `GET /health` → `{"status":"ok"}`.
- **Error model**: JSON envelope with code/message/details; UI shows error bar.
- **Container**: `docker build -t tinylink:latest .` then `docker run -p 8000:8000 …`.

---

## 2. Monitoring & Observability (minimum viable)

### 2.1 Logs

- **App logs**: Uvicorn access + error logs.
- Run with structured-ish logs & info level:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level info
```

- **Rotation (hosted)**: use OS log rotation or Docker log driver limits, e.g.:

```bash
docker run \
  --log-driver json-file \
  --log-opt max-size=10m \
  --log-opt max-file=3 \
  -p 8000:8000 tinylink:latest
```

### 2.2 Health / Uptime

- **Health endpoint**: `/health` (already implemented) for smoke probes.
- **External ping**: if exposed via ngrok, add an uptime check (e.g., UptimeRobot) every 1–5 min:
  - Expect HTTP 200
  - Retry & alert (email) on >2 consecutive failures.

### 2.3 Basic metrics (Assignment 2 hook)

- **Counters** to add later: total redirects, 410 expired responses, create/update/delete counts.
- **Plan**: expose `/metrics` (Prometheus format) in Assignment 2.

---

## 3. Routine Maintenance

### 3.1 SQLite backup/restore

**Backup (cold, safest)**:

```bash
# stop app or ensure no writes
cp app.db backup/app-$(date +%Y%m%d-%H%M%S).db
```

**Backup (hot, using sqlite3 shell)**:

```bash
sqlite3 app.db ".backup 'backup/app-$(date +%Y%m%d-%H%M%S).db'"
```

**Restore**:

```bash
cp backup/app-YYYYmmdd-HHMMSS.db app.db
```

### 3.2 Vacuum/Integrity (occasionally)

```bash
sqlite3 app.db "PRAGMA integrity_check; VACUUM;"
```

### 3.3 Schema change policy

- Keep **idempotent** `CREATE TABLE IF NOT EXISTS` in `init_db`.
- For real migrations later: adopt Alembic (when moving to Postgres in Assignment 2).

---

## 4. Security & Config

- **Dependencies**: keep `requirements.txt` updated; periodically run `pip list --outdated`.
- **Container scan**: (Assignment 2) e.g. `docker scout quickview` or Trivy.
- **Secrets**: none stored; if later needed, use env vars (never commit).
- **CORS**: not required for same-origin UI; lock down if exposing API cross-domain.
- **Headers**: add `Cache-Control: no-store` on error JSON (already done for handlers).

---

## 5. Performance & Capacity

- **Startup**: FastAPI + SQLite is lightweight.
- **Hot paths**: `/redirect` read + two quick updates (clicks, last_access_at).
- **DB locks**: SQLite is fine for low concurrency; for heavier load move to **Postgres** (planned).
- **HTTP tuning**: keep default Uvicorn workers=1 for dev; scale to more workers behind a reverse proxy if needed (Assignment 2).

---

## 6. Reliability / Ops Playbooks

- **Service won't start**: check port conflict; run with `--port 8001`. Verify Python deps / `jinja2`.
- **DB is locked**: pause traffic, retry, or restart; back up and vacuum. Consider moving to Postgres.
- **QR not working on phones**: confirm you're using the **ngrok HTTPS** URL (public).
- **Expired link edited but still 410**: hard-refresh UI; verify `/api/links/<code>` shows new `expires_at`. (Fixed logic; regression tests cover edit-after-expire).

---

## 7. Continuous Improvement Backlog (Assignment 2)

- **Rate limiting** (protect redirect and POST endpoints).
- **Custom aliases** (user-chosen short codes; validate collisions).
- **CSV export** of links + stats.
- **Postgres** backend + Alembic migrations.
- **CI/CD**: GitHub Actions (lint, tests, build image, optionally push).
- **Container scan** & dependency audit.
- **Metrics endpoint** `/metrics` + dashboard (e.g., Prometheus + Grafana).
- **E2E tests** (Playwright) for UI flows.