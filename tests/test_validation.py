def test_invalid_email_rejected(client, contact_payload):
    response = client.post("/contacts", json=contact_payload(email="not-an-email"))
    assert response.status_code == 422


def test_blank_email_rejected(client, contact_payload):
    response = client.post("/contacts", json=contact_payload(email="   "))
    assert response.status_code == 422


def test_missing_required_fields_rejected(client):
    assert client.post("/profiles", json={}).status_code == 422
    assert client.post("/contacts", json={}).status_code == 422
    assert client.post("/campaigns", json={}).status_code == 422
    assert client.post("/search", json={}).status_code == 422


def test_custom_classification_supported(client):
    payload = {
        "classification": "Blockchain Architects",
        "search_query": "find blockchain architects in Berlin",
    }
    response = client.post("/search", json=payload)
    assert response.status_code == 201
    assert response.json()["classification"] == "Blockchain Architects"


def test_blank_classification_rejected(client):
    response = client.post("/search", json={"classification": "   ", "search_query": "x"})
    assert response.status_code == 422


def test_blank_search_query_rejected(client):
    response = client.post("/search", json={"classification": "X", "search_query": ""})
    assert response.status_code == 422


def test_invalid_profile_url_rejected(client):
    response = client.post(
        "/profiles",
        json={"name": "Ada", "profile_url": "not-a-url"},
    )
    assert response.status_code == 422


def test_invalid_source_url_rejected(client):
    response = client.post(
        "/search",
        json={"classification": "X", "search_query": "x", "source_urls": ["ftp://nope"]},
    )
    assert response.status_code == 422


def test_relevance_score_range_enforced(client):
    assert client.post("/profiles", json={"name": "Ada", "relevance_score": 101}).status_code == 422
    assert client.post("/profiles", json={"name": "Ada", "relevance_score": -1}).status_code == 422


def test_email_recipient_validation(client, contact_payload):
    contact = client.post("/contacts", json=contact_payload()).json()
    campaign = client.post("/campaigns", json={"name": "C"}).json()
    response = client.post(
        "/emails",
        json={
            "contact_id": contact["id"],
            "campaign_id": campaign["id"],
            "recipient": "not-an-email",
            "body": "hi",
        },
    )
    assert response.status_code == 422