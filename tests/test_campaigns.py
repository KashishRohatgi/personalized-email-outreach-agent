def _campaign_payload(**overrides):
    payload = {
        "name": "Summer Outreach",
        "objective": "Introduce our platform to AI researchers",
        "sender_info": "Jane at Acme AI <jane@acme-ai.com>",
        "tone": "Professional but warm",
        "instructions": "Mention specific projects where relevant",
        "status": "DRAFT",
    }
    payload.update(overrides)
    return payload


def test_campaign_creation(client):
    response = client.post("/campaigns", json=_campaign_payload())
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Summer Outreach"
    assert data["status"] == "DRAFT"


def test_campaign_retrieval(client):
    created = client.post("/campaigns", json=_campaign_payload()).json()
    single = client.get(f"/campaigns/{created['id']}")
    assert single.status_code == 200
    assert single.json()["objective"] == "Introduce our platform to AI researchers"

    listed = client.get("/campaigns")
    assert listed.status_code == 200
    assert len(listed.json()) == 1


def test_campaign_default_status(client):
    response = client.post("/campaigns", json={"name": "Autumn Outreach"})
    assert response.status_code == 201
    assert response.json()["status"] == "DRAFT"


def test_campaign_not_found(client):
    assert client.get("/campaigns/9999").status_code == 404