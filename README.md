# MindVault — Cognitive Memory & Knowledge Assistant

MindVault is an AI-powered persistent memory and personalized knowledge management system built as a BCA Minor Project. Unlike standard chatbot wrappers that simply pass chat transcripts back to an LLM, MindVault maintains an evolving cognitive model of the user:
- **Evidence-Driven Progression**: Tracks concept mastery and learning preferences via weighted moving averages over user interactions (task completion, questions, corrections, documents).
- **Knowledge Delta Framing**: Dynamically computes known concepts vs. knowledge gaps to instruct the LLM what *not* to explain and what to focus on.
- **Document Vault**: Extracts and chunks user notes (PDF, DOCX, TXT) with sliding-window word chunks and term-frequency keyword ranking.
- **Reflective Dashboard**: Analyzes behavioral patterns (14-day focus shift, rising concepts, stagnant topics, active preferences).
- **Strict Multi-Tenant Isolation**: Enforces tenant scoping across all database queries and user-scoped filesystem storage (`uploads/{user_id}/`).

---

## 1. Quick Start

### Option A: Local Development (Recommended for fast local testing)

#### 1. Backend Setup
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Optional: add your OPENAI_API_KEY in backend/.env for live AI responses
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
- Interactive API Docs (Swagger): [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- Health Check: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

#### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
- Frontend UI: [http://127.0.0.1:5173](http://127.0.0.1:5173)

### Option B: Docker Compose
```bash
cp backend/.env.example backend/.env
docker compose up --build
```

---

## 2. Running Automated Tests

MindVault includes a comprehensive test suite (unit tests, integration tests, and multi-tenant security isolation tests). All AI provider calls are mockable and isolated, allowing deterministic testing without external API dependencies.

```bash
cd backend
./venv/bin/python -m pytest -q
```
**Test Status**: **65 passed, 0 failed** in `backend/tests/`.

To run the dedicated cross-cutting user isolation test suite:
```bash
cd backend
./venv/bin/python -m pytest tests/test_user_isolation.py -v
```

---

## 3. Architecture & Documentation

- [docs/architecture.md](docs/architecture.md): Full system architecture, database models, and context assembly pipeline.
- [docs/evidence_heuristic.md](docs/evidence_heuristic.md): Detailed explanation and mathematical formula for evidence folding and Knowledge Delta computation.
- [docs/api.md](docs/api.md): REST API endpoints and request/response specifications.
- [docs/database.md](docs/database.md): Relational database schema reference (16 tables).
- [SECURITY_AUDIT.md](SECURITY_AUDIT.md): Comprehensive Phase 8 security and multi-tenant isolation audit report.
- [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md): Initial audit and implementation roadmap.
- [WORKPLAN.md](WORKPLAN.md): Development progress tracking and milestone execution.

---

## 4. Key Design Decisions

1. **Pinned Security Dependencies**:
   `passlib[bcrypt]==1.7.4` and `bcrypt==4.0.1` are strictly pinned to prevent `bcrypt>=5.0.0` incompatibility.
2. **Realistic Academic Scope**:
   No heavy external vector databases or microservices. Document retrieval uses clean term-frequency scoring; knowledge progression uses explainable Bayesian-inspired weighted moving averages.
3. **Graceful Degradation**:
   When `OPENAI_API_KEY` is not configured, the system raises an explicit, typed `AIProviderNotConfiguredError` rather than silently fabricating responses.
4. **Physical Vault Partitioning**:
   Uploaded files are physically isolated in `backend/uploads/{user_id}/` to protect data at rest.
