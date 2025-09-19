# TinyLink+ — Phase 1: Planning

**Project:** TinyLink+ (minimal URL shortener with QR & basic analytics)  
**Student:** Bea  
**SDLC Model:** Waterfall (with a small prototype checkpoint and early test planning)  
**Date:** 19 Sep 2025  

---

## 1. Objectives

Build a tiny, reliable app that:

- Shortens a long URL into a short code.  
- Redirects visitors and increments a click counter.  
- Shows a QR code for the short URL.  
- (Extra Feature) Expiry date disables redirects after a set time.  

---

## 2. Scope

**In scope (MVP):**

- CRUD for links (Create, Read/List, Update, Delete).  
- Persistent storage using SQLite (single file).  
- REST endpoints + a minimal single-page UI (form + table).  
- Redirect endpoint (`/{code}`) that updates analytics.  
- QR code generation endpoint/utility.  

**Out of scope (reserved for Assignment 2 or future possibilities):**

- Authentication / multi-user accounts.  
- Custom domains, HTTPS certificates, or external DBs.  
- Advanced analytics dashboards or rate limiting.  
- Full CI/CD pipeline, cloud deploy, Postgres migration.  

---

## 3. Stakeholders

- **Developer:** Bea (builds and documents).  
- **Instructor/Marker:** Validates features, SDLC artifacts, and code quality.  
- **Demonstration User:** Uses the minimal UI to create and test links.  

---

## 4. Assumptions & Constraints

**Assumptions**  
- Runs locally; no internet-only dependencies.  
- Single user; no login required.  
- Python 3.11+ available on the target machine.  

**Constraints**  
- Keep implementation small and readable (simple modules, short functions).  
- SQLite only; no migration tooling required in this assignment.  
- Deliverables must match Waterfall artifacts.  

---

## 5. Feasibility Summary

- **Technical:** Python + FastAPI + SQLite are lightweight and proven → Feasible.  
- **Operational:** One command (or Docker) to run locally in class → Feasible.  
- **Economic:** No cost (local dev; open-source libs) → Feasible.  

---

## 6. High-Level Requirements (headlines — full details go in SRS)

- **FR1:** Create short link from a valid URL.  
- **FR2:** List all links.  
- **FR3:** Update target URL and/or expiry.  
- **FR4:** Delete a link.  
- **FR5:** Redirect by short code; increment click count; block if expired (410).  
- **FR6:** Generate/serve QR image for a short code.  

- **NFR1:** Simple, fast responses locally (CRUD ≤ 300 ms typical).  
- **NFR2:** Input validation & proper error codes (400/404/410).  
- **NFR3:** Readable code (consistent naming, docstrings for endpoints).  
- **NFR4:** Easy setup (clear README; later, Dockerfile).  

*(SRS in Phase 2 will formalize these with acceptance criteria.)*  

---

## 7. SMART Goals & Milestones

- **By Sun 21 Sep 2025:** Finish SRS (requirements & acceptance criteria).  
- **By Tue 23 Sep 2025:** Finish Design (HLD/LLD + architecture diagram).  
- **By Fri 26 Sep 2025:** Implement CRUD + SQLite.  
- **By Mon 29 Sep 2025:** Implement Redirect + click count and tests.  
- **By Thu 2 Oct 2025:** Implement QR + minimal UI; write README (setup); add Dockerfile.  
- **By Sat 4 Oct 2025:** Finalize report, polish, and submit.  

---

## 8. Risk Register

| ID  | Risk                  | Likelihood | Impact | Mitigation                                                   | Contingency                                     | Owner |
|-----|-----------------------|------------|--------|---------------------------------------------------------------|-------------------------------------------------|-------|
| R1  | Time overrun          | Medium     | High   | Lock MVP (CRUD→Redirect→QR). Daily 1-hour cap per task.       | Drop expiry if needed; keep QR.                 | Bea   |
| R2  | DB hiccups / file locks | Low       | Medium | Use SQLite with simple schema; close connections properly.    | Restart app; replace DB file if corrupted.      | Bea   |
| R3  | Over-promising features | Medium    | High   | Keep “Out of scope” list explicit; no new features mid-build. | Move extras to Assignment 2 backlog.            | Bea   |
| R4  | Tests too late        | Medium     | Medium | Plan tests in Phase 2 (traceability FR↔Tests).               | Write minimal tests first (create→redirect).    | Bea   |
| R5  | UI complexity creeps in | Medium    | Medium | One HTML template; small table; no SPA.                      | Ship without fancy styling if time tight.       | Bea   |

---

## 9. High-Level Schedule (Waterfall)

- **Planning (this doc)** — 19 Sep  
- **Requirements (SRS)** — due 21 Sep  
- **Design (HLD/LLD + diagram)** — due 23 Sep  
- **Development** — 23 Sep to 2 Oct  
- **Testing** — 29 Sep to 2 Oct (planned early, executed during Dev)  
- **Deployment (local + Docker)** — due 2 Oct  
- **Operations & Maintenance note + Report** — due 4 Oct  

---

## 10. Success Criteria (for grading & self-check)

- All **FR1–FR6** work and are demonstrable via UI or API.  
- **README** lets a classmate run it without help.  
- Tests cover the happy path for create→redirect (+ expiry case).  
- Report includes SDLC justification, diagram, and DevOps reflection.  
- Clean Git history (≥ 3 meaningful commits).  

---

## 11. Change Control

- Any new idea goes to a **Backlog** for Assignment 2 (Postgres, auth, rate limiting, CI/CD, etc.).  
- No scope additions to MVP unless something else is removed with equal effort.  

---

## 12. Communication & Version Control

- **Commit after each phase artifact and each feature milestone.**  

**Sample commit messages:**

- `docs(planning): add goals, scope, feasibility, risks, schedule`  
- `docs(srs): add FR/NFR and acceptance criteria`  
- `feat(api): CRUD for links`  
- `feat(redirect): add redirect with click count`  
- `feat(qr): add QR endpoint and UI`  
- `test: add unit/integration tests`  
