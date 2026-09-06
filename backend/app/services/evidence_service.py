"""
EvidenceService — Central brain update pipeline.

RULE:
    Every router, service, and event handler in later phases MUST call
    `record_evidence()` rather than writing directly to KnowledgeConcept or
    LearningPreference level/confidence fields. Direct writes bypass the
    evidence audit trail and break state explainability.

Formula & Heuristics:
    Knowledge state updates follow an iterative, explainable weighted moving adjustment:
    For each evidence event with weight w in [0.0, 1.0]:
        level_next = level + 0.25 * w * (1.0 - level)
        confidence_next = confidence + 0.15 * w * (1.0 - confidence)

    Properties of this heuristic:
    1. Bounded strictly to [0.0, 1.0] as each step moves asymptotically toward 1.0.
    2. Diminishing returns: earlier evidence makes larger adjustments; later evidence
       fine-tunes the state.
    3. Monotonic with positive signals: repeated consistent evidence increases confidence.
    4. Deterministic and replayable directly from all historical Evidence rows.
"""

from datetime import datetime, timezone
from typing import Optional, Union
from sqlalchemy.orm import Session

from app.models.evidence import Evidence, EvidenceType, SubjectType
from app.models.knowledge_concept import KnowledgeConcept
from app.models.learning_preference import LearningPreference
from app.models.knowledge_state_snapshot import KnowledgeStateSnapshot


def record_evidence(
    db: Session,
    user_id: int,
    evidence_type: Union[EvidenceType, str],
    subject_type: Union[SubjectType, str],
    subject_id: int,
    weight: float,
    summary: str,
    source_ref: Optional[str] = None,
) -> Evidence:
    """
    Record an atomic evidence signal and recompute the target subject's knowledge state.

    Design Decision on Subject Existence:
        We explicitly require the target KnowledgeConcept or LearningPreference to
        pre-exist for the specified user_id. This maintains strict referential
        integrity and prevents unvalidated polymorphic references across users.
    """
    if isinstance(evidence_type, str):
        evidence_type = EvidenceType(evidence_type)
    if isinstance(subject_type, str):
        subject_type = SubjectType(subject_type)

    # Validate that the target subject pre-exists and belongs to user_id
    if subject_type == SubjectType.KNOWLEDGE_CONCEPT:
        concept = (
            db.query(KnowledgeConcept)
            .filter(KnowledgeConcept.id == subject_id, KnowledgeConcept.user_id == user_id)
            .first()
        )
        if not concept:
            raise ValueError(f"KnowledgeConcept {subject_id} not found for user {user_id}")
    elif subject_type == SubjectType.LEARNING_PREFERENCE:
        pref = (
            db.query(LearningPreference)
            .filter(LearningPreference.id == subject_id, LearningPreference.user_id == user_id)
            .first()
        )
        if not pref:
            raise ValueError(f"LearningPreference {subject_id} not found for user {user_id}")
    else:
        raise ValueError(f"Unsupported subject_type: {subject_type}")

    # Clamp weight to [0.0, 1.0]
    clamped_weight = max(0.0, min(1.0, float(weight)))

    evidence = Evidence(
        user_id=user_id,
        evidence_type=evidence_type,
        subject_type=subject_type,
        subject_id=subject_id,
        weight=clamped_weight,
        summary=summary,
        source_ref=source_ref,
        created_at=datetime.now(timezone.utc),
    )
    db.add(evidence)
    db.commit()
    db.refresh(evidence)

    # Recompute the target subject's state from all evidence
    update_knowledge_state(db, subject_type, subject_id)

    # Snapshot check if applicable
    if subject_type == SubjectType.KNOWLEDGE_CONCEPT:
        maybe_snapshot(db, subject_id, reason="periodic")

    return evidence


def update_knowledge_state(
    db: Session,
    subject_type: Union[SubjectType, str],
    subject_id: int,
) -> Union[KnowledgeConcept, LearningPreference]:
    """
    Recompute current_level and confidence for a subject by folding across
    all historical Evidence rows targeting it.
    """
    if isinstance(subject_type, str):
        subject_type = SubjectType(subject_type)

    evidence_rows = (
        db.query(Evidence)
        .filter(Evidence.subject_type == subject_type, Evidence.subject_id == subject_id)
        .order_by(Evidence.created_at.asc(), Evidence.id.asc())
        .all()
    )

    now = datetime.now(timezone.utc)

    if subject_type == SubjectType.KNOWLEDGE_CONCEPT:
        concept = db.query(KnowledgeConcept).filter(KnowledgeConcept.id == subject_id).first()
        if not concept:
            raise ValueError(f"KnowledgeConcept {subject_id} does not exist")

        level = 0.0
        confidence = 0.1

        for ev in evidence_rows:
            w = ev.weight
            # Level updates towards signal w
            delta_level = 0.25 * w * (1.0 - level)
            level = max(0.0, min(1.0, level + delta_level))

            # Confidence increases with volume of weighted evidence
            delta_conf = 0.15 * w * (1.0 - confidence)
            confidence = max(0.0, min(1.0, confidence + delta_conf))

        concept.current_level = round(level, 4)
        concept.confidence = round(confidence, 4)
        concept.evidence_count = len(evidence_rows)
        concept.last_updated = now

        db.add(concept)
        db.commit()
        db.refresh(concept)
        return concept

    elif subject_type == SubjectType.LEARNING_PREFERENCE:
        pref = db.query(LearningPreference).filter(LearningPreference.id == subject_id).first()
        if not pref:
            raise ValueError(f"LearningPreference {subject_id} does not exist")

        confidence = 0.1
        for ev in evidence_rows:
            w = ev.weight
            delta_conf = 0.20 * w * (1.0 - confidence)
            confidence = max(0.0, min(1.0, confidence + delta_conf))

        pref.confidence = round(confidence, 4)
        pref.evidence_count = len(evidence_rows)
        pref.last_updated = now

        db.add(pref)
        db.commit()
        db.refresh(pref)
        return pref

    else:
        raise ValueError(f"Unknown subject_type: {subject_type}")


def maybe_snapshot(
    db: Session,
    concept_id: int,
    reason: str = "periodic",
) -> Optional[KnowledgeStateSnapshot]:
    """
    Conditionally captures a point-in-time snapshot of concept level and confidence.
    Triggers automatically on every 5th evidence event or when reason is explicitly specified.
    """
    concept = db.query(KnowledgeConcept).filter(KnowledgeConcept.id == concept_id).first()
    if not concept:
        return None

    # Take snapshot on every 5th evidence event or custom milestone
    should_snapshot = (
        concept.evidence_count > 0 and concept.evidence_count % 5 == 0
    ) or reason == "milestone"

    if should_snapshot:
        snapshot = KnowledgeStateSnapshot(
            user_id=concept.user_id,
            concept_id=concept.id,
            level=concept.current_level,
            confidence=concept.confidence,
            snapshot_reason=reason,
            created_at=datetime.now(timezone.utc),
        )
        db.add(snapshot)
        db.commit()
        db.refresh(snapshot)
        return snapshot

    return None
