# Architecture Overview

```mermaid
flowchart LR
  subgraph Client["Browser / CLI"]
    UI["/ (index.html)"]
    cURL["cURL / HTTP clients"]
  end

  UI -->|Fetch JSON| LinksAPI["FastAPI /api/links (router)"]
  cURL --> LinksAPI
  Client -->|GET /{code}| Redirect["FastAPI /{code} (router)"]

  subgraph App["TinyLink+ (FastAPI)"]
    LinksAPI --> Services["Services: codes.py, qrcodes.py"]
    Redirect --> DB["SQLite (app.db)"]
    LinksAPI --> DB
  end

  Services --> DB
