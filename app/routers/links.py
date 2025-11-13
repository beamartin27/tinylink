from typing import List, Any
from fastapi import APIRouter, HTTPException, Request, Response, Depends
from ..models import LinkCreate, LinkUpdate, LinkOut
from ..utils import err
from ..services.link_service import LinkService, _NOCHANGE # special sentinel object meaning “don’t modify this field” (distinct from None, which might mean “explicitly clear”).
from ..main import get_service
from ..services.qrcodes import make_qr_png  # same as before

# Routers translate service exceptions to HTTP responses, this is the transformation layer following SRP
# Now it doesn't talk to sqlite, generate codes or parse dates

router = APIRouter() # Instance of the router for attaching routes

@router.post("", response_model=LinkOut, status_code=201)
def create_link(payload: LinkCreate, svc: LinkService = Depends(get_service)):
    try:
        rec = svc.create(target_url=str(payload.target_url), expires_at=payload.expires_at)
        return rec
    except ValueError as e:
        raise HTTPException(status_code=400, detail=err("VALIDATION_ERROR", str(e)))

@router.get("", response_model=List[LinkOut])
def list_all(svc: LinkService = Depends(get_service)):
    return svc.list()

@router.get("/{code}", response_model=LinkOut)
def detail(code: str, svc: LinkService = Depends(get_service)):
    try:
        return svc.get(code)
    except KeyError:
        raise HTTPException(status_code=404, detail=err("NOT_FOUND", "Short code not found", {"code": code}))

@router.put("/{code}", response_model=LinkOut)
def update(code: str, payload: LinkUpdate, svc: LinkService = Depends(get_service)):
    data: dict[str, Any] = payload.model_dump(exclude_unset=True)
    target = data.get("target_url", _NOCHANGE)
    expires = data.get("expires_at", _NOCHANGE)
    try:
        return svc.update(code, target_url_sentinel=target, expires_at_sentinel=expires)
    except KeyError:
        raise HTTPException(status_code=404, detail=err("NOT_FOUND", "Short code not found", {"code": code}))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=err("VALIDATION_ERROR", str(e)))

@router.delete("/{code}", status_code=204)
def delete(code: str, svc: LinkService = Depends(get_service)):
    try:
        svc.delete(code)
        return Response(status_code=204)
    except KeyError:
        raise HTTPException(status_code=404, detail=err("NOT_FOUND", "Short code not found", {"code": code}))

@router.get("/{code}/qr")
def qr_png(code: str, request: Request, svc: LinkService = Depends(get_service)):
    try:
        rec = svc.get(code)
    except KeyError:
        raise HTTPException(status_code=404, detail=err("NOT_FOUND", "Short code not found", {"code": code}))
    short_url = rec["short_url"]  # service already shaped it
    png = make_qr_png(short_url)
    return Response(content=png, media_type="image/png", headers={"Cache-Control": "public, max-age=86400"})