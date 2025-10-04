from fastapi import APIRouter, HTTPException, Response
from starlette.responses import RedirectResponse
from datetime import datetime, timezone
from .. import db
from ..utils import err

router = APIRouter() # Instance of the router

@router.get("/{code}") # registers this function as the handler for GET /{code}.
def redirect(code: str):
    rec = db.get_by_code(code) # Query the DB for a record (row) by short code, receives dict
    if not rec:
        raise HTTPException(status_code=404, detail=err("NOT_FOUND","Short code not found",{"code":code}))

    exp_raw = rec.get("expires_at")
    if exp_raw:
        exp = datetime.fromisoformat(exp_raw) # Parse ISO 8601 into a datetime.
        if exp.tzinfo is None: # If the parsed datetime is naive (no timezone), force it to UTC.
            exp = exp.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        if now > exp: # Current time, explicitly timezone-aware (UTC). Perfect for safe comparisons.
            raise HTTPException(status_code=410, detail=err("EXPIRED","Link has expired",{"code":code,"expires_at":exp.isoformat()}))

    db.increment_click(code)
    db.update_last_access(code, datetime.now(timezone.utc))
    return RedirectResponse(url=rec["target_url"], status_code=302, headers={"Cache-Control": "no-store"}
)