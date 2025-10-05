```mermaid
classDiagram
  class Link {
    +int id
    +string short_code
    +string short_url
    +string target_url
    +int click_count
    +datetime last_access_at
    +datetime created_at
    +datetime expires_at
  }

  class LinkCreate {
    +string target_url
    +string expires_at
  }

  class LinkUpdate {
    +string target_url
    +string expires_at
  }

  class LinkOut {
    +string short_code
    +string target_url
    +string short_url
    +datetime created_at
    +datetime expires_at
    +int click_count
    +datetime last_access_at
  }

  class DB {
    +init_db()
    +list_links()
    +get_by_code(code)
    +insert_link(code, target_url, expires_at)
    +update_link(short_code, target_url=NOCHANGE, expires_at=NOCHANGE)
    +delete_link(code)
    +exists_code(code)
    +increment_click(code)
    +update_last_access(code, dt)
  }

  class CodesService {
    +generate_code()
    +generate_unique_code(exists_fn)
  }

  class QRService {
    +make_qr_png(url)
  }

  class RoutersLinks {
    +create_link(payload: LinkCreate)   // POST /api/links
    +list_all(request)                  // GET /api/links
    +detail(code)                       // GET /api/links/{code}
    +update(code, payload: LinkUpdate)  // PUT /api/links/{code}
    +delete(code)                       // DELETE /api/links/{code}
    +qr_png(code)                       // GET /api/links/{code}/qr
  }

  class RoutersRedirect {
  +redirect(code)               // GET /{code}
  }

  DB --> Link
  RoutersLinks --> DB
  RoutersLinks --> CodesService
  RoutersLinks --> QRService
  RoutersRedirect --> DB
  Link <|-- LinkCreate
  Link <|-- LinkUpdate
  LinkOut <-- DB
```
