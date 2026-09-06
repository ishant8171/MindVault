"""
Phase 2 tests:
Verifies EvidenceService and KnowledgeGraphService core behaviors:
- Evidence updates confidence and level upward, bounded <= 1.0
- Pre-existence validation on subject
- Knowledge delta computation flags missing and weak concepts
- Knowledge graph ensure_node and link idempotency
- Strict user isolation across concepts, evidence, nodes, and delta
"""

import uuid
import pytest
from app.database.session import SessionLocal
from app.models.user import User
from app.models.knowledge import NodeType, RelationshipType, KnowledgeNode
from app.models.knowledge_concept import KnowledgeConcept
from app.models.learning_preference import LearningPreference
from app.models.evidence import EvidenceType, SubjectType
from app.models.knowledge_state_snapshot import KnowledgeStateSnapshot
from app.services.evidence_service import record_evidence, update_knowledge_state, maybe_snapshot
from app.services.knowledge_graph_service import (
    ensure_node,
    link,
    compute_knowledge_delta,
    hook_on_concept_created,
)


def _create_user(db):
    uid = uuid.uuid4().hex[:8]
    user = User(
        username=f"u_{uid}",
        email=f"u_{uid}@test.com",
        password_hash="fakehash",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_evidence_updates_confidence_upward_and_bounded():
    db = SessionLocal()
    try:
        user = _create_user(db)
        concept = KnowledgeConcept(
            user_id=user.id,
            name="Binary Search",
            current_level=0.0,
            confidence=0.1,
        )
        db.add(concept)
        db.commit()
        db.refresh(concept)

        initial_level = concept.current_level
        initial_conf = concept.confidence

        # Record 1st evidence
        ev1 = record_evidence(
            db=db,
            user_id=user.id,
            evidence_type=EvidenceType.TASK_COMPLETED,
            subject_type=SubjectType.KNOWLEDGE_CONCEPT,
            subject_id=concept.id,
            weight=0.8,
            summary="Completed binary search implementation",
        )
        db.refresh(concept)
        assert concept.current_level > initial_level
        assert concept.confidence > initial_conf
        assert concept.evidence_count == 1

        level_after_1 = concept.current_level
        conf_after_1 = concept.confidence

        # Record 2nd evidence
        record_evidence(
            db=db,
            user_id=user.id,
            evidence_type=EvidenceType.QUIZ_RESULT,
            subject_type=SubjectType.KNOWLEDGE_CONCEPT,
            subject_id=concept.id,
            weight=0.9,
            summary="Aced quiz on binary search",
        )
        db.refresh(concept)
        assert concept.current_level > level_after_1
        assert concept.confidence > conf_after_1
        assert concept.evidence_count == 2

        # Record 20 heavy evidence events to test upper bound
        for i in range(20):
            record_evidence(
                db=db,
                user_id=user.id,
                evidence_type=EvidenceType.TASK_COMPLETED,
                subject_type=SubjectType.KNOWLEDGE_CONCEPT,
                subject_id=concept.id,
                weight=1.0,
                summary=f"Repetition {i}",
            )

        db.refresh(concept)
        assert concept.current_level <= 1.0
        assert concept.confidence <= 1.0
        assert concept.current_level > 0.95
        assert concept.confidence > 0.90

        # Also verify snapshots were captured on 5th, 10th, 15th, 20th events
        snapshots = (
            db.query(KnowledgeStateSnapshot)
            .filter(KnowledgeStateSnapshot.concept_id == concept.id)
            .all()
        )
        assert len(snapshots) >= 4

    finally:
        db.close()


def test_evidence_requires_concept_preexist():
    db = SessionLocal()
    try:
        user = _create_user(db)
        with pytest.raises(ValueError, match="not found"):
            record_evidence(
                db=db,
                user_id=user.id,
                evidence_type=EvidenceType.EXPLICIT_STATEMENT,
                subject_type=SubjectType.KNOWLEDGE_CONCEPT,
                subject_id=999999,  # Non-existent ID
                weight=0.5,
                summary="Should fail",
            )
    finally:
        db.close()


def test_knowledge_delta_flags_missing_and_weak_concepts():
    db = SessionLocal()
    try:
        user = _create_user(db)

        # Concept 1: Strong (level 0.8, confidence 0.7) -> No gap
        c1 = KnowledgeConcept(
            user_id=user.id,
            name="Python Basics",
            current_level=0.8,
            confidence=0.7,
        )
        # Concept 2: Weak (level 0.2, confidence 0.2) -> Gap
        c2 = KnowledgeConcept(
            user_id=user.id,
            name="Dynamic Programming",
            current_level=0.2,
            confidence=0.2,
        )
        db.add_all([c1, c2])
        db.commit()

        delta = compute_knowledge_delta(
            db=db,
            user_id=user.id,
            required_concept_names=["Python Basics", "dynamic programming", "Distributed Systems"],
            threshold=0.4,
        )

        # Python Basics: exists, strong -> gap is False
        assert delta["Python Basics"]["has_concept"] is True
        assert delta["Python Basics"]["gap"] is False
        assert delta["Python Basics"]["level"] == 0.8

        # dynamic programming: exists (case insensitive match), weak -> gap is True
        assert delta["dynamic programming"]["has_concept"] is True
        assert delta["dynamic programming"]["gap"] is True
        assert delta["dynamic programming"]["level"] == 0.2

        # Distributed Systems: does not exist -> gap is True
        assert delta["Distributed Systems"]["has_concept"] is False
        assert delta["Distributed Systems"]["gap"] is True
        assert delta["Distributed Systems"]["level"] == 0.0

    finally:
        db.close()


def test_knowledge_graph_ensure_node_is_idempotent():
    db = SessionLocal()
    try:
        user = _create_user(db)
        node1 = ensure_node(
            db=db,
            user_id=user.id,
            node_type=NodeType.CONCEPT,
            label="Graph Theory",
            ref_id=42,
        )
        node2 = ensure_node(
            db=db,
            user_id=user.id,
            node_type=NodeType.CONCEPT,
            label="Graph Theory",
            ref_id=42,
        )

        assert node1.id == node2.id

        # Edge idempotency test
        target_node = ensure_node(
            db=db,
            user_id=user.id,
            node_type=NodeType.CONCEPT,
            label="Trees",
            ref_id=43,
        )

        rel1 = link(db, user.id, node1.id, target_node.id, RelationshipType.RELATED_TO)
        rel2 = link(db, user.id, node1.id, target_node.id, RelationshipType.RELATED_TO)
        assert rel1.id == rel2.id

    finally:
        db.close()


def test_user_isolation():
    db = SessionLocal()
    try:
        user_a = _create_user(db)
        user_b = _create_user(db)

        # Concept created for user A
        concept_a = KnowledgeConcept(
            user_id=user_a.id,
            name="Quantum Computing",
            current_level=0.9,
            confidence=0.9,
        )
        db.add(concept_a)
        db.commit()
        db.refresh(concept_a)

        # Evidence for user A
        record_evidence(
            db=db,
            user_id=user_a.id,
            evidence_type=EvidenceType.EXPLICIT_STATEMENT,
            subject_type=SubjectType.KNOWLEDGE_CONCEPT,
            subject_id=concept_a.id,
            weight=0.9,
            summary="User A mastery",
        )

        # User B computes delta for "Quantum Computing"
        delta_b = compute_knowledge_delta(
            db=db,
            user_id=user_b.id,
            required_concept_names=["Quantum Computing"],
        )
        # User B should NOT see User A's concept; it must be flagged as missing
        assert delta_b["Quantum Computing"]["has_concept"] is False
        assert delta_b["Quantum Computing"]["gap"] is True
        assert delta_b["Quantum Computing"]["level"] == 0.0

        # User B trying to record evidence for User A's concept must fail
        with pytest.raises(ValueError, match="not found for user"):
            record_evidence(
                db=db,
                user_id=user_b.id,
                evidence_type=EvidenceType.TASK_COMPLETED,
                subject_type=SubjectType.KNOWLEDGE_CONCEPT,
                subject_id=concept_a.id,
                weight=0.5,
                summary="Attempted cross-user injection",
            )

        # Node isolation: User A's node cannot be linked by User B
        node_a = ensure_node(db, user_a.id, NodeType.CONCEPT, "Secret Node A")
        node_b = ensure_node(db, user_b.id, NodeType.CONCEPT, "Node B")
        with pytest.raises(ValueError, match="belong to user"):
            link(db, user_b.id, node_a.id, node_b.id, RelationshipType.RELATED_TO)

    finally:
        db.close()
