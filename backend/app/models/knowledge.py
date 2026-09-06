import enum

from sqlalchemy import Column, Integer, String, ForeignKey, Enum

from app.database.base import Base


class NodeType(str, enum.Enum):
    USER = "user"
    GOAL = "goal"
    SKILL = "skill"
    CONCEPT = "concept"
    SUBJECT = "subject"
    DOCUMENT = "document"
    PROJECT = "project"
    INTEREST = "interest"
    PREFERENCE = "preference"
    MEMORY = "memory"


class RelationshipType(str, enum.Enum):
    HAS_GOAL = "has_goal"
    HAS_SKILL = "has_skill"
    HAS_CONCEPT = "has_concept"
    LEARNING = "learning"
    WORKING_ON = "working_on"
    INTERESTED_IN = "interested_in"
    PREFERS = "prefers"
    RELATED_TO = "related_to"
    REQUIRES = "requires"
    COMPLETED = "completed"
    COVERS = "covers"
    LINKED_TO = "linked_to"
    EVIDENCE_FOR = "evidence_for"


class KnowledgeNode(Base):
    """
    A node in the personal knowledge graph. `ref_id` optionally points back
    to the originating row (e.g. a Goal id) so the graph stays in sync with
    the structured data instead of being a separate, divergent copy.
    """
    __tablename__ = "knowledge_nodes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    node_type = Column(Enum(NodeType), nullable=False)
    label = Column(String(255), nullable=False)
    ref_id = Column(Integer, nullable=True)  # e.g. goals.id, skills.id, memories.id


class KnowledgeRelationship(Base):
    __tablename__ = "knowledge_relationships"

    id = Column(Integer, primary_key=True, index=True)
    source_node_id = Column(Integer, ForeignKey("knowledge_nodes.id"), nullable=False, index=True)
    target_node_id = Column(Integer, ForeignKey("knowledge_nodes.id"), nullable=False, index=True)
    relationship_type = Column(Enum(RelationshipType), nullable=False)
