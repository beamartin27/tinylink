from fastapi import APIRouter, HTTPException, Response
from starlette.responses import RedirectResponse
from datetime import datetime, timezone
from .. import db

router = APIRouter()

@router.get("/{code}")
def redirect(code: str):
    rec = db.get_by_code(code)
    if not rec:
        raise HTTPException(status_code=404, detail={"error":{"code":"NOT_FOUND","message":"Short code not found","details":{"code":code}}})
    # expiry check
    if rec.get("expires_at"):
        exp = datetime.fromisoformat(rec["expires_at"])
        now = datetime.now(timezone.utc).astimezone(exp.tzinfo) if exp.tzinfo else datetime.now()
        if now > exp:
            raise HTTPException(status_code=410, detail={"error":{"code":"EXPIRED","message":"Link has expired","details":{"code":code}}})
    # analytics (optional)
    db.increment_click(code)
    db.update_last_access(code, datetime.now())
    return RedirectResponse(url=rec["target_url"], status_code=302)
