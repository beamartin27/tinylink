from fastapi import APIRouter, HTTPException, Response
from starlette.responses import RedirectResponse
from datetime import datetime, timezone
from .. import db
from ..utils import err

router = APIRouter()

from datetime import datetime, timezone

@router.get("/{code}")
def redirect(code: str):
    rec = db.get_by_code(code)
    if not rec:
        raise HTTPException(status_code=404, detail=err("NOT_FOUND","Short code not found",{"code":code}))

    exp_raw = rec.get("expires_at")
    if exp_raw:
        exp = datetime.fromisoformat(exp_raw)
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        if now > exp:
            raise HTTPException(status_code=410, detail=err("EXPIRED","Link has expired",{"code":code,"expires_at":exp.isoformat()}))

    db.increment_click(code)
    db.update_last_access(code, datetime.now(timezone.utc))
    return RedirectResponse(
    url=rec["target_url"],
    status_code=302,
    headers={"Cache-Control": "no-store"}
)