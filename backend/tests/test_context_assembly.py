"""
Phase 4 tests:
Verifies ContextAssemblyService and ai_service:
- System prompt skips established concepts and targets knowledge gaps
- Document chunks are injected into context when relevant
- Interaction evidence is emitted after response
- Strict user-scoping: User A context never leaks to User B
- ai_service raises AIProviderNotConfiguredError when OPENAI_API_KEY is not set
All AI calls are mocked; no live network calls.
"""

import uuid
import pytest

from app.core.config import settings
from app.database.session import SessionLocal
from app.models.user import User
from app.models.knowledge_concept import KnowledgeConcept
from app.models.learning_preference import LearningPreference
from app.models.document import Document, DocumentChunk, DocumentStatus
from app.models.evidence import Evidence, EvidenceType
from app.services.ai_service import generate_response, AIProviderNotConfiguredError
from app.services.context_assembly_service import assemble_and_respond


def _create_user(db):
    uid = uuid.uuid4().hex[:8]
    user = User(
        username=f"ctx_u_{uid}",
        email=f"ctx_u_{uid}@test.com",
        password_hash="fakehash",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_ai_service_raises_clear_error_without_api_key(monkeypatch):
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "")
    with pytest.raises(AIProviderNotConfiguredError, match="OPENAI_API_KEY is not set"):
        generate_response("You are a helpful assistant", "Hello")


def test_context_assembly_skips_known_concepts_in_prompt(monkeypatch):
    captured = {}

    def mock_generate_response(system_prompt: str, user_message: str, **kwargs):
        captured["system_prompt"] = system_prompt
        captured["user_message"] = user_message
        return "Here is an explanation focusing on recursion."

    monkeypatch.setattr("app.services.ai_service.generate_response", mock_generate_response)

    db = SessionLocal()
    try:
        user = _create_user(db)

        # Established concept: Functions (level 0.9, conf 0.8)
        c_known = KnowledgeConcept(
            user_id=user.id,
            name="Functions",
            current_level=0.9,
            confidence=0.8,
        )
        # Weak concept: Recursion (level 0.1, conf 0.2)
        c_gap = KnowledgeConcept(
            user_id=user.id,
            name="Recursion",
            current_level=0.1,
            confidence=0.2,
        )
        db.add_all([c_known, c_gap])
        db.commit()

        question = "How does recursion work with functions?"
        reply = assemble_and_respond(db, user.id, question)

        assert reply == "Here is an explanation focusing on recursion."
        sys_prompt = captured["system_prompt"]

        # Assert Functions is framed as already known / do not explain from scratch
        assert "Established Knowledge (DO NOT explain from scratch" in sys_prompt
        assert "Functions" in sys_prompt

        # Assert Recursion is framed as knowledge gap / focus
        assert "Knowledge Gaps (FOCUS your explanation" in sys_prompt
        assert "Recursion" in sys_prompt

    finally:
        db.close()


def test_context_assembly_includes_document_context_when_relevant(monkeypatch):
    captured = {}

    def mock_generate_response(system_prompt: str, user_message: str, **kwargs):
        captured["system_prompt"] = system_prompt
        return "Explanation grounded in notes."

    monkeypatch.setattr("app.services.ai_service.generate_response", mock_generate_response)

    db = SessionLocal()
    try:
        user = _create_user(db)

        # Uploaded study guide on sorting
        doc = Document(
            user_id=user.id,
            filename="algorithms_guide.txt",
            file_type="txt",
            status=DocumentStatus.READY,
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        chunk = DocumentChunk(
            document_id=doc.id,
            chunk_index=0,
            content="QuickSort chooses a pivot element and partitions the array in O(n log n) average time.",
        )
        db.add(chunk)
        db.commit()

        assemble_and_respond(db, user.id, "Explain QuickSort partition efficiency")

        sys_prompt = captured["system_prompt"]
        assert "Reference Notes from User's Vault (Grounding)" in sys_prompt
        assert "QuickSort chooses a pivot element" in sys_prompt

    finally:
        db.close()


def test_context_assembly_logs_evidence_after_response(monkeypatch):
    monkeypatch.setattr(
        "app.services.ai_service.generate_response",
        lambda system_prompt, user_message, **kwargs: "Mock AI response",
    )

    db = SessionLocal()
    try:
        user = _create_user(db)
        concept = KnowledgeConcept(
            user_id=user.id,
            name="SQL",
            current_level=0.3,
            confidence=0.3,
        )
        db.add(concept)
        db.commit()
        db.refresh(concept)

        initial_count = db.query(Evidence).filter(Evidence.user_id == user.id).count()

        assemble_and_respond(db, user.id, "How do SQL join queries work?")

        new_count = db.query(Evidence).filter(Evidence.user_id == user.id).count()
        assert new_count > initial_count

        ev = (
            db.query(Evidence)
            .filter(Evidence.user_id == user.id, Evidence.subject_id == concept.id)
            .first()
        )
        assert ev is not None
        assert ev.evidence_type == EvidenceType.MESSAGE_ANALYZED

    finally:
        db.close()


def test_context_assembly_is_user_scoped(monkeypatch):
    captured = {}

    def mock_generate_response(system_prompt: str, user_message: str, **kwargs):
        captured["system_prompt"] = system_prompt
        return "Response"

    monkeypatch.setattr("app.services.ai_service.generate_response", mock_generate_response)

    db = SessionLocal()
    try:
        user_a = _create_user(db)
        user_b = _create_user(db)

        # User A's private study note
        doc_a = Document(
            user_id=user_a.id,
            filename="secret_a.txt",
            file_type="txt",
            status=DocumentStatus.READY,
        )
        db.add(doc_a)
        db.commit()
        db.refresh(doc_a)

        chunk_a = DocumentChunk(
            document_id=doc_a.id,
            chunk_index=0,
            content="TOP_SECRET_CODE_WORD_ALPHA is the user A private formula.",
        )
        # User A's private preference
        pref_a = LearningPreference(
            user_id=user_a.id,
            preference_type="EXCLUSIVELY_USER_A_PREFERENCE_STYLE",
            confidence=0.9,
        )
        db.add_all([chunk_a, pref_a])
        db.commit()

        # User B queries the assistant
        assemble_and_respond(db, user_b.id, "Tell me about TOP_SECRET_CODE_WORD_ALPHA formula")

        prompt_b = captured["system_prompt"]

        # Assert no User A data leaked into User B's prompt
        assert "TOP_SECRET_CODE_WORD_ALPHA is the user A private formula" not in prompt_b
        assert "EXCLUSIVELY_USER_A_PREFERENCE_STYLE" not in prompt_b

    finally:
        db.close()
