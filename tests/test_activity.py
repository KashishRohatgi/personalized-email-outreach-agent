def test_activity_logging_after_contact_creation(client, contact_payload):
    client.post("/contacts", json=contact_payload())
    response = client.get("/activity")
    assert response.status_code == 200
    actions = [item["action"] for item in response.json()]
    assert "CONTACT_CREATED" in actions


def test_activity_filter_by_action(client, contact_payload):
    client.post("/contacts", json=contact_payload())
    client.post("/contacts", json=contact_payload(name="Grace Hopper"))
    filtered = client.get("/activity", params={"action": "CONTACT_CREATED"})
    assert all(item["action"] == "CONTACT_CREATED" for item in filtered.json())


def test_activity_logs_search_started(client):
    client.post(
        "/search",
        json={"classification": "AI/ML Professionals", "search_query": "computer vision"},
    )
    response = client.get("/activity")
    actions = [item["action"] for item in response.json()]
    assert "SEARCH_STARTED" in actions


def test_activity_log_has_no_secret_columns(db_session):
    from sqlalchemy import inspect

    columns = {c["name"] for c in inspect(db_session.bind).get_columns("activity_logs")}
    assert not any(
        token in columns for token in ("token", "password", "api_key", "secret", "credentials")
    )
    assert columns == {"id", "action", "details", "timestamp"}