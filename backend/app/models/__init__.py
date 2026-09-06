"""
Importing every model here ensures they're all registered on Base.metadata
before create_all() runs in main.py - otherwise SQLAlchemy won't know
about a table just because its file exists somewhere in the project.
"""

from app.models.user import User
from app.models.conversation import Conversation, Message
from app.models.memory import Memory, MemoryCategory, MemorySource, MemoryStatus
from app.models.memory_history import MemoryHistory, MemoryConflict, ConflictStatus, ConflictResolution
from app.models.goal import Goal, GoalStatus, GoalPriority
from app.models.skill import Skill, SkillStatus  # Deprecated in favor of KnowledgeConcept
from app.models.knowledge import KnowledgeNode, KnowledgeRelationship, NodeType, RelationshipType
from app.models.subject import Subject
from app.models.knowledge_concept import KnowledgeConcept
from app.models.learning_preference import LearningPreference
from app.models.evidence import Evidence, EvidenceType, SubjectType
from app.models.knowledge_state_snapshot import KnowledgeStateSnapshot
from app.models.task import Task, TaskStatus
from app.models.document import Document, DocumentChunk, DocumentStatus

__all__ = [
    "User",
    "Conversation", "Message",
    "Memory", "MemoryCategory", "MemorySource", "MemoryStatus",
    "MemoryHistory", "MemoryConflict", "ConflictStatus", "ConflictResolution",
    "Goal", "GoalStatus", "GoalPriority",
    "Skill", "SkillStatus",
    "KnowledgeNode", "KnowledgeRelationship", "NodeType", "RelationshipType",
    "Subject",
    "KnowledgeConcept",
    "LearningPreference",
    "Evidence", "EvidenceType", "SubjectType",
    "KnowledgeStateSnapshot",
    "Task", "TaskStatus",
    "Document", "DocumentChunk", "DocumentStatus",
]
