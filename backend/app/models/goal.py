import enum
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum, Float
from sqlalchemy.orm import relationship

from app.database.base import Base


class GoalStatus(str, enum.Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class GoalPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Goal(Base):
    __tablename__ = "goals"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    priority = Column(Enum(GoalPriority), nullable=False, default=GoalPriority.MEDIUM)
    deadline = Column(DateTime, nullable=True)
    status = Column(Enum(GoalStatus), nullable=False, default=GoalStatus.NOT_STARTED)
    progress = Column(Float, nullable=False, default=0.0)  # 0.0 - 1.0

    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=True, index=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="goals")
    subject = relationship("Subject", back_populates="goals")
    tasks = relationship("Task", back_populates="goal", cascade="all, delete-orphan")
