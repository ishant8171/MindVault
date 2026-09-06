"""
Subject — connective entity.

A Subject is a topic or area that connects Documents, KnowledgeConcepts,
and Goals into a coherent cluster.  The Knowledge Graph service creates a
KnowledgeNode (type=SUBJECT) pointing back here via ref_id so the graph
stays in sync with the structured data.

Created first because KnowledgeConcept and Goal both carry a nullable FK
to this table.
"""

from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.database.base import Base


class Subject(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", back_populates="subjects")
    concepts = relationship("KnowledgeConcept", back_populates="subject")
    goals = relationship("Goal", back_populates="subject")
    documents = relationship("Document", back_populates="subject")
