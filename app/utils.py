# app/utils.py
from typing import Any, Dict, Optional
from datetime import datetime

def _serialize(obj: Any) -> Any: # “datetime-safe” formatter
    if isinstance(obj, datetime): # If the object is a datetime, convert it to a string in ISO 8601 format
        return obj.isoformat()
    if isinstance(obj, dict): # If the object is a dict, recursively serialize its values.
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)): # If the object is a list or tuple, recursively serialize every element.
        return [_serialize(x) for x in obj]
    return obj # If none of the above, return it as-is.

def err(code: str, message: str, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]: # standardized error envelope for your API.
    return {"error": {"code": code, "message": message, "details": _serialize(details) if details else None}}
