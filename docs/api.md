# API Overview — MindVault REST API

This document provides an overview of all primary API endpoints in the MindVault system. Full interactive OpenAPI schemas and request/response specifications are available when the backend server is running at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

All endpoints except `/auth/register`, `/auth/login`, and `/health` require an `Authorization: Bearer <jwt_token>` header.

---

## 1. Health & Authentication (`/auth`)

- `GET /health`: System health check (returns status, app name, and environment).
- `POST /auth/register`: Create a new user account (`email`, `username`, `password`). Returns `201 Created`.
- `POST /auth/login`: Form-encoded login (`username` [email] and `password`). Returns JWT access token.
- `GET /auth/me`: Returns the authenticated user's profile.

---

## 2. Memories (`/memories`)

- `POST /memories/`: Create a new memory. Checks for slot-scoped conflicts. If a contradiction within the same `slot_key` is detected, returns `409 Conflict` with candidate conflict details.
- `GET /memories/`: List user's active memories (excludes `deleted` status).
- `GET /memories/{id}`: Retrieve a specific memory (scoped to current user).
- `PUT /memories/{id}`: Update memory content, importance, or privacy level.
- `DELETE /memories/{id}`: Soft-delete memory (`status = "deleted"`).
- `POST /memories/extract`: Heuristic extraction of facts and preferences from freeform text.
- `POST /memories/retrieve`: Keyword + recency + importance ranked memory retrieval.
- `GET /memories/conflicts/unresolved`: List pending memory conflicts for the user.
- `POST /memories/conflicts/{id}/resolve`: Resolve a conflict (`KEEP_EXISTING`, `OVERWRITE_WITH_NEW`, or `MERGE`).

---

## 3. Knowledge Concepts (`/concepts`)

- `GET /concepts/`: List all knowledge concepts for the authenticated user (with level, confidence, evidence count).
- `POST /concepts/`: Manually create a knowledge concept (e.g. initial baseline before evidence folding).
- `GET /concepts/{id}`: Retrieve concept details.
- `GET /concepts/{id}/history`: Retrieve point-in-time progression snapshots (`KnowledgeStateSnapshot`).

---

## 4. Learning Preferences (`/preferences`)

- `GET /preferences/`: List all inferred or stated learning preferences for the user.
- `POST /preferences/`: Create or update a learning preference (e.g. `prefers_concrete_examples`).
- `DELETE /preferences/{id}`: Remove a learning preference.

---

## 5. Goals & Tasks (`/goals`)

- `GET /goals/`: List all user goals with status, priority, and target dates.
- `POST /goals/`: Create a new goal.
- `GET /goals/{id}`: Get goal details including attached tasks.
- `PATCH /goals/{id}`: Update goal fields or status.
- `DELETE /goals/{id}`: Delete goal and cascade delete associated tasks.
- `POST /goals/{id}/tasks`: Add an actionable milestone task to a goal.
- `PATCH /goals/tasks/{task_id}`: Update task status (`pending`, `in_progress`, `completed`). Completing a task automatically emits an empirical `Evidence` signal (weight 0.3).

---

## 6. Document Vault (`/documents`)

- `POST /documents/upload`: Multipart file upload (PDF, DOCX, TXT). Automatically extracts text and creates 500-word sliding window chunks.
- `GET /documents/`: List uploaded documents with metadata (chunk count, size, type).
- `GET /documents/{id}`: View document details.
- `DELETE /documents/{id}`: Delete document, database chunks, and remove physical file from user upload directory.

---

## 7. Knowledge Graph (`/knowledge-graph`)

- `GET /knowledge-graph/`: Fetch user's graph (nodes and relationships) for visualization.
- `POST /knowledge-graph/nodes`: Create a graph node (validates ownership of underlying `ref_id`).
- `POST /knowledge-graph/links`: Link two user-owned nodes with a directed relationship.
- `POST /knowledge-graph/delta`: Compute Knowledge Delta (known concepts vs. knowledge gaps) for a list of concept names.

---

## 8. Cognitive Reflection Dashboard (`/dashboard`)

- `GET /dashboard/`: Computes and returns the user's reflection state:
  - `current_focus`: 14-day activity share shift for concepts and goals.
  - `rising_concepts`: Concepts showing marked confidence/level velocity over snapshots.
  - `stagnant_or_struggling_concepts`: High-frequency evidence with persistent low confidence.
  - `active_preferences`: High-confidence learning styles.
  - `goals_needing_attention`: Goals with zero recent activity or overdue deadlines.

---

## 9. Cognitive Assistant (`/assistant`)

- `POST /assistant/ask`: Executes the full 5-layer Virtual Brain context assembly pipeline:
  1. Identifies required concepts and computes Knowledge Delta.
  2. Injects high-confidence learning styles.
  3. Grounding via top keyword-matched document vault chunks.
  4. Memory fact retrieval.
  5. Recent chat turn context.
  - Instructs the LLM not to explain known concepts from scratch, focusing on knowledge gaps.
  - Returns answer or raises `503` if `OPENAI_API_KEY` is not configured.
