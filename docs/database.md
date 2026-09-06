# Database / Schema Overview — MindVault

Primary models (high-level):

- `User` — standard user record (email, username, password hash) used for ownership and authentication.
- `Memory` — stores user memories with fields:
  - `id`, `user_id`, `content`, `category`, `importance_score`, `confidence_score`, `source`, `status`, `slot_key`, timestamps
  - `status` supports soft-delete and lifecycle states (`new`, `active`, `archived`, `deleted`, ...)
- `MemoryHistory` — audit trail for changes, conflict resolutions, and lifecycle transitions.
- `MemoryConflict` — records pending conflicts with `old_memory_id` and `new_memory_id`, `status` and `resolution`.
- `Goal`, `Skill` — simple domain objects linked to users; used by UI and knowledge graph.
- `KnowledgeNode`, `KnowledgeRelationship` — represent graph nodes and directed relationships between nodes; relationships are validated by allowed node type pairs.

Notes
- The schema is intentionally simple to stay relational and inspectable. If large-scale vector search is required later, a separate embedding/indexing component should be introduced (out of scope for this repo).
