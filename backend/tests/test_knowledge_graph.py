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


def test_node_and_relationship_crud_and_traversal():
    with TestClient(app) as client:
        headers = _register_and_auth(client)

        # fetch current user id and create a user node representing self
        me = client.get("/auth/me", headers=headers)
        assert me.status_code == 200
        user_id = me.json()["id"]
        r = client.post("/knowledge/nodes/", json={"node_type": "user", "label": "me", "ref_id": user_id}, headers=headers)
        assert r.status_code == 201
        user_node = r.json()
        uid_node = user_node["id"]

        # create goal and skill via existing APIs
        gr = client.post("/goals/", json={"title": "Ship X"}, headers=headers)
        assert gr.status_code == 201
        goal = gr.json()

        sr = client.post("/skills/", json={"name": "Python"}, headers=headers)
        assert sr.status_code == 201
        skill = sr.json()

        # create goal node referencing goal
        gn = client.post("/knowledge/nodes/", json={"node_type": "goal", "label": "Ship X", "ref_id": goal["id"]}, headers=headers)
        assert gn.status_code == 201
        goal_node = gn.json()

        # create skill node referencing skill
        skn = client.post("/knowledge/nodes/", json={"node_type": "skill", "label": "Python", "ref_id": skill["id"]}, headers=headers)
        assert skn.status_code == 201
        skill_node = skn.json()

        # link user -> has_goal -> goal
        rel1 = client.post("/knowledge/relationships/", json={"source_node_id": uid_node, "target_node_id": goal_node["id"], "relationship_type": "has_goal"}, headers=headers)
        assert rel1.status_code == 201

        # link goal -> requires -> skill
        rel2 = client.post("/knowledge/relationships/", json={"source_node_id": goal_node["id"], "target_node_id": skill_node["id"], "relationship_type": "requires"}, headers=headers)
        assert rel2.status_code == 201

        # traverse from user, depth 2 should reach skill
        trav = client.get(f"/knowledge/traverse/?start={uid_node}&depth=2", headers=headers)
        assert trav.status_code == 200
        data = trav.json()
        node_ids = {n["id"] for n in data["nodes"]}
        assert skill_node["id"] in node_ids

        # gaps: user has no skills, so missing should include Python
        gaps = client.get(f"/knowledge/goal_gaps/{goal_node['id']}", headers=headers)
        assert gaps.status_code == 200
        gdata = gaps.json()
        missing = gdata["missing_skills"]
        assert any(s["label"] == "Python" for s in missing)


def test_invalid_relationship_and_isolation():
    with TestClient(app) as client:
        headers_a = _register_and_auth(client)
        # create nodes for user A
        mea = client.get("/auth/me", headers=headers_a)
        assert mea.status_code == 200
        uid = mea.json()["id"]
        r = client.post("/knowledge/nodes/", json={"node_type": "user", "label": "me", "ref_id": uid}, headers=headers_a)
        ua = r.json()["id"]
        # create second user
        headers_b = _register_and_auth(client)
        meb = client.get("/auth/me", headers=headers_b)
        assert meb.status_code == 200
        user_b_id = meb.json()["id"]
        rb = client.post("/knowledge/nodes/", json={"node_type": "user", "label": "them", "ref_id": user_b_id}, headers=headers_b)
        ub = rb.json()["id"]

        # user A cannot create relationship using user B's node
        bad = client.post("/knowledge/relationships/", json={"source_node_id": ua, "target_node_id": ub, "relationship_type": "has_goal"}, headers=headers_a)
        assert bad.status_code == 400
