# TinyLink+ — Assignment 2 Refactor Report

**Project:** TinyLink+  
**Student:** Bea  

TinyLink+ started as a basic FastAPI URL shortener (Assignment 1). It worked, but mixed SQL, HTTP, and business logic in the same modules, had no clear service layer, and was hard to test or deploy cleanly.  

Assignment 2 refactors the codebase, adds tests and metrics, and wires a CI/CD pipeline that deploys to Azure App Service.

---

## 1. Goals and scope

**Main goals**

- Apply SOLID principles, especially:
  - *Single Responsibility*: each layer has one job.
  - *Dependency Inversion*: high-level logic depends on abstractions, not SQLite.
- Separate concerns:
  - **Routers** → HTTP, request/response, status codes.
  - **Services** → URL-shortening rules and business logic.
  - **Repositories** → persistence and SQL.
- Centralize configuration through environment variables.
- Add monitoring endpoints (`/health`, `/metrics`) for observability.
- Make the app easy to test (unit + integration) and easy to deploy (Docker + GitHub Actions + Azure).

**Original issues (very short)**

- `app/db.py` mixed connection management, schema and CRUD and was imported everywhere.
- Routers contained validation rules, expiry logic and code generation directly.
- Code generation was a standalone function, not easily injectable or replaceable.
- No metrics, no health endpoint, and configuration was scattered.

**Scope of A2**

- Introduce a repository abstraction and a service layer.
- Refactor routers to depend on services via FastAPI's `Depends`.
- Add centralized settings, metrics middleware and `/health`.
- Add tests with a coverage gate.
- Package the app into a Docker image.
- Add CI/CD workflows: one for tests/build, one for deployment to Azure App Service.

---

## 2. Architecture improvements

### 2.1 Persistence: `LinkRepository` and `SqliteLinkRepository`

The persistence layer was redesigned around a **repository abstraction**:

- `LinkRepository` protocol defines operations such as `create`, `get_by_code`, `update`, `delete`, and `list`.
- `SqliteLinkRepository` implements this contract using SQLite and SQL statements.
- It is responsible for:
  - Opening connections and creating the schema (`init_schema`).
  - Translating between DB column names and domain fields (e.g. `click_count` vs `clicks`).

Impacts:

- All direct SQL code is now confined to `app/repositories/sqlite.py`.
- Higher-level components depend on the `LinkRepository` interface, so switching storage (or faking it in tests) is straightforward.
- Schema initialization is called once through a dependency (`get_repo`), instead of being scattered.

### 2.2 Service layer: `LinkService` and code strategy

The business logic for short links lives in **`LinkService`**:

- Depends on a `LinkRepository` and a `CodeStrategy` (Dependency Inversion).
- Responsibilities:
  - Validate target URLs (must start with `http://` or `https://`).
  - Generate unique short codes using a strategy object (`RandomCodeStrategy`).
  - Apply expiry rules: expired links raise `PermissionError` and should return HTTP 410.
  - Resolve a code:
    - Look up the link.
    - Update click count and `last_access_at`.
    - Return the resolved target URL.
  - Convert raw DB rows into domain dictionaries with:
    - `short_url` = `base_url + "/" + short_code`.
    - Normalized `click_count`.
    - Datetimes parsed from strings.

A small `CodeStrategy` interface and `RandomCodeStrategy` implementation wrap the existing code generator, but make it injectable (e.g. for deterministic codes in tests or different patterns in the future).

Result: business rules are centralized, testable, and independent of FastAPI or SQLite.

### 2.3 API layer: routers and dependency injection

The FastAPI routers were rewritten to be **thin HTTP adapters**:

- `app/routers/links.py`:
  - Now injects `LinkService` via `Depends(get_service)`.
  - Handles:
    - Request models (`LinkCreate`, `LinkUpdate`).
    - Response models (`LinkOut`).
    - HTTP-level concerns such as status codes, error mapping and returning a QR PNG.
  - Maps service exceptions to HTTP errors:
    - `KeyError` → 404 (not found).
    - `PermissionError` → 410 (expired).
    - `ValueError` / validation errors → 400.

- `app/routers/redirect.py`:
  - Exposes `GET /{code}` to resolve and redirect.
  - Delegates to `LinkService.resolve`.
  - Returns `RedirectResponse` or the appropriate error status.

No router knows anything about SQLite or SQL. They only talk to a service object and to FastAPI's request/response types.

### 2.4 Settings, error handling and health

Global configuration is centralized in `app/settings.py`:

- `Settings` reads:
  - `APP_ENV` (default `"dev"`).
  - `APP_DB_PATH` (default `"app.db"`).
  - `APP_BASE_URL` (default `"http://localhost:8000"`).
- `get_settings()` is cached so env vars are read once.
- `app/deps.py` uses these settings to create:
  - The concrete repository (`SqliteLinkRepository(settings.db_path)`).
  - The service (`LinkService(repo, base_url=settings.base_url)`).

Cross-cutting concerns:

- Error handling:
  - A helper `err(code, message, details)` builds a standard JSON envelope under the `"error"` key.
  - Global exception handlers for `RequestValidationError` (400) and `HTTPException` ensure consistent responses.
- Health:
  - `GET /health` returns `{"status": "ok"}` and is used by deployment and monitoring checks.

This makes configuration, error formats and health checks predictable in all environments (local, Docker, Azure).

---

## 3. Monitoring and Prometheus metrics

Observability is provided via **Prometheus-compatible metrics** defined in `app/metrics.py`:

- Middleware `MetricsMiddleware` wraps every request and:
  - Measures latency.
  - Increments a counter labelled by HTTP method, route and status code.
- A `/metrics` endpoint serializes all metrics in Prometheus' text format (`generate_latest()`).

Prometheus is configured (locally) with the example file `docs/prometheus.example.yml` to scrape:

- `http://localhost:8000/metrics` when running locally.
- From there we can graph `http_requests_total` and latency histograms.

Screenshots stored in `docs/prometheus_targets.png` and `docs/prometheus_query.png` show:

- The TinyLink+ target appearing as **UP** in Prometheus.
- A non-empty graph of `http_requests_total` after creating and using links.

Together with `/health`, this gives a minimal but complete monitoring story for the assignment.

---

## 4. Testing and quality gates

Tests live under `tests/` and treat TinyLink+ as a package (`from app.main import create_app`, `from app.services.link_service import LinkService`, etc.).

**Unit tests (`tests/unit/`):**

- Use fake in-memory repositories to test `LinkService` in isolation:
  - Valid and invalid URL creation.
  - Code generation using `RandomCodeStrategy`.
  - Expiry rules (expired links raise `PermissionError`).
  - Click counting on `resolve`.
- Test the code strategy wrapper (`RandomCodeStrategy`) independently from the rest of the app.

**Integration tests (`tests/integration/`):**

- Use a temporary SQLite database and `APP_DB_PATH` to exercise the real stack:
  - Create, list, update and delete links via the API.
  - Resolve a code and follow the redirect.
  - Verify QR PNG bytes.
  - Confirm expired links return HTTP 410.

A helper:

1. Creates a temp SQLite file.
2. Sets `APP_DB_PATH` to that file.
3. Calls `create_app()`, which triggers schema creation via the repository.

**Quality gate:**

The standard command (locally and in CI) is:
```bash
python -m pytest -q --cov=app --cov-report=xml --cov-fail-under=70
```

At submission time, coverage is around 91%, comfortably above the 70% gate.

---

## 5. Containerization and CI/CD pipeline

### 5.1 Docker image

The project includes a single-stage Dockerfile that:

- Uses `python:3.12-slim` as base image.
- Copies `requirements.txt` and installs dependencies with `pip install --no-cache-dir`.
- Copies the application code into `/app`.
- Creates a non-root user (`appuser`) and runs the app as that user.
- Exposes port 8000.
- Starts the app with:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Environment variables (`APP_DB_PATH`, `APP_BASE_URL`) still control DB location and the base URL inside the container, exactly as in local development.

### 5.2 GitHub Actions CI/CD

Two workflows are used:

**Main CI workflow (tests & Docker build)**

Triggered on pushes/PRs to master. Jobs:

- **Lint**: `ruff check .` (fails on style errors such as unused variables).
- **Tests + coverage**: runs the pytest command with the `--cov-fail-under=70` gate.
- **Docker build**: builds the TinyLink+ image (and can push it to a registry like GHCR).

**Azure deployment workflow**

File: `.github/workflows/master_bea-tinylink-app.yml` (generated through Azure's Deployment Center and slightly edited).

- **build job**:
  - Checks out the repo.
  - Sets up Python 3.12.
  - Creates a small virtualenv and installs dependencies.
  - Uploads the application files as an artifact.

- **deploy job**:
  - Downloads the artifact.
  - Logs into Azure using OIDC and a user-assigned managed identity.
  - Deploys the code to the `bea-tinylink-app` Web App in the student subscription.

The result is a fully automated pipeline:

**git push → CI (lint + tests + coverage + Docker build) → Azure workflow → deployed TinyLink+.**

---

## 6. Azure App Service deployment

TinyLink+ is deployed on Azure App Service (Linux).

**Resources:**

- Resource Group in West Europe (provided by the course).
- Web App: `bea-tinylink-app`.
- App Service Plan: small B1 tier.

**Key configuration (App Settings in Azure):**

- `APP_DB_PATH = /home/site/wwwroot/app.db`  
  → Location of the SQLite file in Azure. This folder is writable, so the app creates the DB on first run.

- `APP_BASE_URL = https://bea-tinylink-app-…azurewebsites.net`  
  → Used by `LinkService` to build the `short_url` field.

Because the DB is created fresh at `/home/site/wwwroot/app.db`, the Azure deployment starts with no links in the table; this is expected and acceptable. It also means local development data is not accidentally shipped to production.

After a successful deployment the following checks were performed against the live URL:

- `GET /` → UI loads and allows creating links.
- `GET /docs` → FastAPI Swagger UI available.
- `GET /health` → `{"status": "ok"}`.
- `GET /metrics` → Prometheus metrics text.
- New short URLs redirect correctly, and expired links return HTTP 410.

---

## 7. Conclusion and future work

Assignment 2 turns TinyLink+ from a monolithic, SQLite-dependent script into a small but clean service:

- Architecture split into repositories, services and routers.
- Centralized settings and consistent error handling.
- Metrics and health endpoints suitable for monitoring.
- Tests with a coverage gate, packaged in a Docker image.
- Automated CI + CD ending in a working Azure deployment.

**Possible future improvements:**

- Structured logging (JSON logs with correlation IDs).
- Enable/disable metrics via `APP_ENABLE_METRICS` in production.
- Add authentication and/or rate limiting.
- Use an external DB (e.g. Azure SQL) behind the same `LinkRepository` interface.