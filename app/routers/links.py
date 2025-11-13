from fastapi import APIRouter, HTTPException, Response, Request
from typing import List, Any
from datetime import datetime
from ..models import LinkCreate, LinkUpdate, LinkOut
from .. import db
from ..services.qrcodes import make_qr_png
from ..services.codes import generate_unique_code
from ..utils import err
from ..db import NOCHANGE # special sentinel object meaning “don’t modify this field” (distinct from None, which might mean “explicitly clear”).
import os # Read environment variables (for BASE_URL).

router = APIRouter() # Instance of the router for attaching routes
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000") # Optional base URL for building short links outside a request context (not actually used below because we derive from request.base_url, but good to have as a fallback in other contexts).

# --- Convert the raw database dict into a structured LinkOut Pydantic model (leading underscore means “internal helper”). ---
def _to_link_out(rec: dict, base: str) -> LinkOut: # The rec parameter comes from the db queries that return dictionaries representing database rows
    short_url = f"{base}/{rec['short_code']}" # Build the public short URL from the base (scheme + host + port) plus the code.
    def parse_dt(x):
        if not x: 
            return None
        if isinstance(x, datetime): 
            return x
        try: 
            return datetime.fromisoformat(x)
        except Exception: 
            return None

    return LinkOut( # Same structure as links table
        short_code=rec["short_code"],
        target_url=rec["target_url"],
        short_url=short_url,
        created_at=parse_dt(rec.get("created_at")),
        expires_at=parse_dt(rec.get("expires_at")),
        click_count=rec.get("click_count", 0),  # default to 0 if missing
        last_access_at=parse_dt(rec.get("last_access_at")),
    )

# --- Handle HTTP requests ---
@router.post("", response_model=LinkOut, status_code=201)
def create_link(payload: LinkCreate, request: Request): # payload is a Pydantic model instance created by FastAPI from the request body (here, LinkCreate).
    # Pydantic already validated AnyUrl; extra guard (length, scheme) optional
    if len(str(payload.target_url)) > 500: # Extra sanity check (defense-in-depth) to reject absurdly long URLs.
        raise HTTPException(status_code=400, detail=err("VALIDATION_ERROR", "target_url too long", {"field": "target_url", "max": 500}))
    code = generate_unique_code(db.exists_code) # Generates a random code and retries on collision using db.exists_code as a verifier.
    rec = db.insert_link(code, str(payload.target_url), payload.expires_at) # return dict of inserted link details
    base = str(request.base_url).rstrip("/")
    return _to_link_out(rec, base) # format as Pydantic model

@router.get("", response_model=List[LinkOut]) # Array of LinkOut objects, GET /api/links
def list_all(request: Request):
    base = str(request.base_url).rstrip("/")
    rows = db.list_links()
    return [_to_link_out(r, base) for r in rows] # Return formatted output of every record

@router.get("/{code}", response_model=LinkOut) # Get specific short link details, GET /api/links/{code}
def detail(code: str, request: Request):
    rec = db.get_by_code(code)
    if not rec:
        raise HTTPException(status_code=404, detail=err("NOT_FOUND", "Short code not found", {"code": code}))
    base = str(request.base_url).rstrip("/")
    return _to_link_out(rec, base)

@router.put("/{code}", response_model=LinkOut) # Modify specific short link, PUT /api/links/{code}
def update(code: str, payload: LinkUpdate, request: Request): # Payload is the body a client sends to an update endpoint
    data: dict[str, Any] = payload.model_dump(exclude_unset=True)  # Pydantic v2, Convert Pydantic model to dict, excluding fields the client didn’t send
    target = data.get("target_url", NOCHANGE) # Use NOCHANGE sentinel for fields the client omitted. Distinguishes “leave as-is” from “set to null”.
    expires = data.get("expires_at", NOCHANGE) # .get() is a built-in dict method in Python

    rec = db.update_link(code, target, expires)  # pass sentinels
    if rec is None:
        raise HTTPException(status_code=404, detail=err("NOT_FOUND", "Short code not found", {"code": code}))

    base = str(request.base_url).rstrip("/")
    return _to_link_out(rec, base)

@router.delete("/{code}", status_code=204) # Remove a link, DELETE /api/links/{code}
def delete(code: str):
    ok = db.delete_link(code)
    if not ok:
        raise HTTPException(status_code=404, detail=err("NOT_FOUND", "Short code not found", {"code": code}))
    return Response(status_code=204) # 204 No Content on success

@router.get("/{code}/qr") # GET /api/links/{code}/qr → returns a PNG image of the QR for the short URL.
def qr_png(code: str, request: Request):
    rec = db.get_by_code(code)
    if not rec:
        raise HTTPException(status_code=404, detail=err("NOT_FOUND", "Short code not found", {"code": code}))
    base = str(request.base_url).rstrip("/")
    short_url = f"{base}/{rec['short_code']}"
    png = make_qr_png(short_url)
    return Response(content=png, media_type="image/png", headers={"Cache-Control": "public, max-age=86400"}) # Cache header allows public caching for 1 day (86400 seconds)—QRs are stable, so caching is safe & faster.

@router.get("/__debug_raw/{code}") # GET /api/links/__debug_raw/{code} → returns the raw DB dict (no shaping).
def debug_raw(code: str):
    return db.get_by_code(code)