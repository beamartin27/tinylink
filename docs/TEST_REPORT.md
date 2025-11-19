# TEST_REPORT — TinyLink+

## 1. Objective

Verify that TinyLink+ meets the functional requirements (FR1–FR6 from the SRS) and that critical flows keep working after refactors, with:

- Unit tests for business logic and code generation.
- Integration tests for the FastAPI API + SQLite.
- A coverage gate of **≥ 70%** (actual coverage ≈ **91%** at submission).

---

## 2. Scope

- **Unit**  
  - `RandomCodeStrategy` and low-level code generation behavior.
  - `LinkService` business rules with a fake in-memory repository.
- **Integration (API)**  
  - CRUD endpoints, redirect logic, expiry, and QR PNG on a temporary SQLite DB.
- **Manual acceptance**  
  - UI-level checks (create, edit, delete, redirect, QR, expiry) via the browser.

---

## 3. Test layout & tooling

- Tests live under `tests/` and treat the app as an installed package:
  - `from app.services import codes`
  - `from app.main import create_app`
- Structure:
  - `tests/unit/`
  - `tests/integration/`
- Tools:
  - `pytest`, `pytest-cov`
  - `fastapi.testclient.TestClient`

---

## 4. Test types

### 4.1 Unit tests (`tests/unit/`)

**`test_codes_strategy.py`**

- Verifies that `RandomCodeStrategy`:
  - Respects the configured `length` and `max_tries`.
  - Delegates correctly to `codes.generate_unique_code(...)`.

**`test_link_service.py`**

- Uses a simple fake in-memory repository to isolate `LinkService` from SQLite.
- Covers business rules:
  - **URL validation**: invalid targets are rejected.
  - **Create / list / get / update / delete**:
    - Data round-trips correctly via the service.
  - **Expiry logic**:
    - Expired links cause `PermissionError` on `resolve()`, which routers map to HTTP 410.
  - **Click counting and last access**:
    - `resolve(code)` increments `click_count` and sets `last_access_at`.

These tests exercise the core domain logic **without** touching the database or HTTP.

---

### 4.2 Integration / API tests (`tests/integration/`)

**`test_links_api.py`**

- Uses a temporary SQLite DB (`tempfile.NamedTemporaryFile`) and the `APP_DB_PATH` environment variable.
- Builds the app via `create_app()` and drives it with `TestClient`.
- Covers the main flows:

| ID | Scenario                                  | What it checks                                                |
|----|-------------------------------------------|----------------------------------------------------------------|
| T1 | Create + invalid body                     | 201 on valid create, 400/422 on invalid JSON/body             |
| T2 | List + detail                             | Newly created links appear in list and are retrievable by code|
| T3 | Update target and expiry (set + clear)    | Target URL changes, expiry can be set and then cleared (null) |
| T4 | Delete → 404 on detail                    | DELETE returns 204; subsequent GET by code returns 404        |
| T5 | Redirect increments clicks                | GET `/{code}` → 302; click count increments; last_access set  |
| T6 | QR PNG endpoint                           | `/api/links/{code}/qr` returns `200` with `image/png` body    |
| T7 | Expired link returns HTTP 410 (Gone)      | Expired link → GET `/{code}` returns 410                      |

These integration tests exercise the full FastAPI stack (routers + service + repository + SQLite) **in-process**, which is essentially end-to-end for the API layer.

---

## 5. How tests bootstrap the DB

**Helper: `make_client_with_tmpdb()`**

- Creates a temporary SQLite file with `NamedTemporaryFile`.
- Sets `APP_DB_PATH` to point to that file.
- Calls `create_app()`, so `SqliteLinkRepository.init_schema()` runs through DI.
- Returns a `TestClient` bound to that app instance.

No test ever touches the real application database (`app.db` on disk).

---

## 6. Coverage and CI

### 6.1 Coverage command

Recommended local (and used in CI):

```bash
python -m pytest -q --cov=app --cov-report=xml --cov-fail-under=70
