"""
DocumentService — Ingestion, text extraction, chunking, and user-scoped retrieval.

Storage Path Convention:
    Uploaded documents are stored locally on disk under:
        {settings.UPLOAD_DIR}/{user_id}/{filename_or_uuid}
    For instance: `uploads/1/lecture_notes.pdf`.
    This guarantees clean filesystem separation per user without requiring cloud storage.

Search & Ranking Mechanism:
    Retrieval uses user-scoped keyword/term-overlap frequency scoring.
    Embeddings-based vector search is explicitly marked as Future Scope and is NOT
    faked or stubbed.
"""

import os
import re
import logging
from pathlib import Path
from typing import List, Union, Tuple
from sqlalchemy.orm import Session

import pypdf
import docx

from app.core.config import settings
from app.models.document import Document, DocumentChunk, DocumentStatus

logger = logging.getLogger(__name__)


def get_user_upload_dir(user_id: int) -> Path:
    """
    Get or create the user-scoped local upload directory.
    Storage path convention: {settings.UPLOAD_DIR}/{user_id}/
    """
    base_dir = Path(settings.UPLOAD_DIR)
    user_dir = base_dir / str(user_id)
    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir


def extract_text(file_path: Union[str, Path], file_type: str) -> str:
    """
    Extract text from a PDF, DOCX, or TXT file.
    Raises ValueError on unsupported formats or extraction errors.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    ftype = file_type.lower().strip().lstrip(".")

    try:
        if ftype == "pdf":
            reader = pypdf.PdfReader(str(path))
            pages_text = []
            for i, page in enumerate(reader.pages):
                extracted = page.extract_text()
                if extracted:
                    pages_text.append(extracted)
            return "\n\n".join(pages_text).strip()

        elif ftype in ("docx", "doc"):
            doc = docx.Document(str(path))
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            return "\n\n".join(paragraphs).strip()

        elif ftype in ("txt", "md"):
            try:
                return path.read_text(encoding="utf-8").strip()
            except UnicodeDecodeError:
                return path.read_text(encoding="latin-1").strip()

        else:
            raise ValueError(f"Unsupported file type: {file_type}")

    except Exception as exc:
        logger.error(f"Text extraction failed for {path} ({file_type}): {exc}")
        raise


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """
    Splits text into chunks using a sliding word window.
    Default: ~500 words per chunk with ~50 words of overlap between adjacent chunks.
    """
    cleaned = text.strip()
    if not cleaned:
        return []

    words = cleaned.split()
    if len(words) <= chunk_size:
        return [cleaned]

    chunks: List[str] = []
    step = max(1, chunk_size - overlap)
    total_words = len(words)

    for i in range(0, total_words, step):
        window = words[i : i + chunk_size]
        chunks.append(" ".join(window))
        if i + chunk_size >= total_words:
            break

    return chunks


def process_document(db: Session, document: Document, file_path: Union[str, Path]) -> None:
    """
    Extracts text from the file, generates chunks, persists DocumentChunk records,
    and updates Document.status to READY (or FAILED on error).
    Guarantees the document is never left stuck in PROCESSING.
    """
    try:
        text = extract_text(file_path, document.file_type)
        if not text:
            logger.warning(f"No text extracted for Document {document.id}")

        chunks = chunk_text(text, chunk_size=500, overlap=50)

        # Clear any prior chunks (in case of re-processing)
        db.query(DocumentChunk).filter(DocumentChunk.document_id == document.id).delete()

        for idx, chunk_content in enumerate(chunks):
            chunk_row = DocumentChunk(
                document_id=document.id,
                chunk_index=idx,
                content=chunk_content,
            )
            db.add(chunk_row)

        document.status = DocumentStatus.READY
        db.add(document)
        db.commit()
        db.refresh(document)

    except Exception as exc:
        logger.error(f"Failed to process Document {document.id}: {exc}")
        db.rollback()
        document.status = DocumentStatus.FAILED
        db.add(document)
        db.commit()
        db.refresh(document)


def retrieve_relevant_chunks(
    db: Session,
    user_id: int,
    query: str,
    top_k: int = 5,
) -> List[DocumentChunk]:
    """
    Retrieve relevant DocumentChunks for a specific user.
    CRITICAL: Strictly filtered by Document.user_id to ensure user isolation.

    Ranking:
        Case-insensitive term-frequency overlap scoring. Chunks containing more
        matches for query tokens rank higher.
        Embeddings/semantic search is marked as Future Scope.
    """
    # Fetch all chunks belonging to documents owned by user_id
    chunks = (
        db.query(DocumentChunk)
        .join(Document, DocumentChunk.document_id == Document.id)
        .filter(
            Document.user_id == user_id,
            Document.status == DocumentStatus.READY,
        )
        .all()
    )

    if not chunks:
        return []

    # Tokenize query into alphanumeric words of length >= 2
    query_tokens = [
        t.lower()
        for t in re.findall(r"\w+", query)
        if len(t) >= 2
    ]

    if not query_tokens:
        return chunks[:top_k]

    scored_chunks: List[Tuple[float, DocumentChunk]] = []
    for chunk in chunks:
        content_lower = chunk.content.lower()
        score = 0.0

        for token in query_tokens:
            matches = content_lower.count(token)
            if matches > 0:
                # Term frequency contribution
                score += matches

        # Bonus if all query tokens appear in the chunk
        if all(token in content_lower for token in query_tokens):
            score += 5.0

        if score > 0:
            scored_chunks.append((score, chunk))

    # Sort descending by score
    scored_chunks.sort(key=lambda item: item[0], reverse=True)

    results = [item[1] for item in scored_chunks[:top_k]]
    return results
