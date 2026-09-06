# MindVault — Implementation Plan (Phase 0 Audit Output)

> **Produced**: 2026-09-06 after reading every file in the repository
> and running the live server + full test suite.
> This document must be approved before any feature code is written.

---

## 0. Audit — What Was Found vs. What Was Expected

### Live Server Verification (run in this environment, not assumed)

| Check | Result |
|---|---|
| `GET /health` | ✅ `200 {"status": "ok", "app": "MindVault", "env": "development"}` |
| `POST /auth/register` | ✅ `201` — user created |
| `POST /auth/login` | ✅ `200` — JWT returned |
| `GET /auth/me` | ✅ `200` — user profile returned with valid JWT |
| Test suite (`venv/bin/python -m pytest tests/ -q`) | ✅ **25 passed, 0 failed** in 14.98s |

### bcrypt / passlib Pin

`requirements.txt` line 7–8:
```
passlib[bcrypt]==1.7.4
bcrypt==4.0.1
```
✅ Correctly pinned. Fixes the `AttributeError: module 'bcrypt' has no attribute '__about__'`
bug that occurs with `bcrypt>=5.0.0`. **Do not touch without a documented reason.**

### Discrepancy: WORKPLAN.md vs. Reality

WORKPLAN.md describes Phase 3 (Memory CRUD) as "NOT STARTED" and Phases 4–13 as future work,
with the frontend described as an "empty placeholder." The actual repository contains far more:

| What WORKPLAN.md says | What actually exists |
|---|---|
| Memory CRUD — not started | ✅ Fully implemented: CRUD, conflict detection, slot-key scoping, lifecycle transitions, history audit trail |
| Goals — future (Phase 8) | ✅ Fully implemented: CRUD router, service, schema, tests |
| Skills — future (Phase 8) | ✅ Fully implemented: CRUD router, service, schema, tests |
| Knowledge Graph — future (Phase 9) | ✅ Fully implemented: nodes, relationships, BFS traversal, goal-skill gap query, tests |
| AI Chat — future (Phase 4) | ✅ Implemented: `/ai/chat` (memory-aware RAG prompt), `/ai/test` |
| Memory Extraction — future (Phase 5) | ✅ Implemented: `/memories/extract`, `extraction_service.py`, mocked in tests |
| Memory Retrieval — future (Phase 6) | ✅ Implemented: keyword + category + recency + importance scoring at `/memories/retrieve` |
| Tests — empty | ✅ 10 test files, 25 tests, all passing |
| Frontend — empty placeholder | ✅ React + Vite app with Login, Register, Dashboard, Chat, Goals, Skills, Memories pages, GraphView component, auth service, api service |

**WORKPLAN.md is significantly out of date.** It will be updated in Phase 10 (Documentation).

### What Genuinely Does NOT Exist

The entire "Virtual Brain" intelligence layer is missing:

- No `Evidence` model or `EvidenceService`
- No `KnowledgeConcept` model (Skill is enum-status only, cannot represent gradual confidence)
- No `LearningPreference` model or service
- No `KnowledgeStateSnapshot` model
- No `Task` model (Goal has no tasks; goals are flat)
- No `Document` or `DocumentChunk` model or `DocumentService`
- No `Subject` connective entity
- No `ContextAssemblyService` (current AI chat is a simple memory-retrieval prompt, not a knowledge-delta–aware pipeline)
- No `DashboardService` (current dashboard is a static list of goals + skills + memories)
- No Knowledge Delta computation
- No document upload/retrieval API
- No real reflection dashboard endpoint
- No tests for any of the above

---

## 1. Existing Models — Keep / Extend / Replace / Migrate

| Model / Table | Action | Reasoning |
|---|---|---|
| `User` (`users`) | **Keep as-is** | Auth is working; no schema change needed |
| `Conversation` (`conversations`) | **Keep as-is** | Raw chat log; not the same as persistent memory |
| `Message` (`messages`) | **Keep as-is** | Per-turn log; future: source for evidence extraction |
| `Memory` (`memories`) | **Keep as-is** | Slot-key conflict detection is correct and tested; this handles discrete factual/preference statements where one answer wins |
| `MemoryHistory` (`memory_history`) | **Keep as-is** | Audit trail is working and tested |
| `MemoryConflict` (`memory_conflicts`) | **Keep as-is** | Conflict detection + resolution flow is working and tested |
| `Goal` (`goals`) | **Extend** | Add relationship to `Task` (new table); no column changes to `goals` itself |
| `Skill` (`skills`) | **Keep + Migrate** | Keep table and `/skills` router intact for backward compat (existing tests depend on it); migrate existing rows into new `KnowledgeConcept` table via a script; see "Skill data migration" section below |
| `KnowledgeNode` (`knowledge_nodes`) | **Extend** | Add `CONCEPT`, `DOCUMENT`, `SUBJECT` to the `NodeType` enum; add `created_at` column via migration script |
| `KnowledgeRelationship` (`knowledge_relationships`) | **Extend** | Add `HAS_CONCEPT`, `LINKED_TO`, `COVERS`, `EVIDENCE_FOR` to `RelationshipType` enum |

---

## 2. New Tables to Add in Phase 1

| Table (Model) | Purpose |
|---|---|
| `evidence` (`Evidence`) | Append-only log of every raw signal (task completed, question asked, document read, explicit statement, correction) — the single source of truth for "what happened to this user"; all confidence updates flow through this table |
| `knowledge_concepts` (`KnowledgeConcept`) | Evidence-driven representation of what the user knows, with numeric `current_level` and `confidence` (0–1) updated by a weighted moving average each time new evidence arrives — replaces the enum-status `Skill` for knowledge-state tracking |
| `learning_preferences` (`LearningPreference`) | Inferred or stated preferences about how the user learns best (e.g. "wants_examples", "prefers_step_by_step"), updated by the same evidence-folding logic as `KnowledgeConcept` |
| `knowledge_state_snapshots` (`KnowledgeStateSnapshot`) | Point-in-time snapshot of a concept's level + confidence, written automatically every N evidence events, enabling historical progression queries (Year 1 vs. Year 5) without recomputing from raw evidence |
| `tasks` (`Task`) | Proper task entity with FK to `Goal`, status transitions (pending → in_progress → completed → cancelled), and a `completed_at` timestamp; completing a task emits one `Evidence` row (weight = 0.3) — does not assume mastery |
| `documents` (`Document`) | User-scoped uploaded file metadata (filename, mime_type, file_size, extraction status) |
| `document_chunks` (`DocumentChunk`) | Extracted, chunked text from a `Document` (500-word chunks with 50-word overlap), used for keyword-based retrieval; chunk index stored for ordering |
| `subjects` (`Subject`) | Connective entity linking Documents, KnowledgeConcepts, and Goals so the chain Document → Subject → KnowledgeConcept → Goal → Task → Evidence is real and queryable; each Subject gets a `KnowledgeNode` (type = SUBJECT) |

---

## 3. New Services to Build Across Later Phases

| Service | File | Responsibility |
|---|---|---|
| `EvidenceService` | `services/evidence_service.py` | Central entry point every other module calls to record a signal and fold it into the target subject's (concept or preference) confidence using a documented weighted moving average — **no other module may write directly to `confidence` or `current_level` fields** |
| `KnowledgeGraphService` (extend existing) | `services/knowledge_service.py` | Extend the existing service to auto-populate graph nodes/edges from real creation events (concept created, goal linked to concept, document linked to subject) and expose `compute_knowledge_delta(required_concept_ids)` which returns which concepts the user already has sufficient confidence in and which are gaps |
| `DocumentService` | `services/document_service.py` | Text extraction from uploaded files (plain text, PDF via `pypdf`, DOCX via `python-docx`), chunking, storage of chunks, and keyword-ranked retrieval across a user's chunks — gracefully marks documents `failed` if extraction libraries are unavailable |
| `ai_service.py` (already exists, extend) | `services/ai_service.py` | Already correctly isolated; extend to support being mocked cleanly via a `MOCK_AI` env flag so tests never require a real API key |
| `ContextAssemblyService` | `services/context_assembly_service.py` | Orchestrates the full Virtual Brain pipeline for a chat turn: keyword-based intent → concept identification → Knowledge Delta → pull relevant memories + document chunks + learning preferences + active goals → assemble personalized system prompt → call `ai_service` → log post-turn evidence for each concept touched |
| `DashboardService` | `services/dashboard_service.py` | Aggregates a "reflection" view (not an activity count): recent focus shift (evidence category distribution this week vs. last week), concepts with the largest recent confidence change, active learning preference signals, knowledge gaps (concepts with engagement but low confidence) |

---

## 4. Skill Data Migration — What Happens to Existing Dev Data

**Problem**: The current `Skill` model stores only `name`, `category`, and a `SkillStatus` enum
(`not_started / learning / completed`). It cannot represent gradual, evidence-driven progression.
The new `KnowledgeConcept` model needs numeric `current_level` and `confidence` fields.

**Decision: Keep both tables. Migrate, don't drop.**

Rationale:
- The `/skills` endpoint and its tests are working and must continue to pass.
- Dropping the table silently would lose any dev data without documenting it here.
- The `KnowledgeConcept` table is net-new; `skills` stays intact for backward compatibility.

**Migration steps** (implemented in `backend/scripts/migrate_v2.py`, idempotent):

1. Run `Base.metadata.create_all(bind=engine)` — creates all new tables; safe for existing ones.
2. For each row in `skills` where `migrated_from_skill_id` is not already set in `knowledge_concepts`:
   - Create a `KnowledgeConcept` row with:
     - `name` = skill.name
     - `category` = skill.category
     - `current_level` = 0.5 if `skill.status == COMPLETED`, else 0.2 if `LEARNING`, else 0.1 if `NOT_STARTED`
     - `confidence` = same mapping
     - `migrated_from_skill_id` = skill.id (FK link for traceability)
3. Print a summary: "N skills migrated to knowledge_concepts, M already existed."
4. Existing `Skill` rows are NOT modified or deleted.

**Viva note**: The team can explain that the `skills` table is preserved for backward compat and
that the `knowledge_concepts` table is the evidence-driven evolution of it, with a traceable link.

---

## 5. Execution Order (10 Phases)

Each phase must be confirmed runnable (health check + relevant tests pass) before the next begins.

| Phase | Content |
|---|---|
| **0** | ✅ Audit + this plan (current phase) |
| **1** | Data model migration — add all 8 new tables, extend KnowledgeNode/Relationship enums, run `migrate_v2.py`, confirm 25 existing tests still pass |
| **2** | `EvidenceService` + extend `KnowledgeGraphService` (`ensure_node`, `compute_knowledge_delta`) + tests |
| **3** | `DocumentService` (ingest, chunk, retrieve) + tests |
| **4** | `ContextAssemblyService` + updated `ai.py` router + tests (AI always mocked) |
| **5** | New CRUD routers: `Task` (with evidence emission on completion), `KnowledgeConcept`, `LearningPreference` |
| **6** | `DashboardService` + `GET /dashboard/` endpoint |
| **7** | `DocumentService` API layer: upload, list, query endpoints |
| **8** | Frontend updates: Dashboard reflection view, Documents page, Concepts page, Goals + Tasks, richer Chat response |
| **9** | Privacy/isolation audit pass + isolation tests for all new entities + all existing tests must still pass |
| **10** | Documentation update: WORKPLAN.md, README.md, `docs/architecture.md`, `docs/evidence_heuristic.md` |

---

## 6. What Will Be Labeled "Proposed / Future Scope"

Per project convention from WORKPLAN.md, anything not fully implemented is labeled clearly:

- **Semantic / embedding-based search** — retrieval uses keyword overlap only. Embeddings are Future Scope.
- **Automatic concept extraction from conversation messages** — the system logs evidence when the user *asks about* a concept, but does not automatically parse messages and extract knowledge from them. Labeled "Planned."
- **AI-driven intent classification** — the "parse intent" step in `ContextAssemblyService` uses keyword matching, not NLP. Documented in code comments.
- **Alembic migrations** — manual migration script only. Alembic labeled "Future Scope for production deployment."
- **Auto-generated task suggestions from goals** — not in scope; labeled "Planned."

---

## 7. Risks and Open Questions

| Item | Risk level | Question / Note |
|---|---|---|
| `openai==0.28.0` uses deprecated `ChatCompletion.create` API style | Low | The old client is pinned and working. Upgrading it would break `ai_service.py`. Not changing it during this implementation. |
| `on_event("startup")` deprecation warning in test output | Low | FastAPI recommends `lifespan` event handlers. Will fix in Phase 1 as a housekeeping item when touching `main.py`. |
| SQLite `ALTER TABLE` for new column on `knowledge_nodes` | Medium | SQLite supports `ADD COLUMN` but not all column modifiers. The `created_at` column will be added as nullable with no default so SQLite accepts it, then backfilled to `CURRENT_TIMESTAMP`. |
| `Skills` router backward compat | Medium | If the team deprecates `/skills` in the frontend in Phase 8, existing test `test_goals_skills.py` must still pass against the backend. Decision: keep `/skills` alive. |
| Document text extraction reliability | Medium | `pypdf` and `python-docx` handle most common files but will fail on scanned PDFs or password-protected files. `Document.status` = `failed` with a logged message is the graceful path — no crash, clear feedback. |
| Privacy: polymorphic `subject_id` in Evidence | High | `Evidence.subject_id` is an int that points to either `knowledge_concepts.id` or `learning_preferences.id`. SQLite has no enforced polymorphic FK. The service layer must validate ownership before accepting an evidence record. Isolation tests will cover this. |
| No Alembic — schema drift risk | Medium | If `create_all()` is called after new columns are added to existing models, SQLite silently ignores them. The migration script must run explicitly. Clearly documented in README. |

---

## 8. New Files Summary (full list for reference)

**Models (Phase 1)**
- `backend/app/models/evidence.py` [NEW]
- `backend/app/models/knowledge_concept.py` [NEW]
- `backend/app/models/learning_preference.py` [NEW]
- `backend/app/models/knowledge_state_snapshot.py` [NEW]
- `backend/app/models/task.py` [NEW]
- `backend/app/models/document.py` [NEW] — contains both `Document` and `DocumentChunk`
- `backend/app/models/subject.py` [NEW]
- `backend/app/models/__init__.py` [MODIFY] — register all new models
- `backend/app/models/knowledge.py` [MODIFY] — extend enums
- `backend/app/models/user.py` [MODIFY] — add cascade relationships for new models

**Services (Phases 2–6)**
- `backend/app/services/evidence_service.py` [NEW]
- `backend/app/services/document_service.py` [NEW]
- `backend/app/services/context_assembly_service.py` [NEW]
- `backend/app/services/dashboard_service.py` [NEW]
- `backend/app/services/knowledge_service.py` [MODIFY] — extend with `ensure_node`, `compute_knowledge_delta`
- `backend/app/services/ai_service.py` [MODIFY] — add mock support

**Schemas (Phases 2–7)**
- `backend/app/schemas/concept.py` [NEW]
- `backend/app/schemas/preference.py` [NEW]
- `backend/app/schemas/task.py` [NEW]
- `backend/app/schemas/document.py` [NEW]
- `backend/app/schemas/dashboard.py` [NEW]
- `backend/app/schemas/evidence.py` [NEW]

**Routers (Phases 5–7)**
- `backend/app/api/concepts.py` [NEW]
- `backend/app/api/preferences.py` [NEW]
- `backend/app/api/tasks.py` [NEW]
- `backend/app/api/documents.py` [NEW]
- `backend/app/api/dashboard.py` [NEW]
- `backend/app/api/ai.py` [MODIFY] — delegate to ContextAssemblyService
- `backend/app/main.py` [MODIFY] — register new routers, fix lifespan deprecation

**Migration Script (Phase 1)**
- `backend/scripts/migrate_v2.py` [NEW]

**Tests (Phases 2–9)**
- `backend/tests/test_evidence_service.py` [NEW]
- `backend/tests/test_knowledge_delta.py` [NEW]
- `backend/tests/test_document_service.py` [NEW]
- `backend/tests/test_context_assembly.py` [NEW]
- `backend/tests/test_task_evidence_emission.py` [NEW]
- `backend/tests/test_user_isolation_v2.py` [NEW] — covers all new entities

**Requirements (Phase 1)**
- `backend/requirements.txt` [MODIFY] — add `pypdf==4.3.1`, `python-docx==1.1.2`

**Frontend (Phase 8)**
- `frontend/src/pages/Documents.jsx` [NEW]
- `frontend/src/pages/Concepts.jsx` [NEW]
- `frontend/src/pages/Dashboard.jsx` [MODIFY] — replace activity list with reflection view
- `frontend/src/pages/Goals.jsx` [MODIFY] — add task sub-list per goal
- `frontend/src/pages/Chat.jsx` [MODIFY] — show richer response (gaps, concepts, chunks)
- `frontend/src/App.jsx` [MODIFY] — add routes for Documents, Concepts
- `frontend/src/services/api.js` [MODIFY] — add multipart upload helper

**Docs (Phase 10)**
- `WORKPLAN.md` [MODIFY] — update phase statuses to match reality
- `README.md` [MODIFY] — update quick start, note new dependencies
- `docs/architecture.md` [NEW]
- `docs/evidence_heuristic.md` [NEW] — honest documentation of weighted moving average
