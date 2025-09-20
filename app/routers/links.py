from fastapi import APIRouter, HTTPException, Response
from typing import List
from datetime import datetime, timezone
from ..models import LinkCreate, LinkUpdate, LinkOut
from .. import db
from ..services.qrcodes import make_qr_png
import os

router = APIRouter()

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

def _to_link_out(rec: dict) -> LinkOut:
    short_url = f"{BASE_URL}/{rec['short_code']}"
    return LinkOut(
        short_code=rec["short_code"],
        target_url=rec["target_url"],
        short_url=short_url,
        created_at=datetime.fromisoformat(rec["created_at"].replace("Z","")) if "Z" in rec["created_at"] else datetime.fromisoformat(rec["created_at"]),
        expires_at=datetime.fromisoformat(rec["expires_at"]) if rec.get("expires_at") else None,
        click_count=rec.get("click_count", 0),
        last_access_at=datetime.fromisoformat(rec["last_access_at"]) if rec.get("last_access_at") else None,
    )

@router.post("", response_model=LinkOut, status_code=201)
def create_link(payload: LinkCreate):
    # Pydantic already validated AnyUrl; extra guard (length, scheme) optional
    if len(str(payload.target_url)) > 500:
        raise HTTPException(status_code=400, detail={"error": {"code": "VALIDATION_ERROR","message": "target_url too long","details":{"field":"target_url"}}})
    code = __import__("..services.codes".replace("..","app")).services.codes.generate_unique_code(db.exists_code)
    rec = db.insert_link(code, str(payload.target_url), payload.expires_at)
    return _to_link_out(rec)

@router.get("", response_model=List[LinkOut])
def list_all():
    rows = db.list_links()
    return [_to_link_out(r) for r in rows]

@router.get("/{code}", response_model=LinkOut)
def detail(code: str):
    rec = db.get_by_code(code)
    if not rec:
        raise HTTPException(status_code=404, detail={"error":{"code":"NOT_FOUND","message":"Short code not found","details":{"code":code}}})
    return _to_link_out(rec)

@router.put("/{code}", response_model=LinkOut)
def update(code: str, payload: LinkUpdate):
    rec = db.update_link(code, str(payload.target_url) if payload.target_url else None, payload.expires_at)
    if rec is None:
        raise HTTPException(status_code=404, detail={"error":{"code":"NOT_FOUND","message":"Short code not found","details":{"code":code}}})
    return _to_link_out(rec)

@router.delete("/{code}", status_code=204)
def delete(code: str):
    ok = db.delete_link(code)
    if not ok:
        raise HTTPException(status_code=404, detail={"error":{"code":"NOT_FOUND","message":"Short code not found","details":{"code":code}}})
    return Response(status_code=204)

@router.get("/{code}/qr")
def qr_png(code: str):
    rec = db.get_by_code(code)
    if not rec:
        raise HTTPException(status_code=404, detail={"error":{"code":"NOT_FOUND","message":"Short code not found","details":{"code":code}}})
    short_url = f"{BASE_URL}/{rec['short_code']}"
    png = make_qr_png(short_url)
    return Response(content=png, media_type="image/png", headers={"Cache-Control": "public, max-age=86400"})