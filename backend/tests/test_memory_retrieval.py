import uuid
from datetime import datetime, timezone, timedelta

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


def test_authenticated_retrieval_keyword_matching_and_ranking():
    with TestClient(app) as client:
        headers = _register_and_auth(client)

        # create two memories with same keyword but different importance
        r1 = client.post("/memories/", json={"content": "I like cats and dogs", "category": "personal", "importance_score": 0.2}, headers=headers)
        assert r1.status_code == 201
        r2 = client.post("/memories/", json={"content": "Cats are my favorite pets", "category": "personal", "importance_score": 0.9}, headers=headers)
        assert r2.status_code == 201

        resp = client.post("/memories/retrieve", json={"query": "cats", "limit": 5}, headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert "results" in body
        results = body["results"]
        assert len(results) >= 1
        # highest importance should rank first
        assert results[0]["importance_score"] >= results[-1]["importance_score"]


def test_unauthenticated_retrieval_rejected():
    with TestClient(app) as client:
        resp = client.post("/memories/retrieve", json={"query": "anything"})
        assert resp.status_code == 401


def test_user_isolation():
    with TestClient(app) as client:
        headers_a = _register_and_auth(client)
        # Create second user
        unique = uuid.uuid4().hex[:8]
        email_b = f"test+{unique}@example.com"
        r = client.post("/auth/register", json={"email": email_b, "username": f"u_{unique}", "password": "strongpassword"})
        assert r.status_code == 201
        login_b = client.post("/auth/login", data={"username": email_b, "password": "strongpassword"})
        token_b = login_b.json()["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # user A creates memory
        r1 = client.post("/memories/", json={"content": "User A secret note", "category": "personal"}, headers=headers_a)
        assert r1.status_code == 201
        # user B creates memory
        r2 = client.post("/memories/", json={"content": "User B secret note about cats", "category": "personal"}, headers=headers_b)
        assert r2.status_code == 201

        # user A searches for 'cats' should not see user B's memory
        resp = client.post("/memories/retrieve", json={"query": "cats"}, headers=headers_a)
        assert resp.status_code == 200
        assert all("User B" not in r["content"] for r in resp.json()["results"])


def test_no_relevant_results_and_short_query_edge_cases():
    with TestClient(app) as client:
        headers = _register_and_auth(client)

        # No relevant results
        resp = client.post("/memories/retrieve", json={"query": "qwertyuiop"}, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["results"] == []

        # Short query should be rejected
        resp2 = client.post("/memories/retrieve", json={"query": "hi"}, headers=headers)
        assert resp2.status_code == 400


def test_ranking_considers_recency():
    with TestClient(app) as client:
        headers = _register_and_auth(client)

        # create old memory and new memory with same keyword and similar importance
        r_old = client.post("/memories/", json={"content": "Remember project", "category": "project", "importance_score": 0.6}, headers=headers)
        assert r_old.status_code == 201
        old_id = r_old.json()["id"]

        r_new = client.post("/memories/", json={"content": "Remember project details", "category": "project", "importance_score": 0.6}, headers=headers)
        assert r_new.status_code == 201

        # make the first memory older by 120 days
        db = SessionLocal()
        try:
            mem = db.query(Memory).filter(Memory.id == old_id).first()
            mem.created_at = datetime.now(timezone.utc) - timedelta(days=120)
            db.add(mem)
            db.commit()
        finally:
            db.close()

        resp = client.post("/memories/retrieve", json={"query": "remember project", "limit": 5}, headers=headers)
        assert resp.status_code == 200
        results = resp.json()["results"]
        assert len(results) >= 1
        # newer memory should appear before older one due to recency bonus
        ids = [r["id"] for r in results]
        assert r_new.json()["id"] in ids
        if old_id in ids:
            assert ids.index(r_new.json()["id"]) < ids.index(old_id)
