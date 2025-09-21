# Low-Level Design (LLD) — TinyLink+

**Project:** TinyLink+  
**Student:** Bea  
**Date:** 20 Sep 2025

---

## 0. Purpose
Make implementation mechanical: define schema, DTOs, function contracts, endpoint behaviors, error shapes, and file layout.

---

## 1. Database Schema (authoritative SQL)

```sql
CREATE TABLE IF NOT EXISTS links (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  short_code TEXT NOT NULL UNIQUE,
  target_url TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  click_count INTEGER NOT NULL DEFAULT 0,          -- optional analytics
  last_access_at TEXT,                             -- optional analytics
  expires_at TEXT                                  -- optional expiry (ISO 8601)
);
CREATE INDEX IF NOT EXISTS idx_links_short_code ON links(short_code);
```

**Notes:**
- `created_at` / `last_access_at` stored as ISO-8601 text; simple for SQLite.
- `idx_links_short_code` enables fast redirect lookups.

## 2. Data Transfer Objects (Pydantic)

```python
# models.py
from pydantic import BaseModel, AnyUrl, Field
from typing import Optional
from datetime import datetime

class LinkCreate(BaseModel):
    target_url: AnyUrl
    expires_at: Optional[datetime] = None

class LinkUpdate(BaseModel):
    target_url: Optional[AnyUrl] = None
    expires_at: Optional[datetime] = None

class LinkOut(BaseModel):
    short_code: str = Field(min_length=6, max_length=8, pattern=r"^[A-Za-z0-9]+$")
    target_url: AnyUrl
    short_url: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    click_count: Optional[int] = 0
    last_access_at: Optional[datetime] = None

class ErrorOut(BaseModel):
    error: dict  # {"code": str, "message": str, "details": dict | None}
```

## 3. Persistence Layer (db.py) — Function Contracts

```python
# db.py
from typing import Optional, List, Tuple
from datetime import datetime

def init_db(db_path: str) -> None: ...
def get_by_code(code: str) -> Optional[dict]: ...
def list_links() -> List[dict]: ...
def insert_link(code: str, target_url: str, expires_at: Optional[datetime]) -> dict: ...
def update_link(code: str, target_url: Optional[str], expires_at: Optional[datetime]) -> Optional[dict]: ...
def delete_link(code: str) -> bool: ...
def exists_code(code: str) -> bool: ...
def increment_click(code: str) -> None: ...           # optional analytics
def update_last_access(code: str, dt: datetime) -> None: ...
```

Return shape for records (dict) aligns with LinkOut fields (except short_url, added at router level using BASE_URL).

## 4. Services

### 4.1 Short-code Generation (services/codes.py)

```python
import secrets, string

ALPHABET = string.ascii_letters + string.digits
LENGTH = 6  # can be 6–8

def generate_code(length: int = LENGTH) -> str:
    return ''.join(secrets.choice(ALPHABET) for _ in range(length))

def generate_unique_code(exists_fn, max_tries: int = 5) -> str:
    for _ in range(max_tries):
        code = generate_code()
        if not exists_fn(code):
            return code
    # fallback: increase length once
    return generate_code(length=LENGTH+1)
```

### 4.2 QR Generation (services/qrcodes.py)

```python
# returns raw PNG bytes for the given URL
def make_qr_png(url: str) -> bytes: ...
```

Response header: `Content-Type: image/png`.  
Consider `Cache-Control: public, max-age=86400`.

## 5. Endpoints — Detailed Contracts

### 5.1 POST /api/links (Create — FR1)
- **Request**: LinkCreate
- **Process**:
  1. Validate target_url (http(s)://, ≤ 500 chars).
  2. `code = generate_unique_code(db.exists_code)`
  3. `db.insert_link(code, target_url, expires_at)`
  4. Build `short_url = BASE_URL + "/" + code`
- **Response**: 201 Created, body LinkOut
- **Errors**: 400 (ErrorOut)

### 5.2 GET /api/links (List — FR2)
- **Process**: `db.list_links()` → map rows to LinkOut (with short_url).
- **Response**: 200 OK, List[LinkOut]

### 5.3 GET /api/links/{code} (Detail — FR2)
- **Process**: `db.get_by_code(code)` or 404.
- **Response**: 200 OK, LinkOut or 404 (ErrorOut)

### 5.4 PUT /api/links/{code} (Update — FR3)
- **Request**: LinkUpdate (at least one field present).
- **Process**: validate fields → `db.update_link` → 404 if missing.
- **Response**: 200 OK, LinkOut
- **Errors**: 400, 404 (ErrorOut)

### 5.5 DELETE /api/links/{code} (Delete — FR4)
- **Process**: `db.delete_link(code)` → True → 204 No Content else 404.
- **Response**: 204 No Content or 404 (ErrorOut)

### 5.6 GET /{code} (Redirect — FR5)
- **Process**:
  1. `link = db.get_by_code(code)` → if None: 404.
  2. If `link.expires_at` and `now() > expires_at`: 410.
  3. (Optional analytics) `db.increment_click(code)`; `db.update_last_access(code, now())`.
  4. 302 Found to target_url.
- **Response**: HTTP redirect; no body.
- **Errors**: 404, 410 (ErrorOut)

### 5.7 GET /api/links/{code}/qr (QR — FR6)
- **Process**:
  1. Load link or 404.
  2. Compute short URL → `make_qr_png(short_url)`.
  3. Return PNG bytes.
- **Response**: 200 OK with image/png
- **Errors**: 404 (ErrorOut)

## 6. Minimal UI (templates/index.html)
- **Form**: target_url (required), expires_at (optional ISO-8601).
- **Table**: Short URL (copy button), QR thumbnail (linked to PNG), Target URL (trimmed), Created, Clicks*, Expires, Actions (Edit/Delete).
- **Interaction**: Plain HTML + server rendering (no SPA).

*Clicks shown only if analytics enabled.

## 7. Error Handling (Uniform)
Payload uses ErrorOut.

**Mapping**:
- 400: validation / malformed body.
- 404: unknown short_code.
- 410: expired link on redirect.

**Examples**:
```json
{ "error": { "code": "NOT_FOUND", "message": "Short code not found", "details": {"code":"Ab3xYz"} } }
```

## 8. File Structure

```
tinylink/
  app/
    main.py              # FastAPI app factory, router registration
    db.py                # SQLite helpers + CRUD
    models.py            # Pydantic DTOs
    utils.py             # helper
    routers/
      links.py           # CRUD + QR
      redirect.py        # GET /{code}
    services/
      codes.py           # short-code gen
      qrcodes.py         # QR generation
    templates/
      index.html         # minimal UI
  tests/
    test_links.py        # T1–T6 (+ T7–T8 optional)
```

## 9. Pseudocode (core paths)

### Redirect
```python
def redirect(code: str):
    link = db.get_by_code(code)
    if not link:
        return JSON(404, err("NOT_FOUND", "Short code not found", {"code": code}))
    if link.expires_at and now() > link.expires_at:
        return JSON(410, err("EXPIRED", "Link has expired", {"code": code}))
    # optional analytics
    db.increment_click(code)
    db.update_last_access(code, now())
    return REDIRECT_302(link.target_url)
```

### Create
```python
def create_link(payload: LinkCreate):
    if not valid_url(payload.target_url):
        return JSON(400, err("VALIDATION_ERROR", "target_url must start with http(s)://", {"field": "target_url"}))
    code = generate_unique_code(db.exists_code)
    rec = db.insert_link(code, str(payload.target_url), payload.expires_at)
    return JSON(201, to_link_out(rec, base_url=BASE_URL))
```

## 10. Non-Functional Hooks (LLD specifics)
- **Performance**: Index on short_code; keep transactions short; avoid storing QR images.
- **Portability**: BASE_URL and DB_PATH env variables with defaults.
- **Security**: strict URL validation; consistent error messages; no user-controlled redirect target.
- **Headers**: image/png for QR; consider basic caching.

## 11. Test Mapping (from SRS)
- **T1 (FR1 - Create)**: valid/invalid create → 201/400
- **T2 (FR2 - List)**: create two → list has two
- **T3 (FR3 - Update)**: update target/expiry → returns updated
- **T4 (FR4 - Delete)**: delete then detail → 404
- **T5 (FR5 - Redirect)**: redirect existing → 302; unknown → 404; expired → 410
- **T6 (FR6 - QR)**: QR → 200 PNG; unknown → 404
- **T7 (FR7, opt)**: redirect increments click_count, sets last_access_at
- **T8 (FR8, opt)**: expired link → 410