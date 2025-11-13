# TinyLink+ Refactor Plan (A2)

## Goals
- Enforce SOLID (SRP/DIP), remove code smells, improve testability.
- Separate concerns: routers (I/O), services (business), repositories (persistence).
- Centralize config & logging. Add metrics & health.

## Findings
- **app/db.py**: schema + connection + CRUD together → extract a `LinkRepository` interface + `SqliteLinkRepository`.
- **Routers**: some business logic lives in routers → move into `LinkService`.
- **services/codes.py**: code generation OK; formalize Strategy/Factory.
- **Config**: ensure DB path, base URL, etc., come from env → `settings.py`.
- **Errors/logging**: unify error mapping, add structured logging later.
- **Tests**: split into unit (services with fake repo), integration (sqlite repo), minimal E2E.

## Priorities (order)
1) Repository interface + SQLite adapter
2) LinkService + thin routers
3) Env-driven settings + logging
4) Metrics middleware + /metrics
5) Tests layout (unit/integration/E2E), coverage ≥70%
