from typing import List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.models.knowledge_concept import KnowledgeConcept
from app.models.subject import Subject
from app.models.knowledge import NodeType, RelationshipType
from app.models.evidence import EvidenceType, SubjectType
from app.schemas.concept import ConceptCreate, ConceptOut, ConceptUpdate
from app.services.knowledge_graph_service import (
    hook_on_concept_created,
    ensure_node,
    link,
)

router = APIRouter(prefix="/concepts", tags=["concepts"])


@router.get("/", response_model=List[ConceptOut])
def list_concepts(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all KnowledgeConcepts for the authenticated user."""
    return (
        db.query(KnowledgeConcept)
        .filter(KnowledgeConcept.user_id == current_user.id)
        .order_by(KnowledgeConcept.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.get("/{concept_id}", response_model=ConceptOut)
def get_concept(
    concept_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve a single KnowledgeConcept owned by the authenticated user."""
    concept = (
        db.query(KnowledgeConcept)
        .filter(KnowledgeConcept.id == concept_id, KnowledgeConcept.user_id == current_user.id)
        .first()
    )
    if not concept:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Concept not found")
    return concept


@router.post("/", response_model=ConceptOut, status_code=status.HTTP_201_CREATED)
def create_concept(
    concept_in: ConceptCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Manually create a KnowledgeConcept (e.g. user adds a baseline topic).
    Wires the created concept directly into the Knowledge Graph.
    """
    if concept_in.subject_id:
        subject = (
            db.query(Subject)
            .filter(Subject.id == concept_in.subject_id, Subject.user_id == current_user.id)
            .first()
        )
        if not subject:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Subject not found or not owned")

    concept = KnowledgeConcept(
        user_id=current_user.id,
        name=concept_in.name.strip(),
        category=concept_in.category,
        current_level=concept_in.initial_level if concept_in.initial_level is not None else 0.0,
        confidence=concept_in.initial_confidence if concept_in.initial_confidence is not None else 0.1,
        evidence_count=0,
        subject_id=concept_in.subject_id,
        created_at=datetime.now(timezone.utc),
    )
    db.add(concept)
    db.commit()
    db.refresh(concept)

    # Wire into Knowledge Graph: ensure node exists for concept
    concept_node = hook_on_concept_created(db, concept)

    # If linked to subject, link concept node to subject node
    if concept.subject_id:
        subject_node = ensure_node(
            db=db,
            user_id=current_user.id,
            node_type=NodeType.SUBJECT,
            label=subject.name,
            ref_id=subject.id,
        )
        link(
            db=db,
            user_id=current_user.id,
            source_node_id=subject_node.id,
            target_node_id=concept_node.id,
            relationship_type=RelationshipType.COVERS,
        )

    return concept


@router.patch("/{concept_id}", response_model=ConceptOut)
def update_concept(
    concept_id: int,
    concept_in: ConceptUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update metadata of a KnowledgeConcept (confidence/level are driven by EvidenceService)."""
    concept = (
        db.query(KnowledgeConcept)
        .filter(KnowledgeConcept.id == concept_id, KnowledgeConcept.user_id == current_user.id)
        .first()
    )
    if not concept:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Concept not found")

    if concept_in.name is not None:
        concept.name = concept_in.name.strip()
    if concept_in.category is not None:
        concept.category = concept_in.category
    if concept_in.subject_id is not None:
        subject = (
            db.query(Subject)
            .filter(Subject.id == concept_in.subject_id, Subject.user_id == current_user.id)
            .first()
        )
        if not subject:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Subject not found or not owned")
        concept.subject_id = concept_in.subject_id

    db.add(concept)
    db.commit()
    db.refresh(concept)
    return concept


@router.delete("/{concept_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_concept(
    concept_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a KnowledgeConcept owned by current user."""
    concept = (
        db.query(KnowledgeConcept)
        .filter(KnowledgeConcept.id == concept_id, KnowledgeConcept.user_id == current_user.id)
        .first()
    )
    if not concept:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Concept not found")
    db.delete(concept)
    db.commit()
    return None
