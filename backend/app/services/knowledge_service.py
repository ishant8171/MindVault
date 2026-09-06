from sqlalchemy.orm import Session
from typing import List, Tuple, Set

from app.models.knowledge import KnowledgeNode, KnowledgeRelationship, NodeType, RelationshipType
from app.models.user import User
from app.models.goal import Goal
from app.models.skill import Skill


ALLOWED_RELATION_PAIRS = {
    RelationshipType.HAS_GOAL: (NodeType.USER, NodeType.GOAL),
    RelationshipType.HAS_SKILL: (NodeType.USER, NodeType.SKILL),
    RelationshipType.REQUIRES: (NodeType.GOAL, NodeType.SKILL),
    RelationshipType.LEARNING: (NodeType.USER, NodeType.SKILL),
    RelationshipType.RELATED_TO: (NodeType.SKILL, NodeType.SKILL),
    RelationshipType.WORKING_ON: (NodeType.USER, NodeType.PROJECT),
}


def create_node(db: Session, user: User, node_type: NodeType, label: str, ref_id: int | None = None) -> KnowledgeNode:
    # validate ref_id ownership for GOAL/SKILL/USER types
    if ref_id is not None:
        if node_type == NodeType.GOAL:
            g = db.query(Goal).filter(Goal.id == ref_id).first()
            if not g or g.user_id != user.id:
                raise ValueError("ref_id goal not found or not owned by user")
        if node_type == NodeType.SKILL:
            s = db.query(Skill).filter(Skill.id == ref_id).first()
            if not s or s.user_id != user.id:
                raise ValueError("ref_id skill not found or not owned by user")
        if node_type == NodeType.USER:
            if ref_id != user.id:
                raise ValueError("user node ref_id must point to current user")
        if node_type == NodeType.MEMORY:
            from app.models.memory import Memory, MemoryStatus
            m = db.query(Memory).filter(Memory.id == ref_id).first()
            if not m or m.user_id != user.id or m.status == MemoryStatus.DELETED:
                raise ValueError("ref_id memory not found or not owned by user")
        if node_type == NodeType.CONCEPT:
            from app.models.knowledge_concept import KnowledgeConcept
            c = db.query(KnowledgeConcept).filter(KnowledgeConcept.id == ref_id).first()
            if not c or c.user_id != user.id:
                raise ValueError("ref_id concept not found or not owned by user")
        if node_type == NodeType.DOCUMENT:
            from app.models.document import Document
            d = db.query(Document).filter(Document.id == ref_id).first()
            if not d or d.user_id != user.id:
                raise ValueError("ref_id document not found or not owned by user")
        if node_type == NodeType.SUBJECT:
            from app.models.subject import Subject
            sub = db.query(Subject).filter(Subject.id == ref_id).first()
            if not sub or sub.user_id != user.id:
                raise ValueError("ref_id subject not found or not owned by user")

    node = KnowledgeNode(user_id=user.id, node_type=node_type, label=label, ref_id=ref_id)
    db.add(node)
    db.commit()
    db.refresh(node)
    return node


def get_node(db: Session, node_id: int, user_id: int) -> KnowledgeNode | None:
    return db.query(KnowledgeNode).filter(KnowledgeNode.id == node_id, KnowledgeNode.user_id == user_id).first()


def list_nodes(db: Session, user_id: int) -> List[KnowledgeNode]:
    return db.query(KnowledgeNode).filter(KnowledgeNode.user_id == user_id).all()


def delete_node(db: Session, node: KnowledgeNode) -> None:
    # cascade delete relationships
    db.query(KnowledgeRelationship).filter((KnowledgeRelationship.source_node_id == node.id) | (KnowledgeRelationship.target_node_id == node.id)).delete(synchronize_session=False)
    db.delete(node)
    db.commit()


def create_relationship(db: Session, user: User, source_id: int, target_id: int, rel_type: RelationshipType) -> KnowledgeRelationship:
    src = get_node(db, source_id, user.id)
    tgt = get_node(db, target_id, user.id)
    if not src or not tgt:
        raise ValueError("source or target node not found or not owned by user")

    allowed = ALLOWED_RELATION_PAIRS.get(rel_type)
    if allowed:
        if not (src.node_type == allowed[0] and tgt.node_type == allowed[1]):
            raise ValueError(f"Invalid node types for relationship {rel_type}")

    # prevent duplicate
    exists = db.query(KnowledgeRelationship).filter(
        KnowledgeRelationship.source_node_id == source_id,
        KnowledgeRelationship.target_node_id == target_id,
        KnowledgeRelationship.relationship_type == rel_type,
    ).first()
    if exists:
        return exists

    rel = KnowledgeRelationship(source_node_id=source_id, target_node_id=target_id, relationship_type=rel_type)
    db.add(rel)
    db.commit()
    db.refresh(rel)
    return rel


def delete_relationship(db: Session, rel: KnowledgeRelationship) -> None:
    db.delete(rel)
    db.commit()


def traverse(db: Session, user_id: int, start_node_id: int, depth: int = 1) -> Tuple[List[KnowledgeNode], List[KnowledgeRelationship]]:
    # simple BFS outward traversal following source->target edges up to depth
    nodes: dict[int, KnowledgeNode] = {}
    rels: dict[int, KnowledgeRelationship] = {}
    frontier = {start_node_id}
    visited: Set[int] = set()
    for d in range(depth):
        if not frontier:
            break
        next_frontier = set()
        for sid in frontier:
            if sid in visited:
                continue
            visited.add(sid)
            n = get_node(db, sid, user_id)
            if not n:
                continue
            nodes[n.id] = n
            # outgoing
            outgoing = db.query(KnowledgeRelationship).filter(KnowledgeRelationship.source_node_id == sid).all()
            for r in outgoing:
                rels[r.id] = r
                tgt = get_node(db, r.target_node_id, user_id)
                if tgt:
                    nodes[tgt.id] = tgt
                    if tgt.id not in visited:
                        next_frontier.add(tgt.id)
        frontier = next_frontier

    return list(nodes.values()), list(rels.values())


def goal_skill_gaps(db: Session, user: User, goal_node_id: int) -> Tuple[List[KnowledgeNode], List[KnowledgeNode], List[KnowledgeNode]]:
    # returns required_skills, owned_skills, missing_skills
    goal_node = get_node(db, goal_node_id, user.id)
    if not goal_node or goal_node.node_type != NodeType.GOAL:
        raise ValueError("goal node not found or not a goal")

    # required skills: relationships from goal -> skill with REQUIRES
    req_rels = db.query(KnowledgeRelationship).filter(KnowledgeRelationship.source_node_id == goal_node_id, KnowledgeRelationship.relationship_type == RelationshipType.REQUIRES).all()
    required_skill_ids = [r.target_node_id for r in req_rels]
    required_skills = [get_node(db, sid, user.id) for sid in required_skill_ids]
    required_skills = [s for s in required_skills if s]

    # owned skills: user -> skill HAS_SKILL
    user_node = db.query(KnowledgeNode).filter(KnowledgeNode.user_id == user.id, KnowledgeNode.node_type == NodeType.USER, KnowledgeNode.ref_id == user.id).first()
    owned_skill_nodes = []
    if user_node:
        rels = db.query(KnowledgeRelationship).filter(KnowledgeRelationship.source_node_id == user_node.id, KnowledgeRelationship.relationship_type.in_([RelationshipType.HAS_SKILL, RelationshipType.LEARNING])).all()
        owned_ids = [r.target_node_id for r in rels]
        owned_skill_nodes = [get_node(db, sid, user.id) for sid in owned_ids]
        owned_skill_nodes = [s for s in owned_skill_nodes if s]

    owned_ids = {s.id for s in owned_skill_nodes}
    missing = [s for s in required_skills if s.id not in owned_ids]
    return required_skills, owned_skill_nodes, missing
