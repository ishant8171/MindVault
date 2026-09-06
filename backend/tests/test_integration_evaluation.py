import uuid
from fastapi.testclient import TestClient

from app.main import app


def _register_and_auth(client, unique=None):
    if unique is None:
        unique = uuid.uuid4().hex[:8]
    email = f"test+{unique}@example.com"
    username = f"tester_{unique}"
    pw = "strongpassword"
    r = client.post("/auth/register", json={"email": email, "username": username, "password": pw})
    assert r.status_code == 201
    login = client.post("/auth/login", data={"username": email, "password": pw})
    assert login.status_code == 200
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_controlled_dataset_evaluation(monkeypatch):
    """Integration-style evaluation using a small deterministic dataset.

    This test exercises multiple backend flows: memory storage, retrieval,
    conflict detection/resolution, knowledge graph creation/traversal, and
    extraction (AI provider mocked). It computes simple metrics over the
    synthetic dataset and asserts expected outcomes for our controlled inputs.
    """

    # Controlled dataset (synthetic)
    dataset = [
        {"label": "long_term_pref", "content": "I prefer dark mode on by default", "category": "preference", "slot_key": "ui_pref", "importance_score": 0.8},
        {"label": "temp_info", "content": "My one-time code is 12345 until tomorrow", "category": "temporary", "slot_key": "otp_code", "importance_score": 0.1},
        {"label": "goal_alpha", "content": "Finish project Alpha by end of quarter", "category": "goal", "slot_key": "goal_alpha", "importance_score": 0.9},
        {"label": "skill_python", "content": "Proficient in Python and SQL", "category": "skill", "slot_key": "skill_prog", "importance_score": 0.7},
        {"label": "project_x", "content": "Working on project X regarding ML", "category": "project", "slot_key": "project_X", "importance_score": 0.6},
        # two genuine conflicts (same slot_key, different content)
        {"label": "city_old", "content": "I live in Boston", "category": "personal", "slot_key": "city", "importance_score": 0.5},
        {"label": "city_new", "content": "I live in New York", "category": "personal", "slot_key": "city", "importance_score": 0.6},
        # related words but different slots -> not a conflict (should both be stored)
        {"label": "dessert_like", "content": "I like apple pie", "category": "preference", "slot_key": "dessert1", "importance_score": 0.2},
        {"label": "tech_pref", "content": "Apple is my favorite company", "category": "preference", "slot_key": "preference_tech", "importance_score": 0.3},
    ]

    # Mock AI extraction to produce deterministic candidate output when /memories/extract is called
    extracted_candidates = [
        {"content": "Remember to submit report", "slot_key": "submit_report", "category": "important_event", "confidence_score": 0.8},
    ]

    fake_extract_text = '[{"content": "Remember to submit report", "slot_key": "submit_report", "category": "important_event", "confidence_score": 0.8}]'
    fake_resp = {"choices": [{"message": {"content": fake_extract_text}}]}
    monkeypatch.setattr("app.services.ai_service.generate_text", lambda prompt, system_message=None, **kwargs: fake_resp)

    with TestClient(app) as client:
        headers = _register_and_auth(client)

        # 1) Create dataset memories (except the conflicting second element will be tested)
        created = {}
        for item in dataset:
            # For the second city entry, expect conflict behavior
            if item["label"] == "city_new":
                # first ensure old exists
                pass
            resp = client.post("/memories/", json={"content": item["content"], "category": item["category"], "slot_key": item["slot_key"], "importance_score": item.get("importance_score")}, headers=headers)
            # For the second city (conflict) we expect a 409; handle that below
            if item["label"] == "city_new":
                assert resp.status_code == 409
                conflict_id = resp.json()["detail"]["conflict_id"]
            else:
                assert resp.status_code == 201
                created[item["label"]] = resp.json()

        # 2) Conflict detection: we should have a conflict id from attempting to add city_new
        assert "conflict_id" in locals()

        # 3) Resolve conflict - keep_old (preserve Boston)
        r = client.post(f"/memories/conflicts/{conflict_id}/resolve", json={"action": "keep_old"}, headers=headers)
        assert r.status_code == 200
        assert r.json().get("resolution") in ("kept_old", "kept_old_and_archived") or "kept_old" in r.json().get("resolution", "kept_old")

        # 4) Retrieval relevance: query for "dark mode" should return the long_term_pref memory top
        resp = client.post("/memories/retrieve", json={"query": "dark mode", "limit": 5}, headers=headers)
        assert resp.status_code == 200
        results = resp.json()["results"]
        assert len(results) >= 1
        # ensure the top result refers to our long_term_pref
        top = results[0]
        assert "dark mode" in top["content"].lower()

        # 5) Privacy/ownership boundaries: another user should not list or get these memories
        headers_b = _register_and_auth(client)
        list_b = client.get("/memories/", headers=headers_b)
        assert list_b.status_code == 200
        ids_b = {m["id"] for m in list_b.json()}
        # none of created ids should be visible to user B
        assert not any(cid in ids_b for cid in [v["id"] for v in created.values()])

        # 6) Extraction endpoint (mocked) should return our deterministic candidate
        ext = client.post("/memories/extract", json={"text": "Please extract important items"}, headers=headers)
        assert ext.status_code == 200
        cands = ext.json().get("candidates", [])
        # measure extraction accuracy: expected 1 candidate and content match
        expected = extracted_candidates
        matched = 0
        for e in expected:
            if any(e["content"] == c.get("content") for c in cands):
                matched += 1
        extraction_accuracy = matched / len(expected)
        assert extraction_accuracy == 1.0

        # 7) Knowledge graph: create goal & skill and connect them, then traverse
        gr = client.post("/goals/", json={"title": "Integrate test goal"}, headers=headers)
        assert gr.status_code == 201
        goal = gr.json()
        sr = client.post("/skills/", json={"name": "IntegrationSkill"}, headers=headers)
        assert sr.status_code == 201
        skill = sr.json()

        gn = client.post("/knowledge/nodes/", json={"node_type": "goal", "label": "Integrate test goal", "ref_id": goal["id"]}, headers=headers)
        assert gn.status_code == 201
        goal_node = gn.json()
        skn = client.post("/knowledge/nodes/", json={"node_type": "skill", "label": "IntegrationSkill", "ref_id": skill["id"]}, headers=headers)
        assert skn.status_code == 201
        skill_node = skn.json()
        # create relationship
        rel = client.post("/knowledge/relationships/", json={"source_node_id": goal_node["id"], "target_node_id": skill_node["id"], "relationship_type": "requires"}, headers=headers)
        assert rel.status_code == 201
        trav = client.get(f"/knowledge/traverse/?start={goal_node['id']}&depth=1", headers=headers)
        assert trav.status_code == 200
        nodes = {n["id"] for n in trav.json()["nodes"]}
        assert skill_node["id"] in nodes

        # If we reach here, basic evaluation metrics computed above are as-expected
