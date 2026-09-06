# Database / Schema Overview — MindVault

MindVault uses a relational schema designed with SQLAlchemy ORM, backed by SQLite in development and compatible with PostgreSQL for production via the `DATABASE_URL` environment variable.

The schema comprises **16 relational tables**, categorized into 4 domain subsystems:

---

## 1. Identity & Memory Subsystem

1. **`users`**:
   - `id`, `email`, `username`, `password_hash`, `created_at`, `updated_at`.
   - Core tenant anchor; all user-scoped records enforce foreign key cascade on `user_id`.
2. **`memories`**:
   - `id`, `user_id`, `content`, `category`, `slot_key`, `importance_score`, `confidence_score`, `source`, `status`, `privacy_level`, `created_at`, `updated_at`.
   - Stores slot-scoped facts and preferences. Contradictions within the same `slot_key` trigger conflict detection.
3. **`memory_history`**:
   - `id`, `memory_id`, `action`, `previous_content`, `new_content`, `reason`, `created_at`.
   - Append-only audit trail capturing memory updates and conflict resolutions.
4. **`memory_conflicts`**:
   - `id`, `user_id`, `slot_key`, `existing_memory_id`, `candidate_content`, `status`, `resolution`, `created_at`, `resolved_at`.
   - Tracks detected contradictions pending user resolution.

---

## 2. Evidence-Driven Cognitive Subsystem (Virtual Brain)

5. **`evidence`**:
   - `id`, `user_id`, `evidence_type`, `subject_type`, `subject_id`, `weight`, `summary`, `created_at`.
   - Append-only empirical event log (e.g. task completed, question asked, document uploaded, correction noted). Single source of truth for confidence changes.
6. **`knowledge_concepts`**:
   - `id`, `user_id`, `name`, `current_level` (0.0 to 5.0), `confidence` (0.0 to 1.0), `evidence_count`, `last_evidence_at`, `created_at`, `updated_at`.
   - Evidence-driven representation of conceptual mastery, updated via weighted moving average.
7. **`learning_preferences`**:
   - `id`, `user_id`, `preference_type`, `confidence` (0.0 to 1.0), `evidence_count`, `created_at`, `updated_at`.
   - Inferred or declared learning style habits (e.g. `prefers_concrete_examples`).
8. **`knowledge_state_snapshots`**:
   - `id`, `concept_id`, `level`, `confidence`, `snapshot_at`.
   - Historical progression snapshots created every 5 evidence events to calculate growth velocity.
9. **`subjects`**:
   - `id`, `user_id`, `name`, `description`, `created_at`.
   - Connective domain entity linking documents, concepts, and goals.

---

## 3. Goals & Milestone Tasks Subsystem

10. **`goals`**:
    - `id`, `user_id`, `subject_id`, `title`, `description`, `status`, `priority`, `target_date`, `created_at`, `updated_at`.
    - User objectives and educational milestones.
11. **`tasks`**:
    - `id`, `goal_id`, `user_id`, `title`, `description`, `status`, `completed_at`, `created_at`, `updated_at`.
    - Actionable steps belonging to a goal. Marking a task completed automatically emits an empirical `Evidence` signal (weight 0.3).
12. **`skills`**:
    - `id`, `user_id`, `name`, `level`, `category`, `created_at`, `updated_at`.
    - Legacy skill records preserved for backward compatibility.

---

## 4. Document Vault & Relational Knowledge Graph

13. **`documents`**:
    - `id`, `user_id`, `filename`, `file_type`, `file_size`, `chunk_count`, `created_at`.
    - Uploaded reference documents (PDF, DOCX, TXT).
14. **`document_chunks`**:
    - `id`, `document_id`, `user_id`, `chunk_index`, `content`, `created_at`.
    - 500-word sliding window text segments (with 50-word overlap) queried via term-frequency keyword ranking.
15. **`knowledge_nodes`**:
    - `id`, `user_id`, `label`, `node_type`, `ref_id`, `created_at`.
    - Graph vertices (`CONCEPT`, `DOCUMENT`, `SUBJECT`, `GOAL`, `SKILL`).
16. **`knowledge_relationships`**:
    - `id`, `user_id`, `source_node_id`, `target_node_id`, `relationship_type`, `created_at`.
    - Directed edges linking graph nodes (`PREREQUISITE_FOR`, `COVERS`, `PART_OF`, `RELATED_TO`, `HAS_CONCEPT`, etc.).

---

## Notes on Architecture Design

- **Inspectability**: All models are relational and inspectable using standard SQL tools (`sqlite3`).
- **Data Integrity**: Foreign key constraints and cascade deletions ensure clean cleanup of dependent child entities.
- **Tenant Isolation**: Every user-owned table includes a foreign key constraint to `users.id` and queries strictly enforce this filter.
