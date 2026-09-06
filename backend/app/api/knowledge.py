from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.schemas.knowledge import KnowledgeNodeCreate, KnowledgeNodeOut, KnowledgeRelationshipCreate, KnowledgeRelationshipOut, TraverseResult, GoalGapsOut
from app.services import knowledge_service


router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.post("/nodes/", response_model=KnowledgeNodeOut, status_code=status.HTTP_201_CREATED)
def create_node(node_in: KnowledgeNodeCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        node = knowledge_service.create_node(db, current_user, node_in.node_type, node_in.label, node_in.ref_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return node


@router.get("/nodes/{node_id}", response_model=KnowledgeNodeOut)
def read_node(node_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    node = knowledge_service.get_node(db, node_id, current_user.id)
    if not node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node not found")
    return node


@router.get("/nodes/", response_model=list[KnowledgeNodeOut])
def list_nodes(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return knowledge_service.list_nodes(db, current_user.id)


@router.delete("/nodes/{node_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_node(node_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    node = knowledge_service.get_node(db, node_id, current_user.id)
    if not node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node not found")
    knowledge_service.delete_node(db, node)
    return None


@router.post("/relationships/", response_model=KnowledgeRelationshipOut, status_code=status.HTTP_201_CREATED)
def create_relationship(rel_in: KnowledgeRelationshipCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        rel = knowledge_service.create_relationship(db, current_user, rel_in.source_node_id, rel_in.target_node_id, rel_in.relationship_type)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return rel


@router.delete("/relationships/{rel_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_relationship(rel_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    rel = db.query(knowledge_service.KnowledgeRelationship).filter(knowledge_service.KnowledgeRelationship.id == rel_id).first()
    if not rel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Relationship not found")
    # ensure ownership via source node
    src = knowledge_service.get_node(db, rel.source_node_id, current_user.id)
    if not src:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Relationship not found")
    knowledge_service.delete_relationship(db, rel)
    return None


@router.get("/traverse/", response_model=TraverseResult)
def traverse(
    start: int = Query(..., description="start node id"),
    depth: int = Query(default=1, ge=1, le=10, description="traversal depth"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    start_node = knowledge_service.get_node(db, start, current_user.id)
    if not start_node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Start node not found")
    nodes, rels = knowledge_service.traverse(db, current_user.id, start, depth)
    return {"nodes": nodes, "relationships": rels}


@router.get("/goal_gaps/{goal_node_id}", response_model=GoalGapsOut)
def goal_gaps(goal_node_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    goal_node = knowledge_service.get_node(db, goal_node_id, current_user.id)
    if not goal_node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal node not found")
    try:
        required, owned, missing = knowledge_service.goal_skill_gaps(db, current_user, goal_node_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return {"required_skills": required, "owned_skills": owned, "missing_skills": missing}
