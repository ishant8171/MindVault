"""
KnowledgeStateSnapshot — point-in-time copy of concept level and confidence.

Written automatically every N evidence events or on key milestones.
Never mutated after creation. Used to show historical progression
(e.g. Year 1 vs Year 5) without replaying or scanning all historical Evidence rows.
"""

from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.database.base import Base


class KnowledgeStateSnapshot(Base):
    __tablename__ = "knowledge_state_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    concept_id = Column(Integer, ForeignKey("knowledge_concepts.id"), nullable=False, index=True)

    level = Column(Float, nullable=False)
    confidence = Column(Float, nullable=False)

    snapshot_reason = Column(String(100), nullable=False, default="periodic")  # e.g. "periodic", "milestone"
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    concept = relationship("KnowledgeConcept", back_populates="snapshots")
    user = relationship("User")
