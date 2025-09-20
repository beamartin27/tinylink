# High-Level Design (HLD) — TinyLink+

**Project:** TinyLink+  
**Student:** Bea  
**Date:** 20 Sep 2025  
**Scope:** Minimal URL shortener with CRUD, redirect, SQLite persistence, and QR generation (plus optional expiry & click analytics).

---

## 0. Purpose & Alignment
This HLD translates the SRS into a concrete architecture and module boundaries so implementation is mechanical. It stays within the MVP defined in PLANNING and maps directly to FR1–FR6 (FR7–FR8 optional).  
- SRS: FR1–FR6 (+ FR7/FR8 optional) ✅  
- SDLC: Waterfall with small prototype/checkpoints ✅

---

## 1. Architecture Overview

TinyLink+ is a **client–server** web app:
- **Frontend**: Minimal HTML (Jinja2) for form + table.  
- **Backend**: FastAPI service exposing REST + one redirect route.  
- **Storage**: SQLite file `app.db`.  
- **QR Service**: On-demand generation of PNG from short URL.

### 1.1 Context Diagram (ASCII)

```
+-----------+ HTTP (UI & REST) +-------------------+ SQLite I/O +----------+
| Browser   | <----------------------> | FastAPI App       | <----------------> | SQLite   |
| (User/UI) |                         | (Routers/Services) |                    | app.db   |
+-----------+                         +-------------------+                    +----------+
      |                                         ^ ^
      | GET /{code} (302 redirect)              | |
      |-----------------------------------------+ |
      |                                           |
      | GET /api/links/{code}/qr (PNG)           |
      +-------------------------------------------+
```

### 1.2 Key Flows
- **Create**: UI/POST → validate → generate unique code → insert → return short URL.  
- **Redirect**: GET `/{code}` → load → (check expiry) → (increment analytics) → **302** to target.  
- **QR**: GET `/api/links/{code}/qr` → generate PNG with the short URL → return image.

---

## 2. Modules & Responsibilities

- **Routers**
  - `routers/links.py`: REST CRUD for links + QR endpoint (FR1–FR4, FR6).
  - `routers/redirect.py`: `GET /{code}` redirect (FR5) and optional analytics/expiry checks.
- **Services**
  - `services/codes.py`: short-code generation (6–8 chars, alnum) with collision retry.
  - `services/qrcodes.py`: QR PNG generation from the short URL.
- **Persistence**
  - `app/db.py`: connection helpers + queries (get/insert/update/delete).
- **Models**
  - `app/models.py`: Pydantic DTOs for requests/responses.
- **Templates**
  - `templates/index.html`: single page with form + table.

---

## 3. Conceptual Data Model
**Entity: Link**
- `id` (int, PK)  
- `short_code` (text, unique)  
- `target_url` (text)  
- `created_at` (timestamp, default now)  
- `click_count` (int, default 0) *(optional)*  
- `last_access_at` (timestamp) *(optional)*  
- `expires_at` (timestamp) *(optional)*

Rationale: sufficient for CRUD, redirect, QR, and optional analytics/expiry with a single index on `short_code`.

---

## 4. Public Interfaces (API)
| Method | Path                         | Purpose                         | Request (JSON)                                  | Response | Status Codes |
|-------:|------------------------------|---------------------------------|--------------------------------------------------|----------|--------------|
| POST   | `/api/links`                 | Create short link (FR1)         | `{ "target_url": str, "expires_at": str? }`     | Link     | **201**, 400 |
| GET    | `/api/links`                 | List links (FR2)                | —                                                | [Link]   | **200**      |
| GET    | `/api/links/{code}`          | Get link detail (FR2)           | —                                                | Link     | **200**, 404 |
| PUT    | `/api/links/{code}`          | Update link (FR3)               | `{ "target_url": str?, "expires_at": str? }`    | Link     | **200**, 400, 404 |
| DELETE | `/api/links/{code}`          | Delete link (FR4)               | —                                                | —        | **204**, 404 |
| GET    | `/{code}`                    | Redirect (FR5)                  | —                                                | —        | **302**, 404, 410* |
| GET    | `/api/links/{code}/qr`       | QR image (FR6)                  | —                                                | PNG      | **200**, 404 |

*410 only when expiry is enabled for that link.

All JSON responses share a consistent error shape on failures (see §6).

---

## 5. Design Decisions
- **FastAPI + SQLite**: minimal deps, easy to run; fits single-user demo.  
- **One template**: keeps UI effort tiny; all features demoable.  
- **Single table**: avoids premature complexity; indexed by `short_code`.  
- **PNG QR on demand**: no storage of images needed; cache allowed at client.

---

## 6. Security, Validation & Error Model
- **Validation**: `target_url` must start with `http://` or `https://` and length ≤ 500.  
- **Open-redirect prevention**: we only redirect to the stored `target_url` (no user-controlled next param).  
- **Error JSON** (example):
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "target_url must start with http(s)://",
    "details": {"field": "target_url"}
  }
}
```

- **Status codes**: 400 invalid input; 404 not found; 410 expired; 201 created; 204 no content.
- **Headers**: QR responses include `Content-Type: image/png`; can add `Cache-Control: public, max-age=86400`.

## 7. Performance & Reliability (NFR hooks)
- CRUD typical ≤ **500 ms** locally; QR typical ≤ **1.5 s** on first render.
- SQLite with **index on** `short_code` ensures O(log n) lookups.
- Short-lived DB connections; basic retries on code collision.

## 8. Deployment & Ops
- Local run via `uvicorn app.main:app --reload`.
- Optional `Dockerfile` for Assignment 2.
- Config via env vars (e.g., `BASE_URL`, `DB_PATH`) with sensible defaults.

## 9. Testing Strategy (High level)
- **Unit**: code generator, validators.
- **Integration**: CRUD lifecycle, redirect, QR endpoint.
- **Acceptance**: FR1–FR6 happy paths + negative cases; optional FR7–FR8.

## 10. Traceability (SRS ↔ HLD)
- FR1–FR6 mapped to table in §4; data model in §3; flows in §1.2.
- FR7–FR8 (optional) addressed by fields `click_count`, `last_access_at`, `expires_at`.