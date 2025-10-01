# tests/test_links.py
import os, tempfile, json, shutil
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

# Importa la app y el db del paquete
from app.main import create_app
import app.db as db
from app.services import codes

def norm(u: str) -> str:
    # accept optional trailing slash normalization
    return u.rstrip("/")


def make_client_with_tmpdb():
    tmpdb = tempfile.NamedTemporaryFile(delete=False)
    tmpdb.close()
    os.environ["APP_DB_PATH"] = tmpdb.name  # set BEFORE importing app

    from app.main import create_app  # import now, picks up APP_DB_PATH
    app = create_app()
    from app import db
    db.init_db()  # against tmp DB

    client = TestClient(app, follow_redirects=False)
    return client, tmpdb.name

def iso_utc(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()

# ---------- Unit ----------

def test_code_generator_collision():
    calls = {"n": 0}
    def fake_exists(code: str) -> bool:
        calls["n"] += 1
        # colisiona las dos primeras veces, tercera libre
        return calls["n"] < 3
    code = codes.generate_unique_code(fake_exists, max_tries=5)
    assert isinstance(code, str) and len(code) >= 6
    assert calls["n"] == 3

# ---------- Integration CRUD ----------

def test_T1_create_and_invalid_body():
    client, _ = make_client_with_tmpdb()

    # válido
    res = client.post("/api/links", json={"target_url": "https://example.com"})
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["short_code"]
    assert norm(body["target_url"]) == "https://example.com"


    # inválido (URL mala) -> 400 (tu handler de RequestValidationError)
    res2 = client.post("/api/links", json={"target_url": "notaurl"})
    assert res2.status_code in (400, 422)  # según tu handler
    # si 400, espera el shape uniforme
    if res2.status_code == 400:
        err = res2.json()
        assert "error" in err or "detail" in err

def test_T2_list_and_detail():
    client, _ = make_client_with_tmpdb()
    a = client.post("/api/links", json={"target_url": "https://a.example"}).json()
    b = client.post("/api/links", json={"target_url": "https://b.example"}).json()

    lst = client.get("/api/links").json()
    codes = {r["short_code"] for r in lst}
    assert a["short_code"] in codes and b["short_code"] in codes

    det = client.get(f"/api/links/{a['short_code']}")
    assert det.status_code == 200
    assert det.json()["short_code"] == a["short_code"]

def test_T3_update_target_and_expiry_and_clear():
    client, _ = make_client_with_tmpdb()
    c = client.post("/api/links", json={"target_url": "https://old.example"}).json()
    code = c["short_code"]

    # actualiza target y expiry
    exp = iso_utc(datetime.now(timezone.utc) + timedelta(days=1))
    up = client.put(f"/api/links/{code}", json={
        "target_url": "https://new.example",
        "expires_at": exp
    })
    assert up.status_code == 200, up.text
    j = up.json()
    assert norm(j["target_url"]) == "https://new.example"
    assert j["expires_at"]

    # borra expiry (null)
    up2 = client.put(f"/api/links/{code}", json={"expires_at": None})
    assert up2.status_code == 200
    assert up2.json()["expires_at"] is None

def test_T4_delete_then_404_detail():
    client, _ = make_client_with_tmpdb()
    c = client.post("/api/links", json={"target_url": "https://x.example"}).json()
    code = c["short_code"]

    assert client.delete(f"/api/links/{code}").status_code == 204
    assert client.get(f"/api/links/{code}").status_code == 404

def test_T5_redirect_increments_clicks():
    client, _ = make_client_with_tmpdb()
    c = client.post("/api/links", json={"target_url": "https://example.com"}).json()
    code = c["short_code"]

    r = client.get(f"/{code}")
    assert r.status_code == 302
    assert r.headers["Location"].startswith("https://example.com")

    det = client.get(f"/api/links/{code}").json()
    assert det["click_count"] >= 1
    assert det["last_access_at"] is not None

def test_T6_qr_png():
    client, _ = make_client_with_tmpdb()
    c = client.post("/api/links", json={"target_url": "https://example.com"}).json()
    code = c["short_code"]

    r = client.get(f"/api/links/{code}/qr")
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/png"
    assert len(r.content) > 100  # algo razonable

def test_T7_expired_returns_410():
    client, _ = make_client_with_tmpdb()
    past = iso_utc(datetime.now(timezone.utc) - timedelta(hours=1))
    c = client.post("/api/links", json={"target_url": "https://example.com", "expires_at": past}).json()
    code = c["short_code"]

    r = client.get(f"/{code}")
    assert r.status_code == 410
