"""
LearningPreference — inferred or explicitly stated preference about how
the user learns best.

Examples of preference_type values (free-text string, not an enum, so new
preference types can be added without a schema migration):
    "prefers_examples"
    "prefers_visual"
    "prefers_step_by_step"
    "prefers_concise"
    "wants_analogies"

Both explicit statements ("I learn better with examples") and inferred
patterns ("user repeatedly asks for examples") are recorded here via the
EvidenceService using the same weighted moving average that updates
KnowledgeConcept confidence.  The logic is intentionally shared — see
EvidenceService in Phase 2.
"""

from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.database.base import Base


class LearningPreference(Base):
    __tablename__ = "learning_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Free-text preference type — do not use an enum; new preferences must
    # be addable without schema changes.
    preference_type = Column(String(100), nullable=False)

    confidence = Column(Float, nullable=False, default=0.1)   # 0.0–1.0
    evidence_count = Column(Integer, nullable=False, default=0)

    last_updated = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", back_populates="learning_preferences")
    evidence_records = relationship(
        "Evidence",
        primaryjoin=(
            "and_(Evidence.subject_type=='learning_preference', "
            "foreign(Evidence.subject_id)==LearningPreference.id)"
        ),
        viewonly=True,
    )
