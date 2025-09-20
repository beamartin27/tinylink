def err(code: str, message: str, details=None):
    return {"error": {"code": code, "message": message, "details": details}}
