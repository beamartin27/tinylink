from fastapi import APIRouter, Depends, HTTPException
from starlette.responses import RedirectResponse
from ..services.link_service import LinkService
from ..main import get_service
from ..utils import err

router = APIRouter() # instance of the router

@router.get("/{code}")
def go(code: str, svc: LinkService = Depends(get_service)):
    try:
        rec = svc.resolve(code)
        return RedirectResponse(rec["target_url"], status_code=302)
    except KeyError:
        raise HTTPException(status_code=404, detail=err("NOT_FOUND", "Short code not found"))
    except PermissionError:
        raise HTTPException(status_code=410, detail=err("EXPIRED", "Link expired"))
