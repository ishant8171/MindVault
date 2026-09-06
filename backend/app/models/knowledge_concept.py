"""
KnowledgeConcept — evidence-driven knowledge state for a topic/skill.

This is the successor to the flat Skill model for knowledge-state tracking.
Unlike Skill (which stores only an enum status), KnowledgeConcept stores a
numeric current_level and confidence that are updated incrementally via
EvidenceService using a weighted moving average (implemented in Phase 2).

The Skill table is kept alive for backward compatibility — see migrate_v2.py
for the one-time data copy from skills → knowledge_concepts.

Relationship to the Knowledge Graph:
    KnowledgeGraphService creates a KnowledgeNode (node_type=CONCEPT,
    ref_id=concept.id) when a KnowledgeConcept is created.  The FK lives
    on KnowledgeNode.ref_id, not here — we do not duplicate node metadata.

subject_id (nullable FK → subjects):
    A concept can optionally belong to a Subject to enable the chain:
    Document → Subject → KnowledgeConcept → Goal → Task → Evidence.
"""

from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.database.base import Base


class KnowledgeConcept(Base):
    __tablename__ = "knowledge_concepts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    name = Column(String(150), nullable=False)
    category = Column(String(100), nullable=True)   # e.g. "DSA", "Web Dev"

    # Numeric knowledge state — set only through EvidenceService, never directly
    # from a router.  Both are bounded 0.0–1.0.
    current_level = Column(Float, nullable=False, default=0.0)
    confidence = Column(Float, nullable=False, default=0.1)
    evidence_count = Column(Integer, nullable=False, default=0)

    last_updated = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Optional FK back to a Subject cluster
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=True, index=True)

    # Optional traceability link: set during migration from skills table.
    # NULL for concepts created natively in the new system.
    migrated_from_skill_id = Column(Integer, ForeignKey("skills.id"), nullable=True)

    # Relationships
    user = relationship("User", back_populates="knowledge_concepts")
    subject = relationship("Subject", back_populates="concepts")
    snapshots = relationship(
        "KnowledgeStateSnapshot",
        back_populates="concept",
        cascade="all, delete-orphan",
    )
    evidence_records = relationship(
        "Evidence",
        primaryjoin=(
            "and_(Evidence.subject_type=='knowledge_concept', "
            "foreign(Evidence.subject_id)==KnowledgeConcept.id)"
        ),
        viewonly=True,   # navigational only — evidence is written via EvidenceService
    )
