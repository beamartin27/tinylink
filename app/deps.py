from .settings import get_settings
from .repositories.sqlite import SqliteLinkRepository
from .services.link_service import LinkService

def get_repo():
    settings = get_settings()
    repo = SqliteLinkRepository(settings.db_path)
    repo.init_schema()
    return repo

def get_service():
    settings = get_settings()
    repo = get_repo()
    return LinkService(repo, base_url=settings.base_url)
