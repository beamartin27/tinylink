# app/main.py
from pathlib import Path

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.exceptions import RequestValidationError

# Internal modules per HLD/LLD
from .db import init_db
from .routers import links, redirect
from .utils import err

# Templates (absolute path, so it works regardless of CWD)
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def create_app() -> FastAPI:
    """
    Factory that builds and returns the FastAPI app instance.
    Tests import and call this; production uses the global 'app' below.
    """
    app = FastAPI(title="TinyLink+")

    # --- Error handlers (uniform JSON envelope + no-cache headers) ---
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=400,
            content=err("VALIDATION_ERROR", "Invalid request body", {"errors": exc.errors()}),
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        content = exc.detail if isinstance(exc.detail, dict) else err("HTTP_ERROR", str(exc.detail))
        return JSONResponse(
            status_code=exc.status_code,
            content=content,
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )

    # --- DB schema (resolves APP_DB_PATH or defaults to app.db internally) ---
    init_db()

    # --- Routers ---
    app.include_router(links.router, prefix="/api/links", tags=["links"])
    app.include_router(redirect.router, tags=["redirect"])  # /{code}

    # --- Health & UI ---
    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/", response_class=HTMLResponse)
    def home(request: Request):
        return templates.TemplateResponse("index.html", {"request": request, "msg": "TinyLink+ Ready"})

    # >>> THIS MUST BE HERE <<<
    return app


# ASGI entrypoint for uvicorn (e.g., uvicorn app.main:app --reload)
app = create_app()
