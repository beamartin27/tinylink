# TinyLink+ — Assignment 2 Refactor Plan

**Project:** TinyLink+  
**Student:** Bea  
**Context:** A1 delivered a working URL shortener, but with mixed concerns (SQL in routers, tight coupling to SQLite, no clear service layer).

---

## 1. Goals

- Apply SOLID principles (especially SRP & DIP).
- Separate concerns:
  - **Routers** = HTTP & JSON / HTML
  - **Services** = business rules
  - **Repositories** = persistence
- Centralize configuration (env-driven settings).
- Add metrics + health endpoint for observability.
- Make the app easier to test (unit, integration, E2E) and extend in A3+.

---

## 2. Problems in the original design

### app/db.py:
- Connection handling, schema, and CRUD in one module.
- Callers depended directly on SQLite + SQL strings → hard to swap DB or fake it in tests.

### Routers:
- Some business rules (validations, expiry logic, code generation) lived directly in router functions.

### Code generation:
- `services/codes.py` worked but was a bare function, not injectable strategy.

### Config & cross-cutting:
- Environment configuration was ad-hoc.
- No metrics or standard error envelope.

---

## 3. Scope of this refactor (A2 / Step 3)

### In scope:
- Introduce a `LinkRepository` protocol and a concrete `SqliteLinkRepository`.
- Introduce `LinkService` as the single entrypoint for link business logic.
- Refactor routers to use DI (`Depends(get_service)`) and stay I/O-only.
- Centralize settings with `Settings` / `get_settings`.
- Add Prometheus metrics middleware and `/metrics`.
- Keep existing API behavior (status codes, fields) so tests still describe reality.

### Out of scope (deferred):
- Changing the public HTTP API shape.
- Moving away from SQLite.
- Adding auth, rate limiting or complex logging.

---

## 4. Design and concrete changes

### 4.1 Persistence layer

**New repository interface:**
```python
# app/repositories/base.py
class LinkRepository(Protocol):
    def init_schema(self) -> None: ...
    def create(self, data: Dict[str, Any]) -> Dict[str, Any]: ...
    def get_by_code(self, code: str) -> Optional[Dict[str, Any]]: ...
    def get_by_id(self, link_id: int) -> Optional[Dict[str, Any]]: ...
    def list(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]: ...
    def update(self, link_id: int, data: Dict[str, Any]) -> Dict[str, Any]: ...
    def delete(self, link_id: int) -> None: ...
```

**New SQLite implementation:**

- `app/repositories/sqlite.py` implements `SqliteLinkRepository`.
- Responsible for:
  - Opening connections
  - Declaring / migrating schema (`init_schema`)
  - Mapping DB columns (`click_count`) ↔ service/API names (`clicks`, `click_count`).
- `app/db.py` is no longer used; legacy direct-SQL has been removed for A2.

### 4.2 Service layer

**New LinkService** (`app/services/link_service.py`):

- Depends on `LinkRepository` (DIP).
- Encapsulates rules:
  - Valid URLs must start with `http://` or `https://`.
  - Code generation using a code strategy.
  - Expiry check: expired links raise `PermissionError` → mapped to HTTP 410.
  - Updating clicks and `last_access_at` on resolve.
- Shapes outgoing records to what the API returns (`short_url`, `click_count`, parsed datetimes).
- Uses a `_NOCHANGE` sentinel to distinguish "don't touch this field" vs "set to null".

### 4.3 Code generation strategy

**Existing functions kept in** `app/services/codes.py`:
- `generate_code`
- `generate_unique_code(exists_fn, max_tries=...)`

**New Strategy wrapper in** `codes_strategy.py`:
- `CodeStrategy` interface with a `generate(exists_fn)` method.
- `RandomCodeStrategy` delegates to `codes.generate_unique_code(...)`.
- `LinkService` receives an optional `CodeStrategy` (dependency injection); defaults to `RandomCodeStrategy`.
- This keeps the generator testable on its own while making the strategy injectable in future (e.g. deterministic codes in tests).

### 4.4 API layer (routers)

**app/routers/links.py:**
- No SQL, no direct DB calls.
- All operations delegate to `LinkService` obtained via `Depends(get_service)`.
- Responsible for:
  - Mapping service exceptions → HTTP codes (400, 404).
  - Input/output shapes via Pydantic models (`LinkCreate`, `LinkUpdate`, `LinkOut`).
  - Returning QR PNG via `make_qr_png`.

**app/routers/redirect.py:**
- Thin controller over `LinkService.resolve`.
- Maps:
  - `KeyError` → 404
  - `PermissionError` → 410
- Returns `RedirectResponse` to `target_url`.

### 4.5 Settings & cross-cutting

**app/settings.py:**
- Single `Settings` class holding:
  - `app_env`
  - `db_path`
  - `base_url`
  - `enable_metrics`
- `get_settings()` is `@lru_cached` to avoid re-reading env vars.

**app/deps.py:**
- `get_repo()` builds `SqliteLinkRepository` from settings and calls `init_schema()`.
- `get_service()` builds `LinkService(repo, base_url=settings.base_url)`.

**app/metrics.py:**
- Prometheus Counter + Histogram.
- `MetricsMiddleware` measures latency and increments counters.
- `/metrics` endpoint returns the Prometheus exposition format.

**app/utils.py:**
- `err(...)` standardizes error envelopes.
- `_serialize(...)` makes sure datetimes and nested structures are JSON-friendly.

### 4.6 Models

**app/models.py** updated to match the new service shape, but still:
- `LinkCreate` / `LinkUpdate` for request bodies.
- `LinkOut` for responses.
- `ErrorOut` for uniform error structure.

---

## 5. Testing and coverage

Tests live under `tests/` and treat the app as an installed package (`from app.services import codes`, `from app.main import create_app`).

### Test types

- **Unit tests (`tests/unit/`):**
  - `test_codes_strategy.py`
    - Verifies `RandomCodeStrategy` respects `length` / `max_tries` and delegates to `codes.generate_unique_code`.
  - `test_link_service.py`
    - Uses a fake in-memory repo to test business rules of `LinkService`:
      - URL validation
      - Create/list/get/update/delete
      - Expiry logic (raises `PermissionError` when expired)
      - Click counting and `last_access_at` updates on `resolve()`.
- **Integration / API tests (`tests/integration/`):**
  - `test_links_api.py`
    - Uses a temporary SQLite DB (`tempfile.NamedTemporaryFile`) and `APP_DB_PATH`.
    - Builds the app via `create_app()` and drives it through `TestClient`.
    - Covers:
      - CRUD (T1–T4)
      - Redirect behavior and analytics (T5)
      - QR endpoint (T6)
      - Expired links returning HTTP 410 (T7).

### How tests bootstrap the DB

- `make_client_with_tmpdb()`:
  - Creates a temp SQLite file.
  - Sets `APP_DB_PATH` to point to it.
  - Calls `create_app()` so `SqliteLinkRepository.init_schema()` runs via DI.
  - Returns a `TestClient` bound to that app.

### CI / local command

```bash
python -m pytest -q --cov=app --cov-report=xml --cov-fail-under=70
```
---

## 6. Status & next steps

- **Step 3** (repositories + services + routers + metrics + settings) has been implemented and validated by tests.
- Legacy `app/db.py` has been removed; SQL logic is centralized in `SqliteLinkRepository`.
- **Step 4 (testing)**:
  - Unit tests for `CodeStrategy` and `LinkService` are in place.
  - Integration tests cover the FastAPI endpoints end-to-end.
  - Coverage gate (`--cov-fail-under=70`) is enforced and currently at ~91%.