import uuid
from fastapi.testclient import TestClient

from app.main import app


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


def test_extract_endpoint_authenticated(monkeypatch):
    # Mock ai_service.generate_text to return JSON array
    fake_text = '[{"content": "Remember to submit report", "slot_key": "submit_report", "category": "important_event", "confidence_score": 0.8}]'
    fake_resp = {"choices": [{"message": {"content": fake_text}}]}
    monkeypatch.setattr("app.services.ai_service.generate_text", lambda prompt, system_message=None, **kwargs: fake_resp)

    with TestClient(app) as client:
        headers = _register_and_auth(client)
        resp = client.post("/memories/extract", json={"text": "Please help me remember to submit report."}, headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert "candidates" in body
        assert len(body["candidates"]) == 1
        cand = body["candidates"][0]
        assert cand["content"] == "Remember to submit report"
        assert 0.0 <= cand["importance_score"] <= 1.0


def test_extract_endpoint_unauthenticated():
    with TestClient(app) as client:
        resp = client.post("/memories/extract", json={"text": "Hi"})
        assert resp.status_code == 401
