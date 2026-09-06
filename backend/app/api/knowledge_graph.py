from typing import List, Dict, Any
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.models.knowledge import KnowledgeNode, KnowledgeRelationship
from app.schemas.knowledge import KnowledgeNodeOut, KnowledgeRelationshipOut
from app.services.knowledge_graph_service import compute_knowledge_delta

router = APIRouter(prefix="/knowledge-graph", tags=["knowledge-graph"])


class DeltaRequest(BaseModel):
    concept_names: List[str] = Field(min_length=1)


@router.get("/nodes", response_model=List[KnowledgeNodeOut])
def get_user_nodes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve all KnowledgeNodes belonging to the authenticated user."""
    return db.query(KnowledgeNode).filter(KnowledgeNode.user_id == current_user.id).all()


@router.get("/relationships", response_model=List[KnowledgeRelationshipOut])
def get_user_relationships(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve all relationships between nodes owned by the authenticated user."""
    user_node_ids = [
        nid[0]
        for nid in db.query(KnowledgeNode.id).filter(KnowledgeNode.user_id == current_user.id).all()
    ]
    if not user_node_ids:
        return []

    return (
        db.query(KnowledgeRelationship)
        .filter(
            KnowledgeRelationship.source_node_id.in_(user_node_ids),
            KnowledgeRelationship.target_node_id.in_(user_node_ids),
        )
        .all()
    )


@router.post("/delta")
def get_knowledge_delta(
    req: DeltaRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Dict[str, Any]]:
    """
    Compute the Knowledge Delta for the authenticated user given a list of concept names.
    Returns per-concept mastery state and whether each is considered a knowledge gap.
    """
    return compute_knowledge_delta(
        db=db,
        user_id=current_user.id,
        required_concept_names=req.concept_names,
    )
