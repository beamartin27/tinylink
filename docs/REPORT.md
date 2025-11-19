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
- Make the app easier to test (**unit + integration**).

---

## 2. Problems in the original design

### app/db.py

- Connection handling, schema, and CRUD all in one module.
- Callers depended directly on SQLite + SQL strings → hard to swap DB or fake it in tests.

### Routers

- Some business rules (validations, expiry logic, code generation) lived directly in router functions instead of a service layer.

### Code generation

- `services/codes.py` worked but was a bare function, not an injectable strategy.

### Config & cross-cutting

- Environment configuration was ad-hoc.
- No metrics or standard error envelope.

---

## 3. Scope of this refactor (Assignment 2)

### In scope (what A2 actually changes)

- Introduce a `LinkRepository` protocol and a concrete `SqliteLinkRepository`.
- Introduce `LinkService` as the single entrypoint for link business logic.
- Refactor routers to use DI (`Depends(get_service)`) and stay I/O-only.
- Centralize settings with `Settings` / `get_settings`.
- Add Prometheus metrics middleware and `/metrics`.
- Add structured tests (unit + integration) with a coverage gate.
- Keep existing API behavior (status codes, fields) so tests still describe reality.

### Out of scope (deferred for future iterations)

- Changing the public HTTP API shape.
- Moving away from SQLite.
- Adding auth, rate limiting or advanced/structured logging.
- A full CI/CD pipeline (GitHub Actions) and real deployment target.

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
  - Opening connections.
  - Declaring / migrating schema (`init_schema`).
  - Mapping DB columns (`click_count`) ↔ service/API names (`clicks`, `click_count`).
- Legacy `app/db.py` has been removed in A2; all direct SQL lives in the repository.

### 4.2 Service layer

**New LinkService** (`app/services/link_service.py`):

- Depends on `LinkRepository` (DIP).
- Encapsulates rules:
  - Valid URLs must start with `http://` or `https://`.
  - Code generation using an injected code strategy.
  - Expiry check: expired links raise `PermissionError` → mapped to HTTP 410 by the router.
  - Updating clicks and `last_access_at` on resolve.
- Shapes outgoing records to what the API returns:
  - `short_url` built from `base_url` + `short_code`
  - `click_count` (normalized from the repo's `clicks`)
  - Datetimes parsed from ISO strings into `datetime` objects.
- Uses a `_NOCHANGE` sentinel to distinguish "don't touch this field" vs "set to null".

### 4.3 Code generation strategy

**Existing functions kept in** `app/services/codes.py`:
- `generate_code`
- `generate_unique_code(exists_fn, *, max_tries=..., length=...)`

**New strategy wrapper in** `codes_strategy.py`:
- `CodeStrategy` interface with a `generate(exists_fn)` method.
- `RandomCodeStrategy`:
  - Holds `length` and `max_tries` as configuration.
  - Delegates to `codes.generate_unique_code(...)` under the hood.
- `LinkService` receives an optional `CodeStrategy` (dependency injection); defaults to `RandomCodeStrategy`.
- This keeps the low-level generator testable on its own while making the strategy injectable in future (e.g. deterministic codes in tests, custom patterns).

### 4.4 API layer (routers)

**app/routers/links.py:**
- Contains no SQL and never touches SQLite directly.
- All operations delegate to `LinkService`, obtained via `Depends(get_service)`.
- Responsibilities:
  - Mapping service exceptions → HTTP codes (400, 404).
  - Input/output shapes via Pydantic models (`LinkCreate`, `LinkUpdate`, `LinkOut`).
  - Returning QR PNG via `make_qr_png`.

**app/routers/redirect.py:**
- Thin controller over `LinkService.resolve`.
- Maps:
  - `KeyError` → 404 (short code not found)
  - `PermissionError` → 410 (expired)
- Returns `RedirectResponse` to `target_url`.

Routers now follow SRP: they handle HTTP concerns only and delegate business logic to the service.

### 4.5 Settings & cross-cutting

**app/settings.py:**
- Single `Settings` class holding:
  - `app_env` (from `APP_ENV`, default `"dev"`)
  - `db_path` (from `APP_DB_PATH`, default `"app.db"`)
  - `base_url` (from `APP_BASE_URL`, default `"http://localhost:8000"`)
  - `enable_metrics` (from `APP_ENABLE_METRICS`, `"1"` → enabled by default)
- `get_settings()` is `@lru_cached` to avoid re-reading env vars.

**app/deps.py:**
- `get_repo()`:
  - Builds `SqliteLinkRepository(settings.db_path)` and calls `init_schema()` once per process.
- `get_service()`:
  - Builds `LinkService(repo, base_url=settings.base_url)`.

**app/metrics.py:**
- Prometheus Counter + Histogram.
- `MetricsMiddleware` measures latency and increments counters for each request.
- `/metrics` endpoint returns the Prometheus exposition format (only when metrics are enabled via settings).

**app/utils.py:**
- `err(...)` standardizes error envelopes.
- `_serialize(...)` ensures datetimes and nested structures are JSON-friendly.

### 4.6 Models

**app/models.py:**
- Still defines:
  - `LinkCreate` / `LinkUpdate` for request bodies.
  - `LinkOut` for responses.
  - `ErrorOut` for uniform error structure.
- Types are aligned with what `LinkService._shape` returns (including parsed datetimes and `click_count`).

---

## 5. Testing and coverage (summary)

A detailed test report is provided in `docs/TEST_REPORT.md`. It covers test types, layout, traceability to FR1–FR6, and coverage statistics.

In summary:

- Tests live under `tests/` and treat the app as an installed package (`from app.services import codes`, `from app.main import create_app`).
- **Unit tests** (`tests/unit/`):
  - `test_codes_strategy.py` checks `RandomCodeStrategy` (length/max_tries and delegation to `codes.generate_unique_code`).
  - `test_link_service.py` uses a fake in-memory repository to test `LinkService` business rules (validation, CRUD, expiry, click counting).
- **Integration tests** (`tests/integration/`):
  - `test_links_api.py` uses a temporary SQLite DB (via `APP_DB_PATH`) and drives the FastAPI app with `TestClient`.
  - Scenarios T1–T7 cover CRUD, redirect, analytics, QR PNG, and expired links returning HTTP 410.

Database bootstrapping for integration tests is done via a helper that:

1. Creates a temp SQLite file.
2. Sets `APP_DB_PATH`.
3. Calls `create_app()`, causing `SqliteLinkRepository.init_schema()` to run via DI.

The standard command (used locally and in CI) is:

```bash
python -m pytest -q --cov=app --cov-report=xml --cov-fail-under=70
```
At submission time, coverage is approximately 91%, above the required 70% threshold.

---

## 6. Containerization (Step 5)

### 6.1 Docker image

To support reproducible runtime environments and future deployment, the app is containerized with a single-stage Dockerfile:

- **Base image**: `python:3.12-slim`.
- **Security**:
  - Non-root user (`appuser`) created and used for the final CMD.
  - Only port `8000` exposed.
- **Dependencies**:
  - `requirements.txt` copied and installed with `pip install --no-cache-dir -r requirements.txt`.
- **App layout in container**:
  - Code under `/app/app`.
  - Default SQLite DB at `/app/app.db` (overridable via env through `APP_DB_PATH`).
- **Runtime command**:
  - `CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]`.

The exact build/run commands are documented in README.md under "Run with Docker".

### 6.2 Configuration in containers

Runtime configuration for containers is done via environment variables:

- `APP_DB_PATH` – path to the SQLite file inside the container.
- `APP_BASE_URL` – public base URL (e.g. your ngrok URL or deployed domain).
- `APP_ENABLE_METRICS` – toggle for the Prometheus metrics endpoint.

These map directly into the `Settings` class (`app/settings.py`), so the same logic is used locally and in Docker.

### 6.3 CI/CD (planned, not implemented yet)

For this assignment, tests and coverage are run locally using the command above. A natural next step (not yet committed in this repo) would be to add a GitHub Actions workflow that:

**On push / PR:**
- Installs dependencies.
- Runs `ruff check .`.
- Runs the pytest + coverage command with a `--cov-fail-under=70` gate.

**On successful CI:**
- Builds the Docker image.
- Optionally pushes to a registry (e.g. GHCR: `ghcr.io/<username>/tinylink:${{ github.sha }}`).
- Optionally triggers a deploy to a target (Render/Fly/VM).

This is left explicitly as future work to keep the scope of A2 focused on refactoring, testing, and containerization.

---

## 7. Observability & Documentation (Step 6)

### 7.1 Metrics

Observability is provided via **Prometheus-compatible metrics**:

- `app/metrics.py` defines:
  - `REQUEST_COUNT` – Counter labelled by HTTP method, route, and status.
  - `REQUEST_LATENCY` – Histogram labelled by HTTP method and route.
- `MetricsMiddleware`:
  - Wraps every request, measures latency, and updates metrics.
  - Uses `request.scope["route"].path` when available, otherwise falls back to `request.url.path`.
- `/metrics` endpoint:
  - Exposed only when `settings.enable_metrics` is `True`.
  - Returns the Prometheus exposition format via `generate_latest()`.

This allows a Prometheus server (or similar) to scrape metrics and build dashboards (e.g. request rate, latency percentiles, error ratios).

> A minimal Prometheus scrape configuration is provided in `docs/prometheus.example.yml`, so the app can be monitored locally or in the cloud. (Screenshot in `docs/`.)

### 7.2 Health endpoint

The health endpoint is kept simple and documented:

- `GET /health` → `{"status": "ok"}`

This can be wired into uptime checks (load balancers, monitoring tools, etc.) and is sufficient for the assignment.

### 7.3 Uniform error handling

Error handling is centralized to give a consistent JSON envelope:

- `app/utils.py::err(code, message, details)` builds:
```json
  {
    "error": {
      "code": "VALIDATION_ERROR",
      "message": "Invalid request body",
      "details": { }
    }
  }
```

Two exception handlers in `app.main`:

- `RequestValidationError` → HTTP 400 with a validation error envelope.
- `HTTPException` → uses `exc.detail` if it's already a dict, or wraps it into `err("HTTP_ERROR", ...)`.

Routers never handcraft ad-hoc JSON error shapes; they either raise `HTTPException` with a structured detail or let the global handlers wrap things.

### 7.4 Documentation updates

The following documentation has been updated to reflect the new architecture and tooling:

**README.md:**
- Updated project structure (repositories, services, settings, metrics).
- Clear instructions for:
  - Local run with and without ngrok.
  - Docker build/run.
  - API usage via curl.
  - Test and coverage commands (pytest + `--cov`).
  - Linting (`ruff check .`).
  - Manual test plan (end-to-end UX checks).

**Refactor plan (this document):**
- Maps original smells → concrete changes (before/after).
- Documents the introduction of:
  - `LinkRepository` + `SqliteLinkRepository`
  - `LinkService` and the code generation strategy
  - Dependency injection for routers and settings
  - Metrics middleware and `/metrics`
  - Testing layout and coverage gate.

---

## 8. Future improvements (beyond A2)

- Add structured logging (e.g. JSON logs, request IDs).
- Implement the GitHub Actions workflow described in §6.3.
- Add more granular metrics (DB timings, per-endpoint error counters).