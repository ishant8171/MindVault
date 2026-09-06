"""
ContextAssemblyService — The Virtual Brain context orchestration pipeline.

Pipeline Steps:
1. Concept Identification: Extracts candidate required concepts via keyword heuristic.
2. Knowledge Delta: Calls KnowledgeGraphService.compute_knowledge_delta to differentiate
   what the user already knows (established) vs. what they lack (gaps).
3. Learning Preferences: Injects high-confidence learning styles (e.g. "prefers_examples").
4. Document Grounding: Retrieves user-scoped DocumentChunks via DocumentService.
5. Adaptive Prompt Assembly: Injects delta framing instructing the AI model to SKIP
   established concepts and FOCUS depth on gaps.
6. Generation: Calls ai_service.generate_response with the assembled prompt.
7. Post-Interaction Evidence: Logs interaction evidence for touched concepts so the
   Virtual Brain continues to evolve.
"""

import re
import logging
from typing import List, Dict, Optional, Tuple, Any
from sqlalchemy.orm import Session

from app.models.knowledge_concept import KnowledgeConcept
from app.models.learning_preference import LearningPreference
from app.models.evidence import EvidenceType, SubjectType
from app.models.conversation import Message
from app.services import ai_service
from app.services.knowledge_graph_service import compute_knowledge_delta
from app.services.document_service import retrieve_relevant_chunks
from app.services.evidence_service import record_evidence
from app.services.retrieval_service import retrieve_memories

logger = logging.getLogger(__name__)

# Heuristic topic map (keyword -> required concepts)
# Documented as a rule-based domain heuristic, not statistical NLU.
TOPIC_KEYWORD_MAP: Dict[str, List[str]] = {
    "recursion": ["Recursion", "Functions", "Call Stack"],
    "factorial": ["Recursion", "Functions", "Mathematical Logic"],
    "fibonacci": ["Recursion", "Dynamic Programming", "Functions"],
    "binary search": ["Binary Search", "Arrays", "Algorithms"],
    "sort": ["Sorting", "Algorithms", "Arrays"],
    "sorting": ["Sorting", "Algorithms", "Arrays"],
    "tree": ["Trees", "Data Structures"],
    "graph": ["Graphs", "Data Structures"],
    "sql": ["SQL", "Relational Databases"],
    "database": ["Databases", "Data Persistence"],
    "api": ["Web APIs", "HTTP Protocols"],
    "pointer": ["Pointers", "Memory Management"],
    "class": ["Object-Oriented Programming", "Classes"],
    "loop": ["Loops", "Control Flow"],
    "function": ["Functions", "Control Flow"],
}


def extract_required_concepts(question: str, available_concept_names: Optional[List[str]] = None) -> List[str]:
    """
    Extract required concepts for a question using a transparent keyword mapping heuristic.
    Also checks if any known user concepts are directly mentioned in the question.
    """
    q_lower = question.lower()
    concepts_found: List[str] = []

    # 1. Match against curated topic keywords
    for keyword, mapped_concepts in TOPIC_KEYWORD_MAP.items():
        if re.search(rf"\b{re.escape(keyword)}\b", q_lower):
            for c in mapped_concepts:
                if c not in concepts_found:
                    concepts_found.append(c)

    # 2. Check if known user concept names are explicitly referenced
    if available_concept_names:
        for cname in available_concept_names:
            if re.search(rf"\b{re.escape(cname.lower())}\b", q_lower):
                if cname not in concepts_found:
                    concepts_found.append(cname)

    # 3. Fallback: if no mapped concepts found, extract key noun-like words
    if not concepts_found:
        tokens = [t.capitalize() for t in re.findall(r"\b[A-Za-z]{4,}\b", question)]
        concepts_found = tokens[:3]

    return concepts_found


def assemble_system_prompt(
    delta: Dict[str, Dict[str, Any]],
    preferences: List[LearningPreference],
    document_chunks: List[Any],
    recent_memories: Optional[List[Dict[str, Any]]] = None,
    recent_messages: Optional[List[Message]] = None,
) -> str:
    """
    Assemble the personalized system prompt.
    Critically differentiates 'already known' concepts from 'knowledge gaps'.
    """
    prompt_lines = [
        "You are MindVault Assistant, an adaptive personal knowledge companion.",
        "Your role is to provide personalized, non-repetitive answers calibrated to the user's current knowledge state.",
        "",
    ]

    # Partition knowledge delta into known vs gaps
    known = [name for name, data in delta.items() if not data["gap"]]
    gaps = [name for name, data in delta.items() if data["gap"]]

    prompt_lines.append("### User Knowledge State:")
    if known:
        prompt_lines.append(
            f"- Established Knowledge (DO NOT explain from scratch; the user ALREADY KNOWS these): {', '.join(known)}."
        )
    if gaps:
        prompt_lines.append(
            f"- Knowledge Gaps (FOCUS your explanation and depth here; explain these clearly): {', '.join(gaps)}."
        )
    if not known and not gaps:
        prompt_lines.append("- Baseline knowledge: General assistance mode.")
    prompt_lines.append("")

    # Injected learning style preferences
    if preferences:
        pref_names = [p.preference_type for p in preferences]
        prompt_lines.append(f"### Adaptive Learning Style:\nThe user learns best with: {', '.join(pref_names)}. Tailor your tone and examples accordingly.")
        prompt_lines.append("")

    # Document grounding
    if document_chunks:
        prompt_lines.append("### Reference Notes from User's Vault (Grounding):")
        for chunk in document_chunks:
            prompt_lines.append(f"- Excerpt: {chunk.content.strip()[:300]}...")
        prompt_lines.append("")

    # Memory grounding
    if recent_memories:
        prompt_lines.append("### Relevant Personal Memories:")
        for m in recent_memories:
            prompt_lines.append(f"- {m['content']}")
        prompt_lines.append("")

    # Recent chat turns
    if recent_messages:
        prompt_lines.append("### Recent Conversation Context:")
        for msg in recent_messages:
            prompt_lines.append(f"- {msg.role.capitalize()}: {msg.content}")
        prompt_lines.append("")

    prompt_lines.append("Deliver a direct, helpful, personalized response honoring the above knowledge model.")
    return "\n".join(prompt_lines)


def assemble_and_respond(
    db: Session,
    user_id: int,
    question: str,
    conversation_id: Optional[int] = None,
) -> str:
    """
    Full Virtual Brain orchestration pipeline:
    (i) Identifies required concepts for the question.
    (ii) Computes Knowledge Delta (known vs gaps).
    (iii) Fetches high-confidence LearningPreferences for user.
    (iv) Retrieves user-scoped DocumentChunks.
    (v) Fetches relevant recent history / memories.
    (vi) Assembles personalized system prompt.
    (vii) Calls ai_service.generate_response.
    (viii) Emits post-interaction Evidence for touched concepts.
    (ix) Returns response text.
    """
    # 1. Fetch user's concepts to assist extraction
    user_concepts = (
        db.query(KnowledgeConcept)
        .filter(KnowledgeConcept.user_id == user_id)
        .all()
    )
    user_concept_names = [c.name for c in user_concepts]
    user_concept_dict = {c.name.strip().lower(): c for c in user_concepts}

    # 2. Extract required concepts
    required_concepts = extract_required_concepts(question, user_concept_names)

    # 3. Compute Knowledge Delta
    delta = compute_knowledge_delta(db, user_id, required_concepts, threshold=0.4)

    # 4. Fetch user's active learning preferences
    preferences = (
        db.query(LearningPreference)
        .filter(LearningPreference.user_id == user_id, LearningPreference.confidence >= 0.25)
        .order_by(LearningPreference.confidence.desc())
        .limit(3)
        .all()
    )

    # 5. Retrieve user-scoped document chunks (strictly scoped to user_id)
    document_chunks = retrieve_relevant_chunks(db, user_id=user_id, query=question, top_k=3)

    # 6. Retrieve relevant memories
    recent_memories = retrieve_memories(db, user_id=user_id, query=question, limit=3)

    # 7. Recent conversation messages if conversation_id is provided
    recent_messages = None
    if conversation_id:
        recent_messages = (
            db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(4)
            .all()
        )
        if recent_messages:
            recent_messages = list(reversed(recent_messages))

    # 8. Assemble system prompt
    system_prompt = assemble_system_prompt(
        delta=delta,
        preferences=preferences,
        document_chunks=document_chunks,
        recent_memories=recent_memories,
        recent_messages=recent_messages,
    )

    # 9. Call AI service
    response = ai_service.generate_response(system_prompt=system_prompt, user_message=question)

    # 10. Record interaction evidence for touched concepts (if they exist for this user)
    for cname in required_concepts:
        matched_concept = user_concept_dict.get(cname.strip().lower())
        if matched_concept:
            try:
                record_evidence(
                    db=db,
                    user_id=user_id,
                    evidence_type=EvidenceType.MESSAGE_ANALYZED,
                    subject_type=SubjectType.KNOWLEDGE_CONCEPT,
                    subject_id=matched_concept.id,
                    weight=0.2,
                    summary=f"User asked question referencing concept '{matched_concept.name}'",
                    source_ref="chat_interaction",
                )
            except Exception as e:
                logger.warning(f"Could not record interaction evidence for concept {cname}: {e}")

    return response
