import os
from typing import List, Optional
from datetime import datetime, timezone
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.models.document import Document, DocumentChunk, DocumentStatus
from app.models.subject import Subject
from app.models.knowledge import NodeType, RelationshipType
from app.schemas.document import DocumentOut, DocumentStatusOut
from app.services.document_service import get_user_upload_dir, process_document
from app.services.knowledge_graph_service import ensure_node, link

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("/", response_model=List[DocumentOut])
def list_documents(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all documents for the authenticated user."""
    docs = (
        db.query(Document)
        .filter(Document.user_id == current_user.id)
        .order_by(Document.upload_date.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    result = []
    for d in docs:
        chunk_count = db.query(DocumentChunk).filter(DocumentChunk.document_id == d.id).count()
        out = DocumentOut.model_validate(d)
        out.chunk_count = chunk_count
        result.append(out)
    return result


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve document metadata for the authenticated user."""
    doc = db.query(Document).filter(Document.id == document_id, Document.user_id == current_user.id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    chunk_count = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).count()
    out = DocumentOut.model_validate(doc)
    out.chunk_count = chunk_count
    return out


@router.get("/{document_id}/status", response_model=DocumentStatusOut)
def get_document_status(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve processing status and chunk count for a document."""
    doc = db.query(Document).filter(Document.id == document_id, Document.user_id == current_user.id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    chunk_count = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).count()
    return DocumentStatusOut(
        id=doc.id,
        filename=doc.filename,
        status=doc.status,
        chunk_count=chunk_count,
    )


@router.post("/upload", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
def upload_document(
    file: UploadFile = File(...),
    subject_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a document (PDF, DOCX, TXT), store it locally in a user-isolated
    directory, extract text, chunk it, and save chunks.
    Processing is performed synchronously for this scope; async queuing is Future Scope.
    """
    if subject_id is not None:
        subject = (
            db.query(Subject)
            .filter(Subject.id == subject_id, Subject.user_id == current_user.id)
            .first()
        )
        if not subject:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Subject not found or not owned")

    filename = Path(file.filename).name
    ext = Path(filename).suffix.lstrip(".").lower() or "txt"

    # Save to user upload directory
    user_dir = get_user_upload_dir(current_user.id)
    saved_path = user_dir / f"{datetime.now(timezone.utc).timestamp()}_{filename}"

    with open(saved_path, "wb") as f:
        f.write(file.file.read())

    # Create Document record
    doc = Document(
        user_id=current_user.id,
        filename=filename,
        file_type=ext,
        status=DocumentStatus.PROCESSING,
        subject_id=subject_id,
        upload_date=datetime.now(timezone.utc),
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Process document (extract, chunk, update status to READY or FAILED)
    process_document(db, doc, saved_path)

    # Wire into Knowledge Graph if subject_id is provided
    if doc.subject_id and doc.status == DocumentStatus.READY:
        try:
            doc_node = ensure_node(
                db=db,
                user_id=current_user.id,
                node_type=NodeType.DOCUMENT,
                label=doc.filename,
                ref_id=doc.id,
            )
            subj_node = ensure_node(
                db=db,
                user_id=current_user.id,
                node_type=NodeType.SUBJECT,
                label=subject.name,
                ref_id=subject.id,
            )
            link(
                db=db,
                user_id=current_user.id,
                source_node_id=subj_node.id,
                target_node_id=doc_node.id,
                relationship_type=RelationshipType.COVERS,
            )
        except Exception:
            pass

    chunk_count = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).count()
    out = DocumentOut.model_validate(doc)
    out.chunk_count = chunk_count
    return out


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a document and its chunks owned by the authenticated user."""
    doc = db.query(Document).filter(Document.id == document_id, Document.user_id == current_user.id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    db.delete(doc)
    db.commit()
    return None
