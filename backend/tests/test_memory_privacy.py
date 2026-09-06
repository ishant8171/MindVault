from fastapi.testclient import TestClient
import uuid

from app.main import app


def _register_and_token(client, email=None):
    unique = uuid.uuid4().hex[:8]
    if not email:
        email = f"priv+{unique}@example.com"
    username = f"priv_{unique}"
    pw = "strongpassword"
    r = client.post("/auth/register", json={"email": email, "username": username, "password": pw})
    assert r.status_code == 201
    login = client.post("/auth/login", data={"username": email, "password": pw})
    assert login.status_code == 200
    token = login.json()["access_token"]
    return token


def test_memory_visibility_and_deletion_isolation():
    with TestClient(app) as client:
        # User A
        token_a = _register_and_token(client)
        headers_a = {"Authorization": f"Bearer {token_a}"}

        # Create a memory as user A
        resp = client.post("/memories/", json={"content": "secret A","slot_key": "slotX"}, headers=headers_a)
        assert resp.status_code == 201
        mem_a = resp.json()
        mem_a_id = mem_a["id"] if isinstance(mem_a, list) else mem_a["id"]

        # Unauthenticated requests are rejected for list and get
        r = client.get("/memories/")
        assert r.status_code == 401
        r = client.get(f"/memories/{mem_a_id}")
        assert r.status_code == 401

        # User B
        token_b = _register_and_token(client)
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # User B should not see user A's memory in list
        list_b = client.get("/memories/", headers=headers_b)
        assert list_b.status_code == 200
        ids_b = [m["id"] for m in list_b.json()]
        assert mem_a_id not in ids_b

        # User B cannot read user A's memory
        r = client.get(f"/memories/{mem_a_id}", headers=headers_b)
        assert r.status_code in (403, 404)

        # User B cannot delete user A's memory
        r = client.delete(f"/memories/{mem_a_id}", headers=headers_b)
        assert r.status_code in (403, 404)

        # User A can delete their own memory (soft-delete)
        r = client.delete(f"/memories/{mem_a_id}", headers=headers_a)
        assert r.status_code == 204

        # After deletion, attempting to read should return 404
        r = client.get(f"/memories/{mem_a_id}", headers=headers_a)
        assert r.status_code == 404
