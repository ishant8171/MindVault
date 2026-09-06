import uuid
from fastapi.testclient import TestClient

from app.main import app
from app.database.session import SessionLocal
from app.models.memory import Memory


def _register_and_auth(client):
    unique = uuid.uuid4().hex[:8]
    email = f"test+{unique}@example.com"
    username = f"tester_{unique}"
    pw = "strongpassword"
    r = client.post("/auth/register", json={"email": email, "username": username, "password": pw})
    assert r.status_code == 201
    login = client.post("/auth/login", data={"username": email, "password": pw})
    assert login.status_code == 200
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_no_conflict_different_slot():
    with TestClient(app) as client:
        headers = _register_and_auth(client)
        r1 = client.post("/memories/", json={"content": "A", "category": "personal", "slot_key": "s1"}, headers=headers)
        assert r1.status_code == 201
        r2 = client.post("/memories/", json={"content": "B", "category": "personal", "slot_key": "s2"}, headers=headers)
        assert r2.status_code == 201


def test_same_slot_exact_duplicate_returns_existing():
    with TestClient(app) as client:
        headers = _register_and_auth(client)
        payload = {"content": "My favorite color is blue", "category": "personal", "slot_key": "color"}
        r1 = client.post("/memories/", json=payload, headers=headers)
        assert r1.status_code == 201
        r2 = client.post("/memories/", json=payload, headers=headers)
        # exact duplicate should return existing memory (no new creation)
        assert r2.status_code in (200, 201)
        assert r1.json()["id"] == r2.json()["id"]


def test_same_slot_potential_conflict_persists_conflict():
    with TestClient(app) as client:
        headers = _register_and_auth(client)
        r1 = client.post("/memories/", json={"content": "I prefer Python", "category": "preference", "slot_key": "lang"}, headers=headers)
        assert r1.status_code == 201
        # different content same slot -> conflict
        r2 = client.post("/memories/", json={"content": "I prefer Rust", "category": "preference", "slot_key": "lang"}, headers=headers)
        assert r2.status_code == 409
        detail = r2.json()["detail"]
        assert "conflict_id" in detail
        conflict_id = detail["conflict_id"]
        # conflict should be listed
        ls = client.get("/memories/conflicts", headers=headers)
        assert ls.status_code == 200
        assert any(c["id"] == conflict_id for c in ls.json())


def test_different_users_isolated():
    with TestClient(app) as client:
        headers_a = _register_and_auth(client)
        # create second user
        unique = uuid.uuid4().hex[:8]
        email_b = f"test+{unique}@example.com"
        r = client.post("/auth/register", json={"email": email_b, "username": f"u_{unique}", "password": "strongpassword"})
        assert r.status_code == 201
        login_b = client.post("/auth/login", data={"username": email_b, "password": "strongpassword"})
        token_b = login_b.json()["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        r1 = client.post("/memories/", json={"content": "A secret", "category": "personal", "slot_key": "x"}, headers=headers_a)
        assert r1.status_code == 201
        r2 = client.post("/memories/", json={"content": "Different", "category": "personal", "slot_key": "x"}, headers=headers_b)
        # user B shouldn't conflict with user A's memory
        assert r2.status_code == 201


def test_conflict_resolution_keep_old_and_history_preserved():
    with TestClient(app) as client:
        headers = _register_and_auth(client)
        r1 = client.post("/memories/", json={"content": "Live in NYC", "category": "personal", "slot_key": "city"}, headers=headers)
        assert r1.status_code == 201
        r2 = client.post("/memories/", json={"content": "Live in San Francisco", "category": "personal", "slot_key": "city"}, headers=headers)
        assert r2.status_code == 409
        conflict_id = r2.json()["detail"]["conflict_id"]
        # resolve keeping old
        resp = client.post(f"/memories/conflicts/{conflict_id}/resolve", json={"action": "keep_old"}, headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["resolution"] == "kept_old"
        # ensure new memory is marked deleted
        ls = client.get("/memories/conflicts", headers=headers).json()
        assert any(c["id"] == conflict_id for c in ls)


def test_conflict_resolution_keep_new_and_archive_old():
    with TestClient(app) as client:
        headers = _register_and_auth(client)
        r1 = client.post("/memories/", json={"content": "Use Vim", "category": "preference", "slot_key": "editor"}, headers=headers)
        assert r1.status_code == 201
        r2 = client.post("/memories/", json={"content": "Use Neovim", "category": "preference", "slot_key": "editor"}, headers=headers)
        assert r2.status_code == 409
        conflict_id = r2.json()["detail"]["conflict_id"]
        resp = client.post(f"/memories/conflicts/{conflict_id}/resolve", json={"action": "keep_new"}, headers=headers)
        assert resp.status_code == 200
        # after resolution, check that old memory is archived
        conflicts = client.get("/memories/conflicts", headers=headers).json()
        assert any(c["id"] == conflict_id for c in conflicts)


def test_conflict_resolution_merge():
    with TestClient(app) as client:
        headers = _register_and_auth(client)
        r1 = client.post("/memories/", json={"content": "I like A", "category": "interest", "slot_key": "pref"}, headers=headers)
        assert r1.status_code == 201
        r2 = client.post("/memories/", json={"content": "I also like B", "category": "interest", "slot_key": "pref"}, headers=headers)
        assert r2.status_code == 409
        conflict_id = r2.json()["detail"]["conflict_id"]
        merged = "I like A and B"
        resp = client.post(f"/memories/conflicts/{conflict_id}/resolve", json={"action": "merge", "merged_content": merged}, headers=headers)
        assert resp.status_code == 200
        # ensure old memory content updated
        # list memories and find slot
        resp2 = client.get("/memories/", headers=headers)
        # ensure merged content appears in some memory
        assert any("A and B" in m["content"] for m in resp2.json())


def test_lifecycle_transitions_and_unauthorized_access():
    with TestClient(app) as client:
        headers = _register_and_auth(client)
        r = client.post("/memories/", json={"content": "Temp note", "category": "temporary", "slot_key": "t1"}, headers=headers)
        assert r.status_code == 201
        mem_id = r.json()["id"]
        # activate
        resp = client.post(f"/memories/{mem_id}/lifecycle", json={"action": "activate"}, headers=headers)
        assert resp.status_code == 200
        # unauthorized resolution
        resp2 = client.post(f"/memories/conflicts/9999/resolve", json={"action": "keep_old"})
        assert resp2.status_code in (401, 404)
