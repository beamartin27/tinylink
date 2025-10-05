# Architecture Overview

```mermaid
flowchart TD
  Browser[Browser / Client]
  subgraph Frontend
    Browser -->|GET /| WebServer[FastAPI static/templates]
    Browser -->|XHR /api/links| API[FastAPI API endpoints]
    WebServer --> Templates[app/templates/index.html]
    WebServer --> Static[app/static/css, js, images]
  end

  subgraph Backend
    API --> Routers["routers/\nlinks.py, redirect.py"]
    Routers --> Services["services/\ncodes.py, qrcodes.py"]
    Routers --> DB[DB layer: app/db.py]
    DB --> SQLite["app.db (SQLite)"]
    Routers --> Models["app/models.py (Pydantic)"]
  end

  Browser -->|clicks short_url| Redirect[GET /{short_code}]
  Redirect --> Routers
  Routers -->|persist/read| DB
  Services -->|helpers| Routers
  API -->|uses models| Models
```
