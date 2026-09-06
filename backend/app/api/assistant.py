from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.models.conversation import Conversation, Message
from app.schemas.assistant import AskRequest, AskResponse
from app.services.ai_service import AIProviderNotConfiguredError
from app.services.context_assembly_service import assemble_and_respond

router = APIRouter(prefix="/assistant", tags=["assistant"])


@router.post("/ask", response_model=AskResponse)
def ask_assistant(
    req: AskRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Primary interface to the Virtual Brain:
    1. Ensures or creates a conversation session for raw chat turn logging.
    2. Logs the incoming user turn to the Message table.
    3. Executes the full ContextAssemblyService pipeline.
    4. Logs the assistant reply to the Message table.
    5. Returns the personalized response.
    """
    # 1. Resolve or create conversation
    conv = None
    if req.conversation_id:
        conv = (
            db.query(Conversation)
            .filter(Conversation.id == req.conversation_id, Conversation.user_id == current_user.id)
            .first()
        )
    if not conv:
        conv = Conversation(
            user_id=current_user.id,
            title=req.question.strip()[:60],
            created_at=datetime.now(timezone.utc),
        )
        db.add(conv)
        db.commit()
        db.refresh(conv)

    # 2. Record user Message turn
    user_msg = Message(
        conversation_id=conv.id,
        role="user",
        content=req.question.strip(),
        created_at=datetime.now(timezone.utc),
    )
    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)

    # 3. Call ContextAssemblyService
    try:
        reply_text = assemble_and_respond(
            db=db,
            user_id=current_user.id,
            question=req.question.strip(),
            conversation_id=conv.id,
        )
    except AIProviderNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Assistant processing failed: {exc}",
        )

    # 4. Record assistant Message turn
    assistant_msg = Message(
        conversation_id=conv.id,
        role="assistant",
        content=reply_text,
        created_at=datetime.now(timezone.utc),
    )
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)

    return AskResponse(
        response=reply_text,
        conversation_id=conv.id,
        user_message_id=user_msg.id,
        assistant_message_id=assistant_msg.id,
    )
