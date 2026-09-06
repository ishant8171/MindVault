# Testing and Evaluation — MindVault

This document describes the testing and evaluation strategy used for Phase 12.

## Test strategy
- Use existing unit and integration tests under `backend/tests/` to validate behavior.
- Add a small deterministic integration/evaluation test that exercises end-to-end flows without contacting external APIs (AI provider is mocked).
- Keep tests focused and avoid duplicating coverage already present in the test suite.

## Test categories
- Authentication and authorization (register, login, JWT-protected endpoints)
- Memory CRUD and privacy (create, read, update, soft-delete, ownership isolation)
- Memory extraction (AI-driven candidate extraction; mocked in tests)
- Importance/confidence handling and retrieval ranking
- Conflict detection, listing, resolution, and lifecycle transitions
- Goals and Skills CRUD and isolation
- Knowledge graph node/relationship CRUD, traversal and goal-gap analysis
- API-level behavior and error semantics (401/403/404/409/204 where appropriate)

## Controlled dataset
The integration/evaluation test uses a small synthetic dataset (no real PII) containing:
- long_term_pref: persistent preference (dark mode)
- temp_info: temporary one-time information (one-time code)
- goal_alpha: a goal entry
- skill_python: a skill entry
- project_x: project/context entry
- city_old / city_new: two memories sharing the same `slot_key` (intentional conflict)
- dessert_like and tech_pref: share the word "apple" but different slots (should not conflict)

The dataset is defined in `backend/tests/test_integration_evaluation.py`.

## Evaluation metrics (computed from the controlled dataset)
- Extraction accuracy: fraction of expected extraction candidates returned by the mocked extraction endpoint.
- Retrieval relevance: top-result correctness for a targeted query (e.g., query "dark mode" should return the long-term preference).
- Conflict detection accuracy: whether the system flags a slot-conflict when two entries share the same `slot_key` but different content.
- Conflict resolution correctness: after resolving a conflict (keep_old / keep_new / merge), the system state reflects the chosen action.
- Knowledge graph correctness: relationships created in the graph are traversable and goal gaps show missing skills.

## Measured results (automated run)

- Full backend test run (including the new integration/evaluation test): 25 passed, 0 failed.

- Evaluation metrics observed on the controlled dataset (deterministic/mocked AI):
	- Extraction accuracy: 1.0 (the mocked extraction endpoint returned the expected candidate)
	- Retrieval relevance (top-1): matched expected long-term preference for the query "dark mode"
	- Conflict detection: the attempted conflicting memory produced a 409 and returned a `conflict_id` as expected
	- Conflict resolution (keep_old): resolving the conflict returned success and preserved the original memory as expected
	- Knowledge graph relationship correctness: created relationship was traversable and the skill node was found during traversal

These measured results come from the deterministic integration test `backend/tests/test_integration_evaluation.py` which uses a mocked AI provider and a synthetic dataset.

## Limitations
- Live OpenAI API calls are not performed during automated tests. The AI provider is mocked so tests are deterministic and do not require an API key.
- These tests validate behavior within the current architecture and configuration; they do not measure real-world AI extraction accuracy with unmocked models.
- Retrieval relevance is evaluated on a small synthetic dataset; broader evaluation with realistic usage data is recommended later.

## How to run
From the repository root:

```bash
cd backend
./venv/bin/python -m pytest -q
```

The test suite will run both unit and integration checks, including the new evaluation test.
