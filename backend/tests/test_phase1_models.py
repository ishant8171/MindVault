"""
Phase 1 smoke tests:
Verifies that all new models (Evidence, KnowledgeConcept, LearningPreference,
KnowledgeStateSnapshot, Task, Document, DocumentChunk, Subject) can be instantiated,
queried, and have proper relationships in the database without regression.
"""

from datetime import datetime, timezone
import pytest
from sqlalchemy import inspect
from app.database.base import engine
from app.database.session import SessionLocal
from app.models import (
    User,
    Goal,
    Skill,
    Subject,
    KnowledgeConcept,
    LearningPreference,
    Evidence,
    EvidenceType,
    SubjectType,
    KnowledgeStateSnapshot,
    Task,
    TaskStatus,
    Document,
    DocumentChunk,
    DocumentStatus,
)


def test_tables_exist():
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    expected_tables = {
        "users",
        "conversations",
        "messages",
        "memories",
        "memory_history",
        "memory_conflicts",
        "goals",
        "skills",
        "knowledge_nodes",
        "knowledge_relationships",
        "subjects",
        "knowledge_concepts",
        "learning_preferences",
        "evidence",
        "knowledge_state_snapshots",
        "tasks",
        "documents",
        "document_chunks",
    }
    for t in expected_tables:
        assert t in table_names, f"Table '{t}' missing from database schema."


def test_models_crud_and_relationships():
    db = SessionLocal()
    try:
        # 1. Create a dummy user
        user = User(
            username=f"phase1_{datetime.now(timezone.utc).timestamp()}",
            email=f"phase1_{datetime.now(timezone.utc).timestamp()}@test.com",
            password_hash="fakehash",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # 2. Subject
        subject = Subject(user_id=user.id, name="Computer Science", description="Core CS concepts")
        db.add(subject)
        db.commit()
        db.refresh(subject)
        assert subject.id is not None

        # 3. KnowledgeConcept linked to Subject
        concept = KnowledgeConcept(
            user_id=user.id,
            name="Recursion",
            category="Algorithms",
            current_level=0.4,
            confidence=0.6,
            subject_id=subject.id,
        )
        db.add(concept)
        db.commit()
        db.refresh(concept)
        assert concept.id is not None
        assert concept.subject.name == "Computer Science"

        # 4. LearningPreference
        pref = LearningPreference(
            user_id=user.id,
            preference_type="prefers_examples",
            confidence=0.75,
            evidence_count=3,
        )
        db.add(pref)
        db.commit()
        db.refresh(pref)
        assert pref.id is not None

        # 5. Evidence (polymorphic ref to KnowledgeConcept)
        ev1 = Evidence(
            user_id=user.id,
            evidence_type=EvidenceType.TASK_COMPLETED,
            subject_type=SubjectType.KNOWLEDGE_CONCEPT,
            subject_id=concept.id,
            weight=0.5,
            summary="Solved recursion problem",
            source_ref="task:101",
        )
        db.add(ev1)

        # Evidence (polymorphic ref to LearningPreference)
        ev2 = Evidence(
            user_id=user.id,
            evidence_type=EvidenceType.EXPLICIT_STATEMENT,
            subject_type=SubjectType.LEARNING_PREFERENCE,
            subject_id=pref.id,
            weight=0.8,
            summary="User explicitly asked for more code examples",
        )
        db.add(ev2)
        db.commit()

        # 6. KnowledgeStateSnapshot
        snapshot = KnowledgeStateSnapshot(
            user_id=user.id,
            concept_id=concept.id,
            level=0.4,
            confidence=0.6,
            snapshot_reason="milestone",
        )
        db.add(snapshot)
        db.commit()
        db.refresh(snapshot)
        assert snapshot.id is not None
        assert snapshot.concept.name == "Recursion"

        # 7. Goal + Task
        goal = Goal(
            user_id=user.id,
            title="Master Algorithms",
            subject_id=subject.id,
        )
        db.add(goal)
        db.commit()
        db.refresh(goal)

        task = Task(
            user_id=user.id,
            goal_id=goal.id,
            title="Implement Merge Sort",
            status=TaskStatus.IN_PROGRESS,
            related_concept_ids=f"[{concept.id}]",
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        assert task.goal.title == "Master Algorithms"
        assert task.goal.subject.name == "Computer Science"

        # 8. Document + DocumentChunk
        doc = Document(
            user_id=user.id,
            filename="dsa_notes.pdf",
            file_type="pdf",
            status=DocumentStatus.READY,
            subject_id=subject.id,
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        chunk = DocumentChunk(
            document_id=doc.id,
            chunk_index=0,
            content="Divide and conquer algorithms partition a problem into subproblems...",
        )
        db.add(chunk)
        db.commit()
        db.refresh(chunk)
        assert chunk.document.filename == "dsa_notes.pdf"
        assert len(doc.chunks) == 1

        # Clean up created test entities
        db.delete(user)
        db.commit()

    finally:
        db.close()
