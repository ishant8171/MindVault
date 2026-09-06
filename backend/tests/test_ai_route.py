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


def test_ai_test_route_authenticated(monkeypatch):
    # Monkeypatch ai_service.generate_text to avoid external API calls
    fake_resp = {"choices": [{"message": {"content": "Hi from fake AI"}}]}
    monkeypatch.setattr("app.services.ai_service.generate_text", lambda prompt, system_message=None, **kwargs: fake_resp)

    with TestClient(app) as client:
        headers = _register_and_auth(client)
        resp = client.post("/ai/test", json={"prompt": "Hello"}, headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["text"] == "Hi from fake AI"
        assert body["raw"] == fake_resp


def test_ai_test_route_unauthenticated():
    with TestClient(app) as client:
        resp = client.post("/ai/test", json={"prompt": "Hello"})
        assert resp.status_code == 401
