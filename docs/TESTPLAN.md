# TESTPLAN — TinyLink+

## Objective
Verify that TinyLink+ meets FR1–FR6 (SRS) and that critical flows work after changes (basic regression).

## Scope
- Unit: short-code generator and validations.
- Integration: CRUD API + redirect + QR on FastAPI with temporary SQLite.
- Acceptance (manual): verify in UI that FR1–FR6 operations work end-to-end.

## Traceability Matrix
| SRS | Feature | Test ID | Type |
|-----|---------|---------|------|
| FR1 | Create link                 | T1 | Integration |
| FR2 | List + Detail               | T2 | Integration |
| FR3 | Update (target/expiry)      | T3 | Integration |
| FR4 | Delete                      | T4 | Integration |
| FR5 | Redirect (+clicks)          | T5 | Integration |
| FR6 | QR PNG                      | T6 | Integration |
| —   | Expired → 410               | T7 | Integration |
| —   | Code generator collision    | U1 | Unit |
| —   | Invalid body → 400          | U2 | Unit/Integration |

## Data
- Temporary SQLite DB per test (file in tmp).
- `BASE_URL` does not affect test logic (TestClient uses `http://testserver`).

## Acceptance Criteria
- All tests T1–T7 and U1–U2 green.
- Evidence: screenshot of `pytest` in green.

## Regression
- Re-run the suite after substantial changes (A2: CI pipeline).