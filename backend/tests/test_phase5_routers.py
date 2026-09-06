"""
Phase 5 tests:
Verifies HTTP routers:
- Standard CRUD happy paths across all new routers
- Task completion automatically emits Evidence and updates concept confidence
- Memory conflict detection and resolution workflow with audit history
- Document multipart upload, synchronous processing, status, and listing
- Assistant ask endpoint with conversation logging and mocked AI service
- CRITICAL user isolation: User A's token can NEVER read, update, or delete User B's
  memories, concepts, preferences, goals, tasks, documents, or graph nodes.
"""

import io
import uuid
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.task import TaskStatus
from app.models.document import DocumentStatus
from app.models.evidence import Evidence


def _register_and_auth(client, tag=None):
    unique = uuid.uuid4().hex[:8]
    prefix = tag or "u"
    email = f"{prefix}_{unique}@example.com"
    username = f"{prefix}_{unique}"
    password = "StrongPassword123!"
    r = client.post("/auth/register", json={"email": email, "username": username, "password": password})
    assert r.status_code == 201, f"Register failed: {r.text}"
    login = client.post("/auth/login", data={"username": email, "password": password})
    assert login.status_code == 200, f"Login failed: {login.text}"
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_concepts_crud():
    with TestClient(app) as client:
        headers = _register_and_auth(client, "concept")

        # 1. Create
        res = client.post("/concepts/", json={"name": "Pointers", "category": "C++", "initial_level": 0.2, "initial_confidence": 0.3}, headers=headers)
        assert res.status_code == 201
        data = res.json()
        cid = data["id"]
        assert data["name"] == "Pointers"
        assert data["current_level"] == 0.2

        # 2. List
        list_res = client.get("/concepts/", headers=headers)
        assert list_res.status_code == 200
        assert any(c["id"] == cid for c in list_res.json())

        # 3. Read single
        get_res = client.get(f"/concepts/{cid}", headers=headers)
        assert get_res.status_code == 200
        assert get_res.json()["id"] == cid

        # 4. Patch
        patch_res = client.patch(f"/concepts/{cid}", json={"category": "Low-level Systems"}, headers=headers)
        assert patch_res.status_code == 200
        assert patch_res.json()["category"] == "Low-level Systems"

        # 5. Delete
        del_res = client.delete(f"/concepts/{cid}", headers=headers)
        assert del_res.status_code == 204
        assert client.get(f"/concepts/{cid}", headers=headers).status_code == 404


def test_preferences_crud():
    with TestClient(app) as client:
        headers = _register_and_auth(client, "pref")

        # 1. Create / reinforce preference
        res = client.post("/preferences/", json={"preference_type": "prefers_visual_diagrams", "initial_confidence": 0.7}, headers=headers)
        assert res.status_code == 201
        data = res.json()
        pid = data["id"]
        assert data["preference_type"] == "prefers_visual_diagrams"
        assert data["confidence"] > 0.1

        # 2. List
        list_res = client.get("/preferences/", headers=headers)
        assert list_res.status_code == 200
        assert any(p["id"] == pid for p in list_res.json())

        # 3. Get single
        get_res = client.get(f"/preferences/{pid}", headers=headers)
        assert get_res.status_code == 200
        assert get_res.json()["id"] == pid


def test_task_completion_emits_evidence():
    with TestClient(app) as client:
        headers = _register_and_auth(client, "task_ev")

        # 1. Create a concept
        c_res = client.post("/concepts/", json={"name": "Graph BFS"}, headers=headers)
        assert c_res.status_code == 201
        cid = c_res.json()["id"]

        # 2. Create a goal
        g_res = client.post("/goals/", json={"title": "Master Graphs"}, headers=headers)
        assert g_res.status_code == 201
        gid = g_res.json()["id"]

        # 3. Create a task linked to concept and goal
        t_res = client.post("/tasks/", json={
            "title": "Implement BFS queue",
            "goal_id": gid,
            "related_concept_ids": [cid],
        }, headers=headers)
        assert t_res.status_code == 201
        tid = t_res.json()["id"]

        # Check concept baseline confidence before completion
        c_before = client.get(f"/concepts/{cid}", headers=headers).json()
        conf_before = c_before["confidence"]

        # 4. Complete the task
        patch_res = client.patch(f"/tasks/{tid}", json={"status": "completed"}, headers=headers)
        assert patch_res.status_code == 200
        assert patch_res.json()["status"] == "completed"
        assert patch_res.json()["completed_at"] is not None

        # 5. Check concept confidence has increased via emitted evidence
        c_after = client.get(f"/concepts/{cid}", headers=headers).json()
        assert c_after["confidence"] > conf_before
        assert c_after["evidence_count"] >= 1


def test_memory_conflict_flow():
    with TestClient(app) as client:
        headers = _register_and_auth(client, "mem_flow")

        # 1. Add first memory in slot "city"
        r1 = client.post("/memories/", json={"content": "I live in Chicago", "slot_key": "city"}, headers=headers)
        assert r1.status_code == 201
        mem1_id = r1.json()["id"]

        # 2. Add conflicting memory in slot "city"
        r2 = client.post("/memories/", json={"content": "I live in Seattle", "slot_key": "city"}, headers=headers)
        assert r2.status_code == 409
        conflict_id = r2.json()["detail"]["conflict_id"]

        # 3. Check conflict in /memories/conflicts
        c_res = client.get("/memories/conflicts", headers=headers)
        assert c_res.status_code == 200
        assert any(c["id"] == conflict_id for c in c_res.json())

        # 4. Resolve conflict by keeping new memory (Seattle)
        res_solve = client.post(f"/memories/conflicts/{conflict_id}/resolve", json={"action": "keep_new"}, headers=headers)
        assert res_solve.status_code == 200
        assert res_solve.json()["status"] == "resolved"


def test_document_upload_endpoint_processes_and_lists():
    with TestClient(app) as client:
        headers = _register_and_auth(client, "doc_up")

        # Upload a sample text file
        file_content = b"Data structures and algorithms are the bedrock of computer science. Dynamic programming optimizes recursive search."
        files = {"file": ("dsa_study.txt", io.BytesIO(file_content), "text/plain")}

        up_res = client.post("/documents/upload", files=files, headers=headers)
        assert up_res.status_code == 201
        doc_data = up_res.json()
        doc_id = doc_data["id"]
        assert doc_data["filename"] == "dsa_study.txt"
        assert doc_data["status"] == "ready"
        assert doc_data["chunk_count"] >= 1

        # List documents
        list_res = client.get("/documents/", headers=headers)
        assert list_res.status_code == 200
        assert any(d["id"] == doc_id for d in list_res.json())

        # Check status endpoint
        status_res = client.get(f"/documents/{doc_id}/status", headers=headers)
        assert status_res.status_code == 200
        assert status_res.json()["status"] == "ready"


def test_knowledge_graph_and_delta_endpoints():
    with TestClient(app) as client:
        headers = _register_and_auth(client, "graph_ep")

        # Create a concept and goal
        client.post("/concepts/", json={"name": "Bit Manipulation", "initial_level": 0.8, "initial_confidence": 0.7}, headers=headers)
        client.post("/goals/", json={"title": "Pass Coding Interview"}, headers=headers)

        # Query nodes
        nodes_res = client.get("/knowledge-graph/nodes", headers=headers)
        assert nodes_res.status_code == 200
        labels = [n["label"] for n in nodes_res.json()]
        assert "Bit Manipulation" in labels
        assert "Pass Coding Interview" in labels

        # Query delta endpoint
        delta_res = client.post("/knowledge-graph/delta", json={"concept_names": ["Bit Manipulation", "Red-Black Trees"]}, headers=headers)
        assert delta_res.status_code == 200
        delta = delta_res.json()
        assert delta["Bit Manipulation"]["has_concept"] is True
        assert delta["Bit Manipulation"]["gap"] is False
        assert delta["Red-Black Trees"]["has_concept"] is False
        assert delta["Red-Black Trees"]["gap"] is True


def test_assistant_ask_endpoint_uses_mocked_ai_service(monkeypatch):
    monkeypatch.setattr(
        "app.services.ai_service.generate_response",
        lambda system_prompt, user_message, **kwargs: "Mocked adaptive response explaining recursion.",
    )

    with TestClient(app) as client:
        headers = _register_and_auth(client, "assistant_ep")

        ask_res = client.post("/assistant/ask", json={"question": "How do recursive base cases work?"}, headers=headers)
        assert ask_res.status_code == 200
        body = ask_res.json()
        assert body["response"] == "Mocked adaptive response explaining recursion."
        assert body["conversation_id"] is not None
        assert body["user_message_id"] is not None
        assert body["assistant_message_id"] is not None


def test_router_user_isolation():
    """
    CRITICAL: Verifies User A's token can NEVER read or modify User B's resources:
    memories, concepts, preferences, goals, tasks, documents, or graph nodes.
    """
    with TestClient(app) as client:
        headers_a = _register_and_auth(client, "user_a")
        headers_b = _register_and_auth(client, "user_b")

        # 1. User A creates resources
        mem_a = client.post("/memories/", json={"content": "User A secret memory"}, headers=headers_a).json()
        conc_a = client.post("/concepts/", json={"name": "User A Secret Concept"}, headers=headers_a).json()
        pref_a = client.post("/preferences/", json={"preference_type": "user_a_only_pref"}, headers=headers_a).json()
        goal_a = client.post("/goals/", json={"title": "User A Secret Goal"}, headers=headers_a).json()
        task_a = client.post("/tasks/", json={"title": "User A Secret Task"}, headers=headers_a).json()

        files = {"file": ("user_a_doc.txt", io.BytesIO(b"User A private note"), "text/plain")}
        doc_a = client.post("/documents/upload", files=files, headers=headers_a).json()

        # 2. User B attempts to access User A's resources (expect 404)
        # Memory
        assert client.get(f"/memories/{mem_a['id']}", headers=headers_b).status_code in (403, 404)
        assert client.delete(f"/memories/{mem_a['id']}", headers=headers_b).status_code in (403, 404)

        # Concept
        assert client.get(f"/concepts/{conc_a['id']}", headers=headers_b).status_code == 404
        assert client.patch(f"/concepts/{conc_a['id']}", json={"category": "Hacked"}, headers=headers_b).status_code == 404
        assert client.delete(f"/concepts/{conc_a['id']}", headers=headers_b).status_code == 404

        # Preference
        assert client.get(f"/preferences/{pref_a['id']}", headers=headers_b).status_code == 404

        # Goal
        assert client.get(f"/goals/{goal_a['id']}", headers=headers_b).status_code == 404
        assert client.delete(f"/goals/{goal_a['id']}", headers=headers_b).status_code == 404

        # Task
        assert client.get(f"/tasks/{task_a['id']}", headers=headers_b).status_code == 404
        assert client.patch(f"/tasks/{task_a['id']}", json={"status": "completed"}, headers=headers_b).status_code == 404
        assert client.delete(f"/tasks/{task_a['id']}", headers=headers_b).status_code == 404

        # Document
        assert client.get(f"/documents/{doc_a['id']}", headers=headers_b).status_code == 404
        assert client.get(f"/documents/{doc_a['id']}/status", headers=headers_b).status_code == 404
        assert client.delete(f"/documents/{doc_a['id']}", headers=headers_b).status_code == 404

        # Graph Nodes
        nodes_b = client.get("/knowledge-graph/nodes", headers=headers_b).json()
        assert not any(n["label"] == "User A Secret Concept" for n in nodes_b)
        assert not any(n["label"] == "User A Secret Goal" for n in nodes_b)
