# app/main.py
import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.exceptions import RequestValidationError

# Internal modules per LLD
from .db import init_db, DEFAULT_DB_PATH
from .routers import links, redirect
from .utils import err

# Config (env-overridable)
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
DB_PATH = Path(os.getenv("DB_PATH", str(DEFAULT_DB_PATH)))

# Templates (absolute path, so it works regardless of CWD)
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def create_app() -> FastAPI:
    app = FastAPI(title="TinyLink+")

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request, exc: RequestValidationError):
        return JSONResponse(status_code=400, content=err("VALIDATION_ERROR", "Invalid request body", {"errors": exc.errors()}))

    # Ensure DB schema is ready (links table + index)
    init_db(DB_PATH)

    # Mount API routers per HLD/LLD
    # /api/links[...]  (CRUD + QR)
    app.include_router(links.router, prefix="/api/links", tags=["links"])
    # /{code}          (redirect 302 + expiry/analytics)
    app.include_router(redirect.router, tags=["redirect"])

    # Healthcheck (kept from your previous file)
    @app.get("/health")
    def health():
        return {"status": "ok"}

    # Minimal UI (kept from your previous file)
    @app.get("/", response_class=HTMLResponse)
    def home(request: Request):
        # You can pass extra context if needed
        return templates.TemplateResponse("index.html", {"request": request, "msg": "TinyLink+ Ready"})

    return app


# ASGI entrypoint for uvicorn
app = create_app()
