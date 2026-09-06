"""
KnowledgeGraphService — Knowledge Graph management and Knowledge Delta computation.

Responsibilities:
1. Idempotent Node & Edge creation (ensure_node, link).
2. Lifecycle hooks linking new Concepts and Goals into graph nodes.
3. Knowledge Delta computation comparing task/topic required concepts against the
   user's current knowledge model.

Design Decisions:
- Concept Matching Scope:
  `compute_knowledge_delta` uses case-insensitive exact name matching against
  `KnowledgeConcept.name`. Fuzzier semantic/embedding-based concept matching is
  explicitly deferred to Future Scope.
- Gap Threshold:
  A concept is flagged as a gap (`gap: True`) if:
  (a) The user has no concept record for it, OR
  (b) The concept's current_level < 0.4, OR
  (c) The concept's confidence < 0.4.
"""

from typing import Dict, Any, List, Optional, Union
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.knowledge import KnowledgeNode, KnowledgeRelationship, NodeType, RelationshipType
from app.models.knowledge_concept import KnowledgeConcept
from app.models.goal import Goal


def ensure_node(
    db: Session,
    user_id: int,
    node_type: Union[NodeType, str],
    label: str,
    ref_id: Optional[int] = None,
) -> KnowledgeNode:
    """
    Idempotently find or create a KnowledgeNode for a user.
    Lookup matches on (user_id, node_type, ref_id) if ref_id is provided,
    otherwise matches on (user_id, node_type, label).
    """
    if isinstance(node_type, str):
        node_type = NodeType(node_type)

    query = db.query(KnowledgeNode).filter(
        KnowledgeNode.user_id == user_id,
        KnowledgeNode.node_type == node_type,
    )
    if ref_id is not None:
        existing = query.filter(KnowledgeNode.ref_id == ref_id).first()
    else:
        existing = query.filter(KnowledgeNode.label == label).first()

    if existing:
        return existing

    node = KnowledgeNode(
        user_id=user_id,
        node_type=node_type,
        label=label,
        ref_id=ref_id,
    )
    db.add(node)
    db.commit()
    db.refresh(node)
    return node


def link(
    db: Session,
    user_id: int,
    source_node_id: int,
    target_node_id: int,
    relationship_type: Union[RelationshipType, str],
) -> KnowledgeRelationship:
    """
    Idempotently connect two KnowledgeNodes with a typed relationship edge.
    Ensures both nodes belong to user_id to enforce user isolation.
    """
    if isinstance(relationship_type, str):
        relationship_type = RelationshipType(relationship_type)

    src = db.query(KnowledgeNode).filter(KnowledgeNode.id == source_node_id, KnowledgeNode.user_id == user_id).first()
    tgt = db.query(KnowledgeNode).filter(KnowledgeNode.id == target_node_id, KnowledgeNode.user_id == user_id).first()
    if not src or not tgt:
        raise ValueError(f"Nodes {source_node_id} and {target_node_id} must both exist and belong to user {user_id}")

    existing = (
        db.query(KnowledgeRelationship)
        .filter(
            KnowledgeRelationship.source_node_id == source_node_id,
            KnowledgeRelationship.target_node_id == target_node_id,
            KnowledgeRelationship.relationship_type == relationship_type,
        )
        .first()
    )
    if existing:
        return existing

    rel = KnowledgeRelationship(
        source_node_id=source_node_id,
        target_node_id=target_node_id,
        relationship_type=relationship_type,
    )
    db.add(rel)
    db.commit()
    db.refresh(rel)
    return rel


# Lifecycle hook helpers for Concept and Goal creation:
def hook_on_concept_created(db: Session, concept: KnowledgeConcept) -> KnowledgeNode:
    """
    TODO (Phase 5 Router): Call this hook inside POST /concepts/ to automatically
    create/ensure the corresponding KnowledgeNode in the user's graph.
    """
    return ensure_node(
        db,
        user_id=concept.user_id,
        node_type=NodeType.CONCEPT,
        label=concept.name,
        ref_id=concept.id,
    )


def hook_on_goal_created(db: Session, goal: Goal) -> KnowledgeNode:
    """
    TODO (Phase 5 Router): Call this hook inside POST /goals/ to automatically
    create/ensure the corresponding KnowledgeNode in the user's graph.
    """
    return ensure_node(
        db,
        user_id=goal.user_id,
        node_type=NodeType.GOAL,
        label=goal.title,
        ref_id=goal.id,
    )


def compute_knowledge_delta(
    db: Session,
    user_id: int,
    required_concept_names: List[str],
    threshold: float = 0.4,
) -> Dict[str, Dict[str, Any]]:
    """
    Compute Knowledge Delta between what a task/question requires and what the
    user currently knows.

    Returns:
        dict mapping concept_name -> {
            "has_concept": bool,
            "level": float,
            "confidence": float,
            "gap": bool
        }

    Matching Strategy:
        Performs case-insensitive name matching against the user's KnowledgeConcept rows.
        Fuzzy NLP/semantic concept matching is labeled as Future Scope.
    """
    delta_report: Dict[str, Dict[str, Any]] = {}

    # Fetch all user concepts once to minimize query overhead
    user_concepts = (
        db.query(KnowledgeConcept)
        .filter(KnowledgeConcept.user_id == user_id)
        .all()
    )
    concept_map = {c.name.strip().lower(): c for c in user_concepts}

    for req in required_concept_names:
        clean_req = req.strip()
        key = clean_req.lower()

        if key in concept_map:
            c = concept_map[key]
            # Flag as gap if either level or confidence is below threshold
            is_gap = (c.current_level < threshold) or (c.confidence < threshold)
            delta_report[clean_req] = {
                "has_concept": True,
                "level": c.current_level,
                "confidence": c.confidence,
                "gap": is_gap,
            }
        else:
            delta_report[clean_req] = {
                "has_concept": False,
                "level": 0.0,
                "confidence": 0.0,
                "gap": True,
            }

    return delta_report
