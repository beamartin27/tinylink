from pydantic import BaseModel, AnyUrl, Field
from typing import Optional, Dict, Any
from datetime import datetime

# classes which inherit from BaseModel and define fields as annotated attributes.
class LinkCreate(BaseModel): # schema for POST body
    target_url: AnyUrl
    expires_at: Optional[datetime] = None

class LinkUpdate(BaseModel): # schema for PUT body (partial updates, optional fields).
    target_url: Optional[AnyUrl] = None
    expires_at: Optional[datetime] = None

class LinkOut(BaseModel): # schema for responses (what the API returns).
    short_code: str = Field(min_length=6, max_length=8, pattern=r"^[A-Za-z0-9]+$")
    target_url: AnyUrl
    short_url: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    click_count: Optional[int] = 0
    last_access_at: Optional[datetime] = None

class ErrorOut(BaseModel): # schema for errors
    error: Dict[str, Any]
