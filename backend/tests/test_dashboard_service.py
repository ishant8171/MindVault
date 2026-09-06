"""
Phase 6 tests:
Verifies DashboardService and GET /dashboard/ endpoint:
- Focus shift detection between windowed evidence activity
- Proper categorization of rising vs. stagnant/struggling concepts
- High-confidence learning preferences surfaced
- Strict user-scoping: User A activity never leaks into User B dashboard
- Graceful handling of fresh/empty accounts without errors
"""

import uuid
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from app.main import app
from app.database.session import SessionLocal
from app.models.user import User
from app.models.knowledge_concept import KnowledgeConcept
from app.models.knowledge_state_snapshot import KnowledgeStateSnapshot
from app.models.learning_preference import LearningPreference
from app.models.evidence import Evidence, EvidenceType, SubjectType
from app.models.goal import Goal, GoalStatus
from app.services.dashboard_service import get_dashboard


def _register_and_auth(client, tag=None):
    unique = uuid.uuid4().hex[:8]
    prefix = tag or "dash_u"
    email = f"{prefix}_{unique}@example.com"
    username = f"{prefix}_{unique}"
    password = "StrongPassword123!"
    r = client.post("/auth/register", json={"email": email, "username": username, "password": password})
    assert r.status_code == 201
    login = client.post("/auth/login", data={"username": email, "password": password})
    assert login.status_code == 200
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _create_user(db):
    uid = uuid.uuid4().hex[:8]
    user = User(
        username=f"dash_db_{uid}",
        email=f"dash_db_{uid}@test.com",
        password_hash="fakehash",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_dashboard_detects_focus_shift_between_windows():
    db = SessionLocal()
    try:
        user = _create_user(db)
        now = datetime.now(timezone.utc)

        # Two concepts: "Web Development" (earlier focus) and "Machine Learning" (recent focus)
        c_web = KnowledgeConcept(user_id=user.id, name="Web Development", current_level=0.5, confidence=0.5)
        c_ml = KnowledgeConcept(user_id=user.id, name="Machine Learning", current_level=0.4, confidence=0.4)
        db.add_all([c_web, c_ml])
        db.commit()

        # Earlier window: 20 days ago (within [now - 28d, now - 14d]) -> 4 events on Web Dev
        for _ in range(4):
            ev = Evidence(
                user_id=user.id,
                evidence_type=EvidenceType.TASK_COMPLETED,
                subject_type=SubjectType.KNOWLEDGE_CONCEPT,
                subject_id=c_web.id,
                weight=0.5,
                summary="Web coursework",
                created_at=now - timedelta(days=20),
            )
            db.add(ev)

        # Recent window: 4 days ago (within [now - 14d, now]) -> 5 events on ML
        for _ in range(5):
            ev = Evidence(
                user_id=user.id,
                evidence_type=EvidenceType.TASK_COMPLETED,
                subject_type=SubjectType.KNOWLEDGE_CONCEPT,
                subject_id=c_ml.id,
                weight=0.6,
                summary="ML model training",
                created_at=now - timedelta(days=4),
            )
            db.add(ev)

        db.commit()

        dashboard = get_dashboard(db, user.id)

        # Machine Learning had 0% earlier share and 100% recent share
        shifts = dashboard["current_focus"]["shifts"]
        assert len(shifts) >= 1
        top_shift = shifts[0]
        assert top_shift["concept_name"] == "Machine Learning"
        assert top_shift["share_change"] > 0

        # Reflection statement should capture the shift toward Machine Learning
        reflections = " ".join(dashboard["reflections"])
        assert "Machine Learning" in reflections

    finally:
        db.close()


def test_dashboard_flags_rising_and_stagnant_concepts_correctly():
    db = SessionLocal()
    try:
        user = _create_user(db)

        # 1. Rising concept: snapshot was 0.3, current confidence is 0.7
        c_rising = KnowledgeConcept(user_id=user.id, name="Recursion", current_level=0.7, confidence=0.7, evidence_count=5)
        db.add(c_rising)
        db.commit()
        db.refresh(c_rising)

        snap = KnowledgeStateSnapshot(
            user_id=user.id,
            concept_id=c_rising.id,
            level=0.3,
            confidence=0.3,
            created_at=datetime.now(timezone.utc) - timedelta(days=10),
        )
        db.add(snap)

        # 2. Stagnant / struggling concept: high evidence count (4) but confidence low (0.2)
        c_struggle = KnowledgeConcept(user_id=user.id, name="Memory Allocation", current_level=0.2, confidence=0.2, evidence_count=4)

        # 3. Not-yet-started concept: evidence_count = 0, confidence = 0.1
        c_new = KnowledgeConcept(user_id=user.id, name="Compilers", current_level=0.0, confidence=0.1, evidence_count=0)

        db.add_all([c_struggle, c_new])
        db.commit()

        dashboard = get_dashboard(db, user.id)

        # Rising concept check
        rising_names = [r["name"] for r in dashboard["rising_concepts"]]
        assert "Recursion" in rising_names

        # Stagnant concept check
        stagnant_names = [s["name"] for s in dashboard["stagnant_or_struggling_concepts"]]
        assert "Memory Allocation" in stagnant_names
        # Not-yet-started must NOT be flagged as struggling
        assert "Compilers" not in stagnant_names

    finally:
        db.close()


def test_dashboard_surfaces_high_confidence_preferences():
    db = SessionLocal()
    try:
        user = _create_user(db)

        # High confidence preference
        p_high = LearningPreference(user_id=user.id, preference_type="worked_code_examples", confidence=0.85, evidence_count=6)
        # Low confidence preference
        p_low = LearningPreference(user_id=user.id, preference_type="abstract_proofs", confidence=0.15, evidence_count=1)

        db.add_all([p_high, p_low])
        db.commit()

        dashboard = get_dashboard(db, user.id)
        active_prefs = [p["preference_type"] for p in dashboard["active_preferences"]]

        assert "worked_code_examples" in active_prefs
        assert "abstract_proofs" not in active_prefs

        reflections = " ".join(dashboard["reflections"])
        assert "worked code examples" in reflections

    finally:
        db.close()


def test_dashboard_is_user_scoped():
    with TestClient(app) as client:
        headers_a = _register_and_auth(client, "dash_a")
        headers_b = _register_and_auth(client, "dash_b")

        # User A creates a concept and preference
        client.post("/concepts/", json={"name": "Proprietary Algorithm A", "initial_level": 0.9, "initial_confidence": 0.9}, headers=headers_a)
        client.post("/preferences/", json={"preference_type": "user_a_only_preference_mode", "initial_confidence": 0.9}, headers=headers_a)

        # User B queries their dashboard
        dash_b = client.get("/dashboard/", headers=headers_b).json()

        dash_b_str = str(dash_b)
        assert "Proprietary Algorithm A" not in dash_b_str
        assert "user_a_only_preference_mode" not in dash_b_str


def test_dashboard_handles_new_user_with_no_history_gracefully():
    with TestClient(app) as client:
        headers_new = _register_and_auth(client, "fresh_user")

        res = client.get("/dashboard/", headers=headers_new)
        assert res.status_code == 200
        data = res.json()

        assert "current_focus" in data
        assert "rising_concepts" in data
        assert "stagnant_or_struggling_concepts" in data
        assert "active_preferences" in data
        assert "goals_needing_attention" in data
        assert "reflections" in data

        assert len(data["rising_concepts"]) == 0
        assert len(data["stagnant_or_struggling_concepts"]) == 0
        assert len(data["active_preferences"]) == 0
        assert len(data["reflections"]) >= 1
        assert "Welcome to MindVault" in data["reflections"][0]
