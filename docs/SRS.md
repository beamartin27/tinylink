# Software Requirements Specification (SRS)

**Project:** TinyLink+  
**Student:** Bea  
**Date:** 19 Sep 2025  
**SDLC Model:** Waterfall (with PoC checkpoint and early test planning)  

---

## 1. Introduction

TinyLink+ is a minimal URL shortener that converts long URLs into short codes, provides QR codes, and tracks basic analytics such as click count.  
This SRS defines the **functional and non-functional requirements**, the **acceptance criteria**, and the **traceability** between requirements and test cases.  

---

## 2. Functional Requirements (FR)

- **FR1: Create short link**  
  The system must allow a user to submit a valid URL and generate a unique short code.  

- **FR2: List links**  
  The system must display all stored links with their details (original URL, short code, click count, expiry date, QR).  

- **FR3: Update link**  
  The system must allow editing an existing link’s target URL and/or expiry date.  

- **FR4: Delete link**  
  The system must allow deleting an existing link by its short code.  

- **FR5: Redirect**  
  Accessing a short code must redirect to the target URL

- **FR6: QR code generation**  
  The system must generate and serve a QR code image for each short link.  

**Optional** (Only if time permits):

- **FR7: Click analytics** 
  On redirect, increment a click counter and store last_access_at.

- **FR8: Expiry** 
  If a link has an expiry date and it’s past, return HTTP 410 (Gone) instead of redirecting.

---

## 3. Non-Functional Requirements (NFR)

- **NFR1: Performance** — CRUD requests should typically complete under 500 ms on a local dev machine; QR generation should typically complete under 1.5 s. 
- **NFR2: Reliability** — Redirects must function consistently as long as the database file is intact.  
- **NFR3: Usability** — A simple HTML page must allow users to create and view links without technical knowledge.  
- **NFR4: Maintainability** — Code must be modular, with clear naming, comments for complex parts, and ≤150 lines per file where practical.  
- **NFR5: Portability** — The system must run on any machine with Python 3.11+ or via Docker.  
- **NFR6: Security** — The system must validate inputs (URLs must begin with http:// or https://, max length 500 chars).  

---

## 4. Acceptance Criteria (per FR)

**FR1 (Create)**  
- Given a valid URL, when submitted, then a short code is returned.  
- Given an invalid URL, when submitted, then an error (HTTP 400) is returned.  

**FR2 (List)**  
- Given stored links, when requested, then a list with all details is returned.  
- If no links exist, an empty list is returned.  

**FR3 (Update)**  
- Given a stored link, when updated, then new values replace the old ones.  
- Invalid updates (e.g., empty URL) return an error.  

**FR4 (Delete)**  
- Given a stored link, when deleted, then it no longer appears in the list.  
- Deleting a non-existent short code returns a 404 error.  

**FR5 (Redirect)** 
- Given a valid short code, when accessed, then the system returns a 302/307 redirect to the target URL.
- Given an unknown short code, return 404.

**FR6 (QR)**  
- Given a stored short code, when QR is requested, then an image is generated and displayed.  
- Invalid/non-existent code returns 404.  

**Optional** (Only if time permits):

**FR7 (Click Analytics)**
- Each access increments `click_count` and updates `last_access_at`.  

**FR8 (Expiry)** 
- If the link has expired, the system returns HTTP 410 Gone.  

---

## 5. Traceability Matrix (FR ↔ Tests)

| Requirement   | Test ID | Planned Test Case                                |
|---------------|---------|--------------------------------------------------|
| FR1 Create    | T1      | Submit valid/invalid URL → short code / error    |
| FR2 List      | T2      | Create 2 links → list returns both               |
| FR3 Update    | T3      | Update link target → new target works            |
| FR4 Delete    | T4      | Delete link → 404 on redirect                    |
| FR5 Redirect  | T5      | Accessing valid short code redirects; unknown code → 404 |
| FR6 QR        | T6      | Request QR → valid PNG image; invalid code → 404 |
| FR7 Analytics *(optional)* | T7 | Redirect increments click counter, updates last access |
| FR8 Expiry *(optional)*    | T8 | Expired link returns HTTP 410 (Gone) instead of redirect |


*(Full tests will be written in Phase 5, but this sets the mapping now.)*  

---

## 6. Glossary

- **Short code:** unique 6–8 character identifier for a link.  
- **QR code:** image encoding the short URL.  
- **Expiry date:** timestamp after which a link is no longer valid.  
