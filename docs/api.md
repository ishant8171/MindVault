# API Overview — MindVault

This document lists primary API endpoints and their purpose. Refer to the live OpenAPI docs when the app is running at `/docs` for full schemas.

Authentication
- `POST /auth/register` — register with `email`, `username`, `password`.
- `POST /auth/login` — form-encoded `username` (email) and `password`; returns `access_token` (JWT).
- `GET /auth/me` — returns the current user (requires Authorization header).

Memories
- `POST /memories/` — create a memory; if a slot-scoped conflict exists, returns `409` with `conflict_id` and candidate details.
- `GET /memories/` — list active memories (excludes `deleted` status).
- `GET /memories/{id}` — retrieve a single memory (404 if not found or deleted).
- `PATCH /memories/{id}` — update memory fields (owner-only).
- `DELETE /memories/{id}` — soft-delete memory (owner-only, 204).
- `POST /memories/extract` — run extraction on free text (AI provider mocked in tests); returns candidates (not persisted).
- `POST /memories/retrieve` — retrieve relevant memories for a query (requires >=3 chars).
- `GET /memories/conflicts` — list pending conflicts for user.
- `POST /memories/conflicts/{id}/resolve` — resolve conflict (keep_old | keep_new | merge).

Goals & Skills
- `POST /goals/`, `GET /goals/{id}`, `PATCH /goals/{id}`, `DELETE /goals/{id}` — CRUD with ownership isolation.
- `POST /skills/`, `GET /skills/{id}`, `PATCH /skills/{id}`, `DELETE /skills/{id}` — CRUD with ownership isolation.

Knowledge Graph
- `POST /knowledge/nodes/` — create nodes (user, goal, skill, etc.) referencing domain objects.
- `POST /knowledge/relationships/` — create typed relationships (validated by allowed pairs).
- `GET /knowledge/traverse/?start={id}&depth={n}` — traverse graph.
- `GET /knowledge/goal_gaps/{goal_node_id}` — compute missing skills for a goal.

AI
- `POST /ai/test` — simple test route that calls `ai_service.generate_text` (mocked in tests).

Error semantics
- `401` — authentication required.
- `403` — forbidden (some endpoints return 404 for unauthorized access to avoid leaking existence).
- `404` — resource not found.
- `409` — conflict detected (slot-scoped memory conflict).
