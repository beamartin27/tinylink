from fastapi import APIRouter, HTTPException, Response, Request
from typing import List, Any
from datetime import datetime, timezone
from ..models import LinkCreate, LinkUpdate, LinkOut
from .. import db
from ..services.qrcodes import make_qr_png
from ..services.codes import generate_unique_code
from ..utils import err
from ..db import NOCHANGE
import os

router = APIRouter()

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

def _to_link_out(rec: dict, base: str) -> LinkOut:
    short_url = f"{base}/{rec['short_code']}"
    def parse_dt(x):
        if not x: return None
        if isinstance(x, datetime): return x
        try: return datetime.fromisoformat(x)
        except Exception: return None

    return LinkOut(
        short_code=rec["short_code"],
        target_url=rec["target_url"],
        short_url=short_url,
        created_at=parse_dt(rec.get("created_at")),
        expires_at=parse_dt(rec.get("expires_at")),
        click_count=rec.get("click_count", 0),
        last_access_at=parse_dt(rec.get("last_access_at")),
    )

@router.post("", response_model=LinkOut, status_code=201)
def create_link(payload: LinkCreate, request: Request):
    # Pydantic already validated AnyUrl; extra guard (length, scheme) optional
    if len(str(payload.target_url)) > 500:
        raise HTTPException(status_code=400, detail=err("VALIDATION_ERROR", "target_url too long", {"field": "target_url", "max": 500}))
    code = generate_unique_code(db.exists_code)
    rec = db.insert_link(code, str(payload.target_url), payload.expires_at)
    base = str(request.base_url).rstrip("/")
    return _to_link_out(rec, base)

@router.get("", response_model=List[LinkOut])
def list_all(request: Request):
    base = str(request.base_url).rstrip("/")
    rows = db.list_links()
    return [_to_link_out(r, base) for r in rows]

@router.get("/{code}", response_model=LinkOut)
def detail(code: str, request: Request):
    rec = db.get_by_code(code)
    if not rec:
        raise HTTPException(status_code=404, detail=err("NOT_FOUND", "Short code not found", {"code": code}))
    base = str(request.base_url).rstrip("/")
    return _to_link_out(rec, base)

@router.put("/{code}", response_model=LinkOut)
def update(code: str, payload: LinkUpdate, request: Request):
    data: dict[str, Any] = payload.model_dump(exclude_unset=True)  # Pydantic v2
    target = data.get("target_url", NOCHANGE)
    expires = data.get("expires_at", NOCHANGE)

    rec = db.update_link(code, target, expires)  # pass sentinels
    if rec is None:
        raise HTTPException(status_code=404, detail=err("NOT_FOUND", "Short code not found", {"code": code}))

    base = str(request.base_url).rstrip("/")
    return _to_link_out(rec, base)

@router.delete("/{code}", status_code=204)
def delete(code: str):
    ok = db.delete_link(code)
    if not ok:
        raise HTTPException(status_code=404, detail=err("NOT_FOUND", "Short code not found", {"code": code}))
    return Response(status_code=204)

@router.get("/{code}/qr")
def qr_png(code: str, request: Request):
    rec = db.get_by_code(code)
    if not rec:
        raise HTTPException(status_code=404, detail=err("NOT_FOUND", "Short code not found", {"code": code}))
    base = str(request.base_url).rstrip("/")
    short_url = f"{base}/{rec['short_code']}"
    png = make_qr_png(short_url)
    return Response(content=png, media_type="image/png", headers={"Cache-Control": "public, max-age=86400"})

@router.get("/__debug_raw/{code}")
def debug_raw(code: str):
    rec = db.get_by_code(code)
    return rec or {}