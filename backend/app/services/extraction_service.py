"""Memory extraction service.

Calls `ai_service` to suggest memory candidates from free text and parses
the provider response into structured candidates. Does NOT persist.
"""
import json
from typing import List

from app.services import ai_service
from app.schemas.memory import MemoryCandidate
from app.models.memory import MemoryCategory


SYSTEM_PROMPT = (
    "You are a helpful extractor. Given user text, return a JSON array of "
    "candidate memories. Each candidate must be an object with: 'content' (string), "
    "optional 'slot_key' (string), optional 'category' (one of: personal, preference, goal, skill, education, project, habit, interest, important_event, temporary, other), "
    "and optional 'confidence_score' (0.0-1.0). Output ONLY the JSON array."
)


def extract_candidates(text: str) -> List[MemoryCandidate]:
    # Query the AI provider with the system prompt and the user's text.
    resp = ai_service.generate_text(prompt=text, system_message=SYSTEM_PROMPT)

    # Attempt to extract text content from provider response
    raw_text = ""
    try:
        raw_text = resp["choices"][0]["message"]["content"]
    except Exception:
        # Fallback: try to stringify response
        raw_text = str(resp)

    # Attempt to parse JSON from the assistant's content
    try:
        parsed = json.loads(raw_text)
    except Exception:
        # If parsing fails, return empty list
        return []

    candidates: List[MemoryCandidate] = []
    for item in parsed:
        # Normalize category if provided
        cat = None
        if "category" in item and item["category"]:
            try:
                cat = MemoryCategory(item["category"])
            except Exception:
                cat = MemoryCategory.OTHER

        candidate = MemoryCandidate(
            content=item.get("content", ""),
            slot_key=item.get("slot_key"),
            category=cat,
            confidence_score=item.get("confidence_score", 0.5),
        )
        candidates.append(candidate)

    return candidates
