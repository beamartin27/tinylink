from fastapi import APIRouter, HTTPException, Response
from starlette.responses import RedirectResponse
from datetime import datetime, timezone
from .. import db
from ..utils import err

router = APIRouter()

@router.get("/{code}")
def redirect(code: str):
    rec = db.get_by_code(code)
    if not rec:
        raise HTTPException(status_code=404, detail=err("NOT_FOUND", "Short code not found", {"code": code}))
    # expiry check
    if rec.get("expires_at"):
        exp = datetime.fromisoformat(rec["expires_at"])
        now = datetime.now(timezone.utc).astimezone(exp.tzinfo) if exp.tzinfo else datetime.now()
        if now > exp:
            raise HTTPException(status_code=410, detail=err("EXPIRED", "Link has expired", {"code": code, "expires_at": exp}))
    # analytics (optional)
    db.increment_click(code)
    db.update_last_access(code, datetime.now())
    return RedirectResponse(url=rec["target_url"], status_code=302)
