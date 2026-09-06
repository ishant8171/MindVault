"""
Evidence — append-only event log.

Every meaningful signal about a user's knowledge or learning style flows
through this table.  Nothing writes directly to KnowledgeConcept.confidence
or LearningPreference.confidence — EvidenceService is the single gate.

DESIGN DECISIONS:
    - Append-only: no UPDATE or DELETE from normal app logic.  Rows are
      permanent records of what happened.
    - subject_type + subject_id is a polymorphic reference:
        subject_type="knowledge_concept" → subject_id points to knowledge_concepts.id
        subject_type="learning_preference" → subject_id points to learning_preferences.id
      SQLite does not enforce cross-table FK consistency for polymorphic
      columns; the service layer validates ownership before inserting.
    - user_id is denormalized here (instead of joining through subject) to
      keep ownership checks cheap and to avoid join logic in EvidenceService.
    - source_ref is a nullable free-text field storing context like
      "task:42", "message:7", or "document:3".  No FK — sources are
      optional and heterogeneous.
"""

import enum
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship

from app.database.base import Base


class EvidenceType(str, enum.Enum):
    TASK_COMPLETED = "task_completed"
    MESSAGE_ANALYZED = "message_analyzed"
    DOCUMENT_QUERY = "document_query"
    CORRECTION = "correction"
    EXPLICIT_STATEMENT = "explicit_statement"
    QUIZ_RESULT = "quiz_result"
    OTHER = "other"


class SubjectType(str, enum.Enum):
    KNOWLEDGE_CONCEPT = "knowledge_concept"
    LEARNING_PREFERENCE = "learning_preference"


class Evidence(Base):
    __tablename__ = "evidence"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    evidence_type = Column(Enum(EvidenceType), nullable=False)

    # Polymorphic reference — see module docstring
    subject_type = Column(Enum(SubjectType), nullable=False)
    subject_id = Column(Integer, nullable=False, index=True)

    # Caller-supplied significance of this signal (0.0 = negligible, 1.0 = very strong)
    weight = Column(Float, nullable=False, default=0.5)

    # Human-readable summary of why this evidence was recorded
    summary = Column(Text, nullable=False, default="")

    # e.g. "task:42", "message:7", "document:3" — nullable; not all events
    # have a traceable source record
    source_ref = Column(String(100), nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationship (read-only navigation back to the user)
    user = relationship("User", back_populates="evidence_records")
