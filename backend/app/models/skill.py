import enum
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship

from app.database.base import Base


class SkillStatus(str, enum.Enum):
    NOT_STARTED = "not_started"
    LEARNING = "learning"
    COMPLETED = "completed"


class Skill(Base):
    """
    [DEPRECATED] Flat skill entity with static enum status.
    Kept for backward compatibility and test stability.
    The primary knowledge-state representation is now KnowledgeConcept,
    which supports numeric level, confidence, and evidence-driven updates.
    """
    __tablename__ = "skills"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    name = Column(String(150), nullable=False)
    category = Column(String(100), nullable=True)  # e.g. "DSA", "Web Dev"
    status = Column(Enum(SkillStatus), nullable=False, default=SkillStatus.NOT_STARTED)

    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="skills")
