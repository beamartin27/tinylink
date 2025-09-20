from pydantic import BaseModel, AnyUrl, Field
from typing import Optional, Dict, Any
from datetime import datetime

class LinkCreate(BaseModel):
    target_url: AnyUrl
    expires_at: Optional[datetime] = None

class LinkUpdate(BaseModel):
    target_url: Optional[AnyUrl] = None
    expires_at: Optional[datetime] = None

class LinkOut(BaseModel):
    short_code: str = Field(min_length=6, max_length=8, pattern=r"^[A-Za-z0-9]+$")
    target_url: AnyUrl
    short_url: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    click_count: Optional[int] = 0
    last_access_at: Optional[datetime] = None

class ErrorOut(BaseModel):
    error: Dict[str, Any]
