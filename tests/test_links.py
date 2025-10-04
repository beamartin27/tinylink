# tests/test_links.py
import os, tempfile, json, shutil
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

# Importa la app y el db del paquete
from app.main import create_app
import app.db as db
from app.services import codes

def norm(u: str) -> str: # "https://example.com" and "https://example.com/" compare equal in assertions.
    # accept optional trailing slash normalization
    return u.rstrip("/")


def make_client_with_tmpdb(): # Generate clients for the tests with temp db
    tmpdb = tempfile.NamedTemporaryFile(delete=False) # Creates a real file on disk for SQLite
    tmpdb.close()
    os.environ["APP_DB_PATH"] = tmpdb.name  # Sets APP_DB_PATH before importing/creating the app so _default_db_path() uses this temp DB.

    from app.main import create_app  # import now, picks up APP_DB_PATH
    app = create_app()
    from app import db
    db.init_db()  # against tmp DB,create the schema in that file.

    client = TestClient(app, follow_redirects=False) # Returns a TestClient bound to this app + the path to the temp DB.
    return client, tmpdb.name

def iso_utc(dt: datetime) -> str: # Normalizes any datetime to UTC ISO 8601 string. Good for consistent expiry values.
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()

# ---------- Unit ----------

def test_code_generator_collision():
    calls = {"n": 0}
    def fake_exists(code: str) -> bool:
        calls["n"] += 1
        # colisiona las dos primeras veces, tercera libre
        return calls["n"] < 3 # simulate 3 collissions (True)
    code = codes.generate_unique_code(fake_exists, max_tries=5)
    assert isinstance(code, str) and len(code) >= 6 # check conditions for success
    assert calls["n"] == 3

# ---------- Integration CRUD ----------

def test_T1_create_and_invalid_body():
    client, _ = make_client_with_tmpdb()

    # valid
    res = client.post("/api/links", json={"target_url": "https://example.com"})
    assert res.status_code == 201, res.text # Creates a link: expect 201 and a JSON body including short_code and normalized target_url.
    body = res.json()
    assert body["short_code"]
    assert norm(body["target_url"]) == "https://example.com"


    # invalid (bad URL) -> 400 (handler of RequestValidationError)
    res2 = client.post("/api/links", json={"target_url": "notaurl"})
    assert res2.status_code in (400, 422)  # depending on your exception handler you might get 400 (custom) or 422 (FastAPI default). The test accepts either.
    if res2.status_code == 400: # If 400, it checks you return your uniform error envelope (err(...) shape).
        err = res2.json()
        assert "error" in err or "detail" in err

def test_T2_list_and_detail():
    client, _ = make_client_with_tmpdb()
    a = client.post("/api/links", json={"target_url": "https://a.example"}).json()
    b = client.post("/api/links", json={"target_url": "https://b.example"}).json()

    lst = client.get("/api/links").json()
    codes = {r["short_code"] for r in lst}
    assert a["short_code"] in codes and b["short_code"] in codes # Check links were saved successfully

    det = client.get(f"/api/links/{a['short_code']}")
    assert det.status_code == 200 # Request has succeeded
    assert det.json()["short_code"] == a["short_code"] # Fetches detail and verifies it matches.

def test_T3_update_target_and_expiry_and_clear():
    client, _ = make_client_with_tmpdb()
    c = client.post("/api/links", json={"target_url": "https://old.example"}).json()
    code = c["short_code"]

    # update target and expiry
    exp = iso_utc(datetime.now(timezone.utc) + timedelta(days=1)) # modify expiry date
    up = client.put(f"/api/links/{code}", json={ 
        "target_url": "https://new.example",
        "expires_at": exp
    }) # update expiry data
    assert up.status_code == 200, up.text # up.text: If the assertion fails, pytest will print up.text (the response body) in the error message.
    j = up.json() # save the updated json
    assert norm(j["target_url"]) == "https://new.example" # check it's updated
    assert j["expires_at"] # asserts that expires_at is truthy (not None, not empty).

    # delete expiry (null)
    up2 = client.put(f"/api/links/{code}", json={"expires_at": None})
    assert up2.status_code == 200
    assert up2.json()["expires_at"] is None

def test_T4_delete_then_404_detail():
    client, _ = make_client_with_tmpdb()
    c = client.post("/api/links", json={"target_url": "https://x.example"}).json()
    code = c["short_code"]

    assert client.delete(f"/api/links/{code}").status_code == 204
    assert client.get(f"/api/links/{code}").status_code == 404 # Not found

def test_T5_redirect_increments_clicks():
    client, _ = make_client_with_tmpdb()
    c = client.post("/api/links", json={"target_url": "https://example.com"}).json()
    code = c["short_code"]

    r = client.get(f"/{code}")
    assert r.status_code == 302 # Redirection response
    assert r.headers["Location"].startswith("https://example.com") # Confirm redirection

    det = client.get(f"/api/links/{code}").json()
    assert det["click_count"] >= 1 # Check click_count incremented
    assert det["last_access_at"] is not None # Check there is a last access

def test_T6_qr_png():
    client, _ = make_client_with_tmpdb()
    c = client.post("/api/links", json={"target_url": "https://example.com"}).json()
    code = c["short_code"]

    r = client.get(f"/api/links/{code}/qr")
    assert r.status_code == 200 # Request succeeded
    assert r.headers["content-type"] == "image/png" # Correct format
    assert len(r.content) > 100  # something reasonable

def test_T7_expired_returns_410():
    client, _ = make_client_with_tmpdb()
    past = iso_utc(datetime.now(timezone.utc) - timedelta(hours=1)) # Select a past date
    c = client.post("/api/links", json={"target_url": "https://example.com", "expires_at": past}).json() # Save the expired date
    code = c["short_code"]

    r = client.get(f"/{code}")
    assert r.status_code == 410 # Gone
