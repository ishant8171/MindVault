from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime

from app.models.knowledge import NodeType, RelationshipType


class KnowledgeNodeCreate(BaseModel):
    node_type: NodeType
    label: str = Field(min_length=1)
    ref_id: Optional[int] = None


class KnowledgeNodeOut(BaseModel):
    id: int
    user_id: int
    node_type: NodeType
    label: str
    ref_id: Optional[int]

    class Config:
        from_attributes = True


class KnowledgeRelationshipCreate(BaseModel):
    source_node_id: int
    target_node_id: int
    relationship_type: RelationshipType


class KnowledgeRelationshipOut(BaseModel):
    id: int
    source_node_id: int
    target_node_id: int
    relationship_type: RelationshipType

    class Config:
        from_attributes = True


class TraverseResult(BaseModel):
    nodes: List[KnowledgeNodeOut]
    relationships: List[KnowledgeRelationshipOut]


class GoalGapsOut(BaseModel):
    required_skills: List[KnowledgeNodeOut]
    owned_skills: List[KnowledgeNodeOut]
    missing_skills: List[KnowledgeNodeOut]
