from database.models import Workflow


def _search_payload(**overrides):
    payload = {
        "classification": "AI/ML Professionals",
        "search_query": "AI researchers working on computer vision",
        "source_urls": ["https://example.com/people"],
    }
    payload.update(overrides)
    return payload


def test_search_job_creation(client, db_session):
    response = client.post("/search", json=_search_payload())
    assert response.status_code == 201
    data = response.json()
    assert data["classification"] == "AI/ML Professionals"
    assert data["search_query"] == "AI researchers working on computer vision"
    assert data["source_urls"] == ["https://example.com/people"]
    assert data["status"] == "RECEIVED"
    assert data["profiles_found"] == 0
    assert data["profiles_relevant"] == 0

    workflow = db_session.query(Workflow).filter_by(workflow_type="SEARCH").first()
    assert workflow is not None
    assert workflow.current_state == "RECEIVED"
    assert workflow.context["search_job_id"] == data["id"]


def test_search_job_retrieval(client):
    created = client.post("/search", json=_search_payload()).json()
    single = client.get(f"/search/{created['id']}")
    assert single.status_code == 200
    assert single.json()["classification"] == "AI/ML Professionals"

    listed = client.get("/search")
    assert listed.status_code == 200
    assert len(listed.json()) == 1


def test_search_does_not_discover_profiles(client):
    response = client.post("/search", json=_search_payload())
    assert response.status_code == 201
    data = response.json()
    assert data["profiles_found"] == 0
    assert data["status"] == "RECEIVED"
    assert client.get("/profiles").json() == []


def test_search_job_not_found(client):
    assert client.get("/search/9999").status_code == 404