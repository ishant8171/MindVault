# MindVault — Project Workplan & Architecture Evolution

**Project Name**: MindVault (BCA Minor Project II)  
**Status**: All 13 Original Phases Completed & Verified + Extended Virtual Brain Architecture Implemented  
**Test Suite**: **65 passed, 0 failed** in `backend/tests/`  
**Frontend**: React 18 + Vite SPA built and verified (`npm run build` succeeds)  
**Security Audit**: Passed with 100% tenant isolation verified ([SECURITY_AUDIT.md](SECURITY_AUDIT.md))

---

## 1. What MindVault Is

MindVault is an AI-powered persistent memory and personal knowledge management system designed as a BCA Minor Project. 

**Core Academic Concept**: The external LLM provides natural language generation only. The custom backend provides cognitive persistence, structured knowledge tracking, evidence-driven confidence progression, conflict resolution, document grounding, and strict user privacy. It is deliberately engineered **not** to be a simple pass-through chatbot wrapper.

---

## 2. Locked-in Architectural Principles (Honest BCA Scope)

- **Backend**: Python 3.12+, FastAPI, SQLAlchemy ORM, Pydantic v2.
- **Database**: SQLite for local development; switchable to PostgreSQL via `DATABASE_URL` (no code changes needed).
- **Frontend**: React 18 + Vite single-page application (`frontend/`).
- **AI Provider**: Strictly isolated behind `backend/app/services/ai_service.py`. Raises `AIProviderNotConfiguredError` if `OPENAI_API_KEY` is not provided; fully mockable for deterministic CI test runs.
- **Authentication**: Stateless HMAC-SHA256 JWT tokens with `Depends(get_current_user)`.
- **Pinned Dependencies**: `passlib[bcrypt]==1.7.4`, `bcrypt==4.0.1`, `pypdf==4.3.1`, `python-docx==1.1.2` (avoids known bcrypt 5.x runtime breakage).
- **No Vector DBs / No Microservices / No Fake AI**: Honest, auditable algorithms: term-frequency keyword ranking for documents and weighted moving averages for knowledge progression.

---

## 3. Status of the 13 Original Phases

All 13 original phases from the initial project inception are fully implemented and verified:

| # | Original Phase Name | Real Current Status | Implementation Details |
|---|---|---|---|
| **1** | **Project architecture & database design** | **DONE** | FastAPI backend initialized, SQLAlchemy ORM configured, engine/session management established. Scaled from the original 10 tables to 16 relational tables. |
| **2** | **Backend setup and authentication** | **DONE** | Registration, login, and `/auth/me` endpoints functional. Pinned bcrypt 4.0.1 to avoid passlib breakage. Password hashing and JWT generation tested. |
| **3** | **Memory CRUD and database** | **DONE** | Complete CRUD in `app/services/memory_service.py` and `app/api/memories.py`. Slot-key scoping, category classification, importance scoring, and soft-delete lifecycle implemented. |
| **4** | **AI API integration** | **DONE** | `app/services/ai_service.py` provides isolated `generate_response()`. Raises typed `AIProviderNotConfiguredError` if unconfigured; mocked in all tests. |
| **5** | **Memory extraction & importance scoring** | **DONE** | Rule-based and pattern extraction in `app/services/extraction_service.py`. Heuristic importance scoring based on recency, category, and explicit user weights. |
| **6** | **Memory retrieval** | **DONE** | Multi-factor keyword + recency + importance ranking implemented in `app/services/retrieval_service.py` and `/memories/retrieve`. |
| **7** | **Conflict detection & memory lifecycle** | **DONE** | Slot-scoped conflict detection (`slot_key`). Conflicts create `MemoryConflict` records; users resolve via `/memories/conflicts/{id}/resolve` with full `MemoryHistory` audit trail. |
| **8** | **Goals and skills** | **DONE** | Goals CRUD with target dates and priorities (`app/api/goals.py`). Extended with actionable `Task` models whose completion emits empirical evidence. Legacy `Skill` models preserved for backward compatibility. |
| **9** | **Knowledge graph** | **DONE** | Relational graph storage in `knowledge_nodes` and `knowledge_relationships`. Supports BFS traversal, gap discovery, and entity linking across concepts, documents, and subjects. |
| **10**| **Frontend dashboard and chat** | **DONE** | React + Vite UI in `frontend/src/`. Features self-reflection dashboard, interactive chat with assistant, goal/task milestone completion with evidence feedback toast, and document vault uploads. |
| **11**| **Privacy controls** | **DONE** | Privacy levels (`public`, `internal`, `confidential`) on memories, soft-deletion semantics, and strict user-scoped query isolation. |
| **12**| **Testing and evaluation** | **DONE** | Comprehensive automated test suite comprising 65 pytest tests across 17 test files. Zero test failures. |
| **13**| **Final polish and documentation** | **DONE** | Detailed documentation: [README.md](README.md), [ARCHITECTURE.md](ARCHITECTURE.md), [docs/evidence_heuristic.md](docs/evidence_heuristic.md), [SECURITY_AUDIT.md](SECURITY_AUDIT.md), and [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md). |

---

## 4. Extension Beyond the Original Plan: The "Virtual Brain" Architecture

Following the Phase 0 audit, the system extended significantly beyond a basic CRUD memory system into a cohesive **Virtual Brain** cognitive architecture, as planned in [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md).

The original 13-phase plan treated memories and skills as static enum records. The extended architecture introduced dynamic, evidence-driven cognitive state:

1. **Evidence-Driven Progression (`Evidence`, `KnowledgeConcept`, `LearningPreference`)**:
   - Instead of static skill enums (e.g. "beginner", "expert"), user knowledge is modeled numerically: `current_level` (0.0 to 5.0) and `confidence` (0.0 to 1.0).
   - Every observable interaction (completing a task, asking a question, reading a document, explicit statements, or corrections) emits an append-only `Evidence` record.
   - A deterministic Bayesian-inspired weighted moving average updates concept levels and confidence.

2. **Knowledge State Snapshots (`KnowledgeStateSnapshot`)**:
   - Every 5 evidence events, a point-in-time snapshot is recorded.
   - Enables historical velocity tracking ("How has confidence grown over the last 14 days?") without replaying raw logs.

3. **Document Vault Ingestion & Grounding (`Document`, `DocumentChunk`, `DocumentService`)**:
   - Ingests PDF, DOCX, and TXT files.
   - Chunks text into 500-word sliding windows with 50-word overlaps.
   - Ranks chunks using a term-frequency keyword algorithm scoped to the authenticated user.

4. **Knowledge Delta Prompt Framing (`ContextAssemblyService`)**:
   - Extracts required technical concepts from user inquiries.
   - Computes the **Knowledge Delta**: concepts with high confidence are marked as **Established Knowledge**, while missing or low-confidence concepts are marked as **Knowledge Gaps**.
   - Frames the LLM prompt: *"DO NOT explain established concepts from scratch; FOCUS explanations on knowledge gaps."* This eliminates repetitive boilerplate answers.

5. **Self-Reflective Dashboard (`DashboardService`)**:
   - Replaces static activity grids with cognitive reflection: computes 14-day focus shift (concepts with growing activity share), rising concepts, stagnant topics (repeated evidence with low confidence), and active learning styles.

6. **Dedicated Security & Tenant Isolation Audit (`SECURITY_AUDIT.md`)**:
   - A dedicated audit across all database queries and services verified 100% multi-tenant isolation.
   - Multi-user isolation test suite ([`test_user_isolation.py`](backend/tests/test_user_isolation.py)) guarantees that User A's data never leaks into User B's queries, documents, prompts, or dashboard.

For technical specifications of this extended architecture, consult [ARCHITECTURE.md](ARCHITECTURE.md) and [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md).
