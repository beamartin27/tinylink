# app/settings.py
from functools import lru_cache
import os

class Settings:
    def __init__(self) -> None:
        self.app_env = os.getenv("APP_ENV", "dev")
        # Where the SQLite file lives (or :memory: for tests)
        self.db_path = os.getenv("APP_DB_PATH", "Rapp.db")
        # Public base URL to build short links (optional)
        self.base_url = os.getenv("APP_BASE_URL", "http://localhost:8000")
        # Metrics toggle (on by default)
        self.enable_metrics = os.getenv("APP_ENABLE_METRICS", "1") == "1"

@lru_cache
def get_settings() -> Settings:
    return Settings()
