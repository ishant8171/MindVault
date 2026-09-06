"""
Phase 3 tests:
Verifies DocumentService functionality:
- Text extraction from PDF and DOCX fixtures
- Sliding-window word chunking with overlap
- End-to-end document processing (status transitions to READY)
- Keyword overlap ranking for chunk retrieval
- Strict user scoping: User A cannot retrieve User B's document chunks
- Error handling: Corrupted/bad file input marks document FAILED gracefully
"""

import uuid
from pathlib import Path
import pytest

from app.database.session import SessionLocal
from app.models.user import User
from app.models.document import Document, DocumentChunk, DocumentStatus
from app.services.document_service import (
    extract_text,
    chunk_text,
    process_document,
    retrieve_relevant_chunks,
)

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def _create_user(db):
    uid = uuid.uuid4().hex[:8]
    user = User(
        username=f"doc_u_{uid}",
        email=f"doc_u_{uid}@test.com",
        password_hash="fakehash",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_extract_text_from_pdf_fixture():
    pdf_path = FIXTURES_DIR / "sample.pdf"
    assert pdf_path.exists(), "sample.pdf fixture is missing"
    text = extract_text(pdf_path, "pdf")
    assert "Personal Knowledge Model" in text
    assert "Knowledge Delta Retrieval" in text


def test_extract_text_from_docx_fixture():
    docx_path = FIXTURES_DIR / "sample.docx"
    assert docx_path.exists(), "sample.docx fixture is missing"
    text = extract_text(docx_path, "docx")
    assert "MindVault Architecture" in text
    assert "accumulated evidence" in text


def test_chunking_produces_expected_chunk_count_and_overlap():
    # Construct a synthetic document of 1200 words
    words = [f"word{i}" for i in range(1200)]
    text = " ".join(words)

    # Chunk size = 500, overlap = 50 -> step = 450
    # Chunk 0: 0..500
    # Chunk 1: 450..950
    # Chunk 2: 900..1200
    # Expected chunks = 3
    chunks = chunk_text(text, chunk_size=500, overlap=50)
    assert len(chunks) == 3

    # Check first chunk word count
    assert len(chunks[0].split()) == 500

    # Check overlap between chunk 0 and chunk 1:
    # Last 50 words of chunk 0 should equal first 50 words of chunk 1
    chunk_0_last_50 = chunks[0].split()[-50:]
    chunk_1_first_50 = chunks[1].split()[:50]
    assert chunk_0_last_50 == chunk_1_first_50


def test_retrieve_relevant_chunks_ranks_query_matches_higher():
    db = SessionLocal()
    try:
        user = _create_user(db)

        # Create a document
        doc = Document(
            user_id=user.id,
            filename="algo_study.txt",
            file_type="txt",
            status=DocumentStatus.READY,
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        # Chunk A: Contains "recursion" once
        chunk_a = DocumentChunk(
            document_id=doc.id,
            chunk_index=0,
            content="Algorithms often use recursion for divide and conquer strategies.",
        )
        # Chunk B: Contains "recursion" three times and "trees"
        chunk_b = DocumentChunk(
            document_id=doc.id,
            chunk_index=1,
            content="Recursion is fundamental. In recursion, a base case prevents infinite recursion. Useful for trees.",
        )
        # Chunk C: Unrelated topic
        chunk_c = DocumentChunk(
            document_id=doc.id,
            chunk_index=2,
            content="Database indexes like B-trees improve SQL query performance.",
        )
        db.add_all([chunk_a, chunk_b, chunk_c])
        db.commit()

        results = retrieve_relevant_chunks(db, user_id=user.id, query="recursion trees", top_k=5)
        assert len(results) >= 2
        # Chunk B has higher term frequency and contains both words -> should rank top
        assert results[0].id == chunk_b.id
        assert results[1].id == chunk_a.id

    finally:
        db.close()


def test_document_retrieval_is_user_scoped():
    db = SessionLocal()
    try:
        user_a = _create_user(db)
        user_b = _create_user(db)

        # User A's document and chunk
        doc_a = Document(
            user_id=user_a.id,
            filename="user_a_secrets.txt",
            file_type="txt",
            status=DocumentStatus.READY,
        )
        db.add(doc_a)
        db.commit()
        db.refresh(doc_a)

        chunk_a = DocumentChunk(
            document_id=doc_a.id,
            chunk_index=0,
            content="Confidential project blueprints for User A proprietary system.",
        )
        db.add(chunk_a)
        db.commit()

        # User B queries with the exact keyword matching User A's chunk
        results_b = retrieve_relevant_chunks(
            db,
            user_id=user_b.id,
            query="Confidential blueprints proprietary system",
            top_k=5,
        )

        # User B MUST NOT see User A's chunk
        assert len(results_b) == 0

        # User A querying same keywords gets the chunk
        results_a = retrieve_relevant_chunks(
            db,
            user_id=user_a.id,
            query="Confidential blueprints proprietary system",
            top_k=5,
        )
        assert len(results_a) == 1
        assert results_a[0].id == chunk_a.id

    finally:
        db.close()


def test_process_document_marks_failed_status_on_bad_file(tmp_path):
    db = SessionLocal()
    try:
        user = _create_user(db)
        corrupt_file = tmp_path / "corrupt.pdf"
        corrupt_file.write_bytes(b"This is completely invalid PDF content that will fail parsing.")

        doc = Document(
            user_id=user.id,
            filename="corrupt.pdf",
            file_type="pdf",
            status=DocumentStatus.PROCESSING,
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        # Processing should catch exception and mark Document as FAILED
        process_document(db, doc, corrupt_file)

        db.refresh(doc)
        assert doc.status == DocumentStatus.FAILED

        # Existing valid fixtures transition to READY
        valid_doc = Document(
            user_id=user.id,
            filename="sample.docx",
            file_type="docx",
            status=DocumentStatus.PROCESSING,
        )
        db.add(valid_doc)
        db.commit()
        db.refresh(valid_doc)

        process_document(db, valid_doc, FIXTURES_DIR / "sample.docx")
        db.refresh(valid_doc)
        assert valid_doc.status == DocumentStatus.READY
        assert len(valid_doc.chunks) > 0

    finally:
        db.close()
