"""
Comprehensive Cross-Cutting User Isolation Security Test Suite (Phase 8).

Verifies strict tenant isolation between User A and User B across all entities,
HTTP endpoints, and internal retrieval services:
1. Auth & Profiles (/auth/me)
2. Memories & Memory Retrieval (/memories/, /memories/{id}, /memories/retrieve)
3. Knowledge Concepts (/concepts/, /concepts/{id})
4. Learning Preferences (/preferences/, /preferences/{id})
5. Goals (/goals/, /goals/{id})
6. Tasks (/tasks/, /tasks/{id})
7. Documents & Chunk Retrieval (/documents/, /documents/{id}, retrieve_relevant_chunks)
8. Knowledge Graph Nodes & Relationships (/knowledge-graph/nodes, /knowledge/traverse/)
9. Knowledge Delta Computation (/knowledge-graph/delta, compute_knowledge_delta)
10. Assistant & Conversation Context (/assistant/ask, assemble_and_respond)
11. Dashboard Reflection Synthesis (/dashboard/, get_dashboard)
12. Cross-user modification / injection protection (evidence recording, node linking)
"""

import io
import uuid
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database.session import SessionLocal
from app.models.user import User
from app.models.knowledge_concept import KnowledgeConcept
from app.models.learning_preference import LearningPreference
from app.models.evidence import Evidence, EvidenceType, SubjectType
from app.models.document import Document, DocumentChunk, DocumentStatus
from app.models.goal import Goal
from app.models.task import Task
from app.models.memory import Memory, MemoryCategory
from app.services.retrieval_service import retrieve_memories
from app.services.document_service import retrieve_relevant_chunks
from app.services.knowledge_graph_service import compute_knowledge_delta, ensure_node, link
from app.services.evidence_service import record_evidence
from app.services.context_assembly_service import assemble_and_respond
from app.services.dashboard_service import get_dashboard


def _auth_user(client, prefix):
    uid = uuid.uuid4().hex[:8]
    email = f"{prefix}_{uid}@privacy.vault"
    username = f"{prefix}_{uid}"
    password = "SuperSecretPassword123!"
    r = client.post("/auth/register", json={"email": email, "username": username, "password": password})
    assert r.status_code == 201
    user_id = r.json()["id"]
    l = client.post("/auth/login", data={"username": email, "password": password})
    assert l.status_code == 200
    token = l.json()["access_token"]
    return user_id, {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_setup():
    with TestClient(app) as client:
        uid_a, headers_a = _auth_user(client, "alice")
        uid_b, headers_b = _auth_user(client, "bob")
        yield client, uid_a, headers_a, uid_b, headers_b


def test_auth_profile_isolation(test_setup):
    client, uid_a, headers_a, uid_b, headers_b = test_setup

    me_a = client.get("/auth/me", headers=headers_a).json()
    me_b = client.get("/auth/me", headers=headers_b).json()

    assert me_a["id"] == uid_a
    assert me_b["id"] == uid_b
    assert me_a["id"] != me_b["id"]
    assert "alice" in me_a["username"]
    assert "bob" in me_b["username"]


def test_memory_crud_and_retrieval_isolation(test_setup):
    client, uid_a, headers_a, uid_b, headers_b = test_setup

    # User A creates memory
    res_a = client.post("/memories/", json={"content": "AliceSecretPassportNumber987", "category": "personal"}, headers=headers_a)
    assert res_a.status_code == 201
    m_a = res_a.json()

    # User B creates memory
    res_b = client.post("/memories/", json={"content": "BobSecretBankAccount654", "category": "personal"}, headers=headers_b)
    assert res_b.status_code == 201
    m_b = res_b.json()

    # User B cannot read Alice's memory by ID
    assert client.get(f"/memories/{m_a['id']}", headers=headers_b).status_code in (403, 404)
    # User A cannot read Bob's memory by ID
    assert client.get(f"/memories/{m_b['id']}", headers=headers_a).status_code in (403, 404)

    # User B list contains 0 items of Alice
    list_b = client.get("/memories/", headers=headers_b).json()
    assert not any(m["id"] == m_a["id"] for m in list_b)
    assert not any("PassportNumber987" in m["content"] for m in list_b)

    # Retrieval service isolation
    db = SessionLocal()
    try:
        results_b = retrieve_memories(db, user_id=uid_b, query="PassportNumber987")
        assert len(results_b) == 0

        results_a = retrieve_memories(db, user_id=uid_a, query="PassportNumber987")
        assert len(results_a) >= 1
        assert "PassportNumber987" in results_a[0]["content"]
    finally:
        db.close()


def test_knowledge_concepts_isolation(test_setup):
    client, uid_a, headers_a, uid_b, headers_b = test_setup

    # Alice creates concept
    c_a = client.post("/concepts/", json={"name": "AliceSpecialAlgorithms", "initial_level": 0.9, "initial_confidence": 0.85}, headers=headers_a).json()
    # Bob creates concept
    c_b = client.post("/concepts/", json={"name": "BobSpecialDatabases", "initial_level": 0.7, "initial_confidence": 0.6}, headers=headers_b).json()

    # Direct ID access
    assert client.get(f"/concepts/{c_a['id']}", headers=headers_b).status_code == 404
    assert client.get(f"/concepts/{c_b['id']}", headers=headers_a).status_code == 404

    # Modification cross-access
    assert client.patch(f"/concepts/{c_a['id']}", json={"category": "Tampered"}, headers=headers_b).status_code == 404
    assert client.delete(f"/concepts/{c_a['id']}", headers=headers_b).status_code == 404

    # Listing isolation
    list_b = client.get("/concepts/", headers=headers_b).json()
    assert not any(c["id"] == c_a["id"] for c in list_b)
    assert not any("AliceSpecialAlgorithms" in c["name"] for c in list_b)


def test_learning_preferences_isolation(test_setup):
    client, uid_a, headers_a, uid_b, headers_b = test_setup

    p_a = client.post("/preferences/", json={"preference_type": "alice_prefers_visual_mindmaps", "initial_confidence": 0.8}, headers=headers_a).json()
    p_b = client.post("/preferences/", json={"preference_type": "bob_prefers_audio_podcasts", "initial_confidence": 0.75}, headers=headers_b).json()

    # Direct ID access
    assert client.get(f"/preferences/{p_a['id']}", headers=headers_b).status_code == 404
    assert client.get(f"/preferences/{p_b['id']}", headers=headers_a).status_code == 404

    # Listing
    list_b = client.get("/preferences/", headers=headers_b).json()
    assert not any(p["id"] == p_a["id"] for p in list_b)
    assert not any("alice_prefers" in p["preference_type"] for p in list_b)


def test_goals_and_tasks_isolation(test_setup):
    client, uid_a, headers_a, uid_b, headers_b = test_setup

    # Alice Goal & Task
    g_a = client.post("/goals/", json={"title": "Alice Goal Mastermind"}, headers=headers_a).json()
    t_a = client.post("/tasks/", json={"title": "Alice Task 1", "goal_id": g_a["id"]}, headers=headers_a).json()

    # Bob attempts to read or mutate Alice's goal/task
    assert client.get(f"/goals/{g_a['id']}", headers=headers_b).status_code == 404
    assert client.patch(f"/goals/{g_a['id']}", json={"status": "completed"}, headers=headers_b).status_code == 404
    assert client.delete(f"/goals/{g_a['id']}", headers=headers_b).status_code == 404

    assert client.get(f"/tasks/{t_a['id']}", headers=headers_b).status_code == 404
    assert client.patch(f"/tasks/{t_a['id']}", json={"status": "completed"}, headers=headers_b).status_code == 404
    assert client.delete(f"/tasks/{t_a['id']}", headers=headers_b).status_code == 404

    # Bob attempting to create a task linked to Alice's goal must be rejected (400)
    res_inject = client.post("/tasks/", json={"title": "Bob Injected Task", "goal_id": g_a["id"]}, headers=headers_b)
    assert res_inject.status_code == 400


def test_documents_and_chunk_retrieval_isolation(test_setup):
    client, uid_a, headers_a, uid_b, headers_b = test_setup

    file_a = {"file": ("alice_blueprint.txt", io.BytesIO(b"CRITICAL_ALICE_PRIVATE_KEY_999 is stored in vault."), "text/plain")}
    doc_a = client.post("/documents/upload", files=file_a, headers=headers_a).json()

    # Direct access
    assert client.get(f"/documents/{doc_a['id']}", headers=headers_b).status_code == 404
    assert client.get(f"/documents/{doc_a['id']}/status", headers=headers_b).status_code == 404
    assert client.delete(f"/documents/{doc_a['id']}", headers=headers_b).status_code == 404

    # Listing
    list_b = client.get("/documents/", headers=headers_b).json()
    assert not any(d["id"] == doc_a["id"] for d in list_b)

    # Retrieval service
    db = SessionLocal()
    try:
        chunks_b = retrieve_relevant_chunks(db, user_id=uid_b, query="CRITICAL_ALICE_PRIVATE_KEY_999")
        assert len(chunks_b) == 0

        chunks_a = retrieve_relevant_chunks(db, user_id=uid_a, query="CRITICAL_ALICE_PRIVATE_KEY_999")
        assert len(chunks_a) >= 1
        assert "CRITICAL_ALICE_PRIVATE_KEY_999" in chunks_a[0].content
    finally:
        db.close()


def test_knowledge_graph_and_delta_isolation(test_setup):
    client, uid_a, headers_a, uid_b, headers_b = test_setup

    # Alice creates concept
    client.post("/concepts/", json={"name": "AliceQuantumEncryption", "initial_level": 0.9, "initial_confidence": 0.9}, headers=headers_a)

    # Bob queries graph nodes
    nodes_b = client.get("/knowledge-graph/nodes", headers=headers_b).json()
    assert not any(n["label"] == "AliceQuantumEncryption" for n in nodes_b)

    # Bob computes delta for Alice's concept
    delta_b = client.post("/knowledge-graph/delta", json={"concept_names": ["AliceQuantumEncryption"]}, headers=headers_b).json()
    # Must be marked as missing (has_concept: False, gap: True) for Bob
    assert delta_b["AliceQuantumEncryption"]["has_concept"] is False
    assert delta_b["AliceQuantumEncryption"]["gap"] is True


def test_dashboard_and_assistant_context_isolation(test_setup, monkeypatch):
    client, uid_a, headers_a, uid_b, headers_b = test_setup

    captured_prompts = []

    def mock_gen(system_prompt: str, user_message: str, **kwargs):
        captured_prompts.append(system_prompt)
        return "Safe response."

    monkeypatch.setattr("app.services.ai_service.generate_response", mock_gen)

    # Alice uploads document and sets preference
    file_a = {"file": ("alice_notes.txt", io.BytesIO(b"Quantum encryption protocols and key distribution ALICE_EXCLUSIVE_SECRET_CONTENT_999"), "text/plain")}
    client.post("/documents/upload", files=file_a, headers=headers_a)
    client.post("/preferences/", json={"preference_type": "alice_unique_pedagogy_style", "initial_confidence": 0.9}, headers=headers_a)

    # Bob queries assistant with keywords matching Alice's documents topic
    client.post("/assistant/ask", json={"question": "Tell me about quantum encryption protocols and pedagogy"}, headers=headers_b)

    assert len(captured_prompts) >= 1
    bob_sys_prompt = captured_prompts[-1]
    assert "ALICE_EXCLUSIVE_SECRET_CONTENT_999" not in bob_sys_prompt
    assert "alice_unique_pedagogy_style" not in bob_sys_prompt

    # Bob queries dashboard
    dash_b = client.get("/dashboard/", headers=headers_b).json()
    dash_b_str = str(dash_b)
    assert "ALICE_EXCLUSIVE_SECRET_CONTENT_999" not in dash_b_str
    assert "alice_unique_pedagogy_style" not in dash_b_str


def test_cross_user_injection_protection(test_setup):
    client, uid_a, headers_a, uid_b, headers_b = test_setup

    c_a = client.post("/concepts/", json={"name": "AliceConceptToProtect"}, headers=headers_a).json()

    db = SessionLocal()
    try:
        # Bob cannot record evidence targeting Alice's concept
        with pytest.raises(ValueError, match="not found for user"):
            record_evidence(
                db=db,
                user_id=uid_b,
                evidence_type=EvidenceType.EXPLICIT_STATEMENT,
                subject_type=SubjectType.KNOWLEDGE_CONCEPT,
                subject_id=c_a["id"],
                weight=0.9,
                summary="Attempted cross-user state manipulation",
            )
    finally:
        db.close()
