from sqlalchemy import inspect


def test_no_email_sending_endpoint_exists(client):
    assert client.post("/send").status_code == 404
    assert client.post("/emails/send").status_code in (404, 405)
    assert client.post("/send-email").status_code == 404
    assert client.post("/gmail/send").status_code == 404
    assert client.get("/gmail").status_code == 404


def test_no_credential_storage_tables(db_session):
    tables = set(inspect(db_session.bind).get_table_names())
    assert not any(
        credential_table in tables
        for credential_table in ("credentials", "tokens", "sessions", "secrets")
    )


def test_no_secret_columns_anywhere(db_session):
    inspector = inspect(db_session.bind)
    for table in inspector.get_table_names():
        columns = {c["name"] for c in inspector.get_columns(table)}
        assert not any(
            token in columns
            for token in ("password", "token", "api_key", "secret", "credential")
        ), f"secret-like column found in {table}"


def test_search_endpoint_never_triggers_web_automation(client):
    created = client.post(
        "/search",
        json={"classification": "AI/ML Professionals", "search_query": "computer vision"},
    ).json()
    assert created["status"] == "RECEIVED"
    assert created["profiles_found"] == 0
    assert client.get("/profiles").json() == []
    job = client.get(f"/search/{created['id']}").json()
    assert job["profiles_found"] == 0
    assert job["status"] == "RECEIVED"