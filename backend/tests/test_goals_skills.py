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


def test_goal_crud_and_isolation():
    with TestClient(app) as client:
        headers = _register_and_auth(client)
        # create goal
        r = client.post("/goals/", json={"title": "Finish project", "description": "Finish X", "priority": "high"}, headers=headers)
        assert r.status_code == 201
        goal = r.json()
        gid = goal["id"]

        # read
        rr = client.get(f"/goals/{gid}", headers=headers)
        assert rr.status_code == 200

        # update progress
        up = client.patch(f"/goals/{gid}", json={"progress": 0.5, "status": "in_progress"}, headers=headers)
        assert up.status_code == 200
        assert up.json()["progress"] == 0.5

        # delete (mark abandoned)
        d = client.delete(f"/goals/{gid}", headers=headers)
        assert d.status_code == 204

        # cross-user isolation
        # create second user
        unique = uuid.uuid4().hex[:8]
        email_b = f"test+{unique}@example.com"
        r2 = client.post("/auth/register", json={"email": email_b, "username": f"u_{unique}", "password": "strongpassword"})
        assert r2.status_code == 201
        login_b = client.post("/auth/login", data={"username": email_b, "password": "strongpassword"})
        token_b = login_b.json()["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # user B cannot access user A's goal
        rr2 = client.get(f"/goals/{gid}", headers=headers_b)
        assert rr2.status_code == 404


def test_skill_crud_and_isolation():
    with TestClient(app) as client:
        headers = _register_and_auth(client)
        # create skill
        r = client.post("/skills/", json={"name": "Python", "category": "programming"}, headers=headers)
        assert r.status_code == 201
        sid = r.json()["id"]

        # read
        rr = client.get(f"/skills/{sid}", headers=headers)
        assert rr.status_code == 200

        # update
        up = client.patch(f"/skills/{sid}", json={"status": "learning"}, headers=headers)
        assert up.status_code == 200
        assert up.json()["status"] == "learning"

        # delete
        d = client.delete(f"/skills/{sid}", headers=headers)
        assert d.status_code == 204

        # cross-user isolation
        unique = uuid.uuid4().hex[:8]
        email_b = f"test+{unique}@example.com"
        r2 = client.post("/auth/register", json={"email": email_b, "username": f"u_{unique}", "password": "strongpassword"})
        login_b = client.post("/auth/login", data={"username": email_b, "password": "strongpassword"})
        token_b = login_b.json()["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}
        rr2 = client.get(f"/skills/{sid}", headers=headers_b)
        assert rr2.status_code == 404
