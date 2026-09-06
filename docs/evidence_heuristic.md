# Evidence Folding & Knowledge Delta Heuristics

## 1. Overview & Motivation

MindVault is built on the premise that an AI cognitive assistant should not treat the user as a static prompt recipient, nor should it rely on opaque vector similarity where confidence cannot be audited. 

Instead, MindVault adopts an **evidence-driven Bayesian-inspired heuristic**:
- Every interaction with the user (completing a task, asking a question, reading a document, explicit statement, or correction) is recorded as an immutable `Evidence` event.
- User knowledge concepts (`KnowledgeConcept`) and learning styles (`LearningPreference`) evolve dynamically via a **weighted moving average** over incoming evidence signals.
- Periodic point-in-time snapshots (`KnowledgeStateSnapshot`) capture progression trajectories over time.

---

## 2. Evidence Types and Weights

Each `Evidence` signal has an explicit type and a calibrated weight in the range `[0.0, 1.0]`:

| Evidence Type | Default Weight | Description |
| :--- | :--- | :--- |
| `CORRECTION` | 0.8 | Direct user correction indicating prior gap or misconception. |
| `EXPLICIT_STATEMENT` | 0.7 | User explicitly stating familiarity, preference, or lack thereof. |
| `TASK_COMPLETION` | 0.3 | Completing a task demonstrates applied effort, but does not imply complete mastery. |
| `QUESTION_ASKED` | 0.2 | Asking a conceptual question implies an active interest or knowledge gap. |
| `DOCUMENT_READ` | 0.1 | Uploading or referencing a document indicates passive exposure. |

---

## 3. Mathematical Update Formula

When an `Evidence` row is recorded for a `KnowledgeConcept`, its `current_level` and `confidence` are updated deterministically:

```python
# Delta direction depends on whether evidence indicates mastery or a gap
delta = 1.0 if is_positive else -0.5

# Weighted Moving Average for Skill/Concept Level (clamped to [0.0, 5.0]):
new_level = (current_level * evidence_count + (delta * weight)) / (evidence_count + 1)
new_level = max(0.0, min(5.0, new_level))

# Incremental Confidence Growth (clamped to [0.0, 1.0]):
confidence_boost = weight * 0.1
new_confidence = min(1.0, current_confidence + confidence_boost)

evidence_count += 1
```

### Automatic Snapshotting
Every `SNAPSHOT_INTERVAL` (default: 5) evidence updates on a concept, a `KnowledgeStateSnapshot` row is created automatically:
- Captures `level`, `confidence`, and `timestamp`.
- Enables historical velocity tracking ("How much has user confidence grown between Week 1 and Week 4?") without replaying raw evidence logs.

---

## 4. Knowledge Delta Computation

Before querying the LLM, MindVault extracts key technical concepts from the user's inquiry and computes the **Knowledge Delta**:

For each required concept:
- If `concept` does not exist for the user OR `confidence < 0.4` OR `current_level < 1.5`:
  - Flagged as `gap = True` (Knowledge Gap).
- If `concept` exists with `confidence >= 0.4` and `current_level >= 1.5`:
  - Flagged as `gap = False` (Established Knowledge).

### Prompt Framing Principle
The prompt generator explicitly frames the instruction:
- **Established Concepts**: *"DO NOT explain from scratch; the user ALREADY KNOWS these: [concepts]"*
- **Knowledge Gaps**: *"FOCUS your explanation and depth here; explain these clearly: [concepts]"*

This completely eliminates repetitive explanations of topics the user already understands, solving one of the most frustrating aspects of standard LLM interactions.

---

## 5. Rationale & Limitations

### Why Not Vector Embeddings / Complex Decay?
1. **Explainability**: Every change in user level or confidence maps directly to an observable row in `evidence`.
2. **Realistic Academic Scope**: Avoids fragile external vector database dependencies or non-deterministic GPU embeddings in a standard BCA project.
3. **Auditability**: Teachers, evaluators, and users can inspect the raw evidence table and immediately understand *why* the assistant framed an answer a certain way.

### Known Limitations
- The moving average weights recent evidence equally to earlier evidence per unit weight unless historical snapshots are queried.
- Concepts must be identified via keyword/alias matching or explicit metadata extraction rather than dense semantic embeddings.
