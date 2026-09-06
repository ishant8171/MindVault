from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database.session import get_db
from app.schemas.ai import AIRequest, AIResponse, ChatRequest, ChatResponse
from app.services import ai_service
from app.services.retrieval_service import retrieve_memories
from app.models.user import User


router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/test", response_model=AIResponse)
def ai_test(
    req: AIRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Authenticated endpoint to test the configured AI provider.

    Returns the assistant text and the raw provider response. The API key
    is never returned.
    """
    # All provider logic lives in ai_service
    try:
        resp = ai_service.generate_text(req.prompt, system_message=req.system_message)
    except NotImplementedError as exc:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))

    # Try to extract assistant content in a provider-agnostic way if possible
    text = ""
    try:
        # OpenAI-style response
        text = resp["choices"][0]["message"]["content"]
    except Exception:
        # Fallback: stringify the raw response
        text = str(resp)

    return AIResponse(text=text, raw=resp)


@router.post("/chat", response_model=ChatResponse)
def ai_chat(
    req: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Memory-aware chat endpoint: retrieves relevant memories for the authenticated user,
    constructs a context-injected prompt, calls the AI provider, and returns the response
    with the list of memory IDs referenced.
    """
    prompt = req.prompt.strip()

    # 1. Retrieve up to 5 relevant active memories for the authenticated user
    memories = retrieve_memories(db, user_id=current_user.id, query=prompt, limit=5)
    memories_used = [m["id"] for m in memories]

    # 2. Build system context message
    if memories:
        memory_lines = "\n".join(
            f"- [{m.get('category', 'other')}] {m['content']}" for m in memories
        )
        system_message = (
            "You are MindVault Assistant, a personal knowledge companion.\n"
            "Here are relevant memories from the user's personal vault:\n"
            f"{memory_lines}\n\n"
            "Use these memories to inform and personalize your response when appropriate."
        )
    else:
        system_message = (
            "You are MindVault Assistant, a personal knowledge companion.\n"
            "No relevant memories were found in the user's vault for this query. "
            "Please answer the user's message normally."
        )

    # 3. Call AI provider abstraction
    try:
        resp = ai_service.generate_text(prompt, system_message=system_message)
    except NotImplementedError as exc:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))

    # 4. Extract assistant reply
    text = ""
    try:
        text = resp["choices"][0]["message"]["content"]
    except Exception:
        text = str(resp)

    return ChatResponse(text=text, memories_used=memories_used)
