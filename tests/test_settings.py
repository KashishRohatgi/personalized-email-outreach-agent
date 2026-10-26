def test_gemini_settings_can_be_saved_and_loaded(client):
    response = client.post(
        "/settings/gemini",
        json={"api_key": "test-gemini-key-123", "model": "gemini-2.5-flash"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["configured"] is True
    assert payload["model"] == "gemini-2.5-flash"

    loaded = client.get("/settings/gemini")
    assert loaded.status_code == 200
    assert loaded.json()["configured"] is True
    assert loaded.json()["model"] == "gemini-2.5-flash"
