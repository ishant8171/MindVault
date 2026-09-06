# MindVault — Cognitive Memory & Personal Knowledge System

MindVault is an AI-powered persistent memory and personalized knowledge management system developed as a BCA Minor Project. Unlike standard chatbot wrappers that simply pass chat transcripts back to an LLM, MindVault maintains an evolving cognitive model of the user:

- **Evidence-Driven Progression**: Updates concept mastery and learning preferences via deterministic weighted moving averages over user interactions (task completion, conceptual questions, corrections, documents).
- **Knowledge Delta Framing**: Computes known concepts vs. knowledge gaps to instruct the LLM what *not* to explain and what to focus on.
- **Document Vault**: Extracts and chunks user notes (PDF, DOCX, TXT) into 500-word sliding windows, retrieving relevant excerpts via keyword/term-frequency scoring.
- **Reflective Dashboard**: Analyzes behavioral patterns (14-day focus shifts, rising concepts, stagnant topics, active learning styles).
- **Strict Multi-Tenant Isolation**: Enforces tenant scoping across all database queries and user-scoped filesystem storage (`uploads/{user_id}/`).

---

## 1. Quick Start & Setup Instructions

### Prerequisites
- Python 3.12+ (tested on Python 3.12 & 3.13)
- Node.js 18+ & npm
- Git

---

### Step 1: Backend Setup (FastAPI + SQLite)

1. Open a terminal and navigate to the `backend/` directory:
   ```bash
   cd backend
   ```

2. Create and activate a Python virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate    # On Windows: venv\Scripts\activate
   ```

3. Install pinned dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   > **Note on pinned dependencies**: `passlib[bcrypt]==1.7.4` and `bcrypt==4.0.1` are pinned explicitly to prevent runtime incompatibility errors.

4. Initialize the environment configuration:
   ```bash
   cp .env.example .env
   ```
   *(Optional: set `OPENAI_API_KEY` in `backend/.env` if you wish to run live OpenAI calls; otherwise, the system will raise an explicit `AIProviderNotConfiguredError` rather than fabricating responses).*

5. Start the FastAPI development server:
   ```bash
   uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
   ```

- **Interactive API Documentation (Swagger UI)**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Health Check**: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

---

### Step 2: Frontend Setup (React + Vite)

1. In a new terminal window, navigate to the `frontend/` directory:
   ```bash
   cd frontend
   ```

2. Install npm dependencies:
   ```bash
   npm install
   ```

3. Start the Vite development server:
   ```bash
   npm run dev
   ```

- **Web Application UI**: [http://127.0.0.1:5173](http://127.0.0.1:5173)

To test the production build:
```bash
npm run build
```

---

### Step 3: Running via Docker Compose (Alternative)

To launch the full backend and persistence layer in a container:
```bash
cp backend/.env.example backend/.env
docker compose up --build
```

---

## 2. Running Automated Tests

All AI provider calls are mockable and isolated behind `ai_service.py`, allowing the entire test suite to execute deterministically without external API dependencies or incurring API costs.

From the `backend/` directory with the virtual environment activated:

```bash
cd backend
./venv/bin/python -m pytest -q
```

**Expected Output**:
```text
65 passed, 203 warnings in 30.56s
```

To run the dedicated cross-cutting multi-tenant isolation suite:
```bash
./venv/bin/python -m pytest tests/test_user_isolation.py -v
```

---

## 3. Documentation & Technical Specifications

- [ARCHITECTURE.md](ARCHITECTURE.md): Comprehensive system architecture, the 16 database models, context assembly pipeline, and honest heuristic disclosure for viva Q&A.
- [docs/evidence_heuristic.md](docs/evidence_heuristic.md): Detailed explanation and mathematical formulas for Bayesian-inspired evidence folding and Knowledge Delta computation.
- [SECURITY_AUDIT.md](SECURITY_AUDIT.md): Complete Phase 8 security and multi-tenant isolation audit report.
- [WORKPLAN.md](WORKPLAN.md): Progression from the original 13-phase plan to the extended Virtual Brain architecture.
- [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md): Detailed Phase 0 audit findings and architectural roadmap.
- [docs/api.md](docs/api.md): REST API endpoints and request/response specifications.
- [docs/database.md](docs/database.md): Relational database schema reference.

---

## 4. Academic Project Boundaries (Honest BCA Scope)

- **Document Retrieval**: MindVault uses deterministic term-frequency (TF) keyword search over 500-word sliding window chunks, not opaque external vector databases.
- **Concept Matching**: Knowledge Delta concepts are identified via keyword/alias matching and explicit entity extraction.
- **AI Provider**: Fully decoupled. If `OPENAI_API_KEY` is not provided, the API returns a structured error rather than simulating fake knowledge.
- **Single-Host Architecture**: SQLite (switchable to Postgres via `DATABASE_URL`) without microservices or message queues.
