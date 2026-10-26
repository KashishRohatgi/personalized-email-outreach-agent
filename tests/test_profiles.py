def _profile_payload():
    return {
        "name": "Ada Lovelace",
        "email": "ada@example.com",
        "profile_url": "https://www.linkedin.com/in/adalovelace",
        "source": "public-web",
        "role": "Researcher",
        "company": "Analytical Engines",
        "classification": "AI/ML Professionals",
        "relevance_score": 87.5,
        "professional_summary": "Pioneer of algorithmic computing.",
        "relevant_points": ["Wrote the first algorithm", "Worked on the Analytical Engine"],
        "research_status": "RESEARCHED",
    }


def test_profile_creation(client):
    response = client.post("/profiles", json=_profile_payload())
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Ada Lovelace"
    assert data["classification"] == "AI/ML Professionals"
    assert data["relevance_score"] == 87.5
    assert data["relevant_points"] == [
        "Wrote the first algorithm",
        "Worked on the Analytical Engine",
    ]
    assert "created_at" in data


def test_profile_retrieval(client):
    created = client.post("/profiles", json=_profile_payload()).json()
    response = client.get(f"/profiles/{created['id']}")
    assert response.status_code == 200
    assert response.json()["name"] == "Ada Lovelace"


def test_profile_not_found(client):
    assert client.get("/profiles/9999").status_code == 404


def test_list_profiles_with_filter(client):
    client.post("/profiles", json=_profile_payload())
    client.post(
        "/profiles",
        json={**_profile_payload(), "name": "Grace Hopper", "classification": "Software Engineers"},
    )
    response = client.get("/profiles", params={"classification": "AI/ML Professionals"})
    assert response.status_code == 200
    names = [item["name"] for item in response.json()]
    assert names == ["Ada Lovelace"]