from fastapi.testclient import TestClient
import uuid

from app.main import app


def test_memory_crud_flow():
    unique = uuid.uuid4().hex[:8]
    email = f"test+{unique}@example.com"
    username = f"tester_{unique}"

    with TestClient(app) as client:
        # Register a user
        register_resp = client.post("/auth/register", json={
            "email": email,
            "username": username,
            "password": "strongpassword",
        })
        assert register_resp.status_code == 201
        # Login to get token
        login_resp = client.post("/auth/login", data={"username": email, "password": "strongpassword"})
        assert login_resp.status_code == 200
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create a memory
        create_resp = client.post(
            "/memories/",
            json={"content": "I prefer Python", "category": "preference", "slot_key": "preferred_language"},
            headers=headers,
        )
        assert create_resp.status_code == 201
        mem = create_resp.json()
        mem_id = mem["id"]

        # Read memory
        read_resp = client.get(f"/memories/{mem_id}", headers=headers)
        assert read_resp.status_code == 200

        # List memories
        list_resp = client.get("/memories/", headers=headers)
        assert list_resp.status_code == 200
        assert len(list_resp.json()) >= 1

        # Update memory
        patch_resp = client.patch(f"/memories/{mem_id}", json={"content": "I prefer Python 3"}, headers=headers)
        assert patch_resp.status_code == 200
        assert patch_resp.json()["content"] == "I prefer Python 3"

        # Delete memory
        del_resp = client.delete(f"/memories/{mem_id}", headers=headers)
        assert del_resp.status_code == 204

        # Re-create initial memory for conflict test
        create_resp = client.post(
            "/memories/",
            json={"content": "I prefer Rust", "category": "preference", "slot_key": "preferred_language"},
            headers=headers,
        )
        assert create_resp.status_code == 201

        # Attempt to create a conflicting memory in same slot
        conflict_resp = client.post(
            "/memories/",
            json={"content": "I prefer Go", "category": "preference", "slot_key": "preferred_language"},
            headers=headers,
        )
        assert conflict_resp.status_code == 409
        detail = conflict_resp.json()["detail"]
        assert detail["message"] == "Slot-conflict detected"
