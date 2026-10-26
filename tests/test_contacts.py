from database.models import Contact, Profile


def test_contact_creation(client, contact_payload):
    response = client.post("/contacts", json=contact_payload())
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "ada@example.com"
    assert data["company"] == "Analytical Engines"


def test_contact_retrieval_and_listing(client, contact_payload):
    created = client.post("/contacts", json=contact_payload()).json()
    single = client.get(f"/contacts/{created['id']}")
    assert single.status_code == 200
    assert single.json()["name"] == "Ada Lovelace"

    listed = client.get("/contacts")
    assert listed.status_code == 200
    assert len(listed.json()) == 1


def test_contact_update(client, contact_payload):
    created = client.post("/contacts", json=contact_payload()).json()
    response = client.put(f"/contacts/{created['id']}", json={"company": "New Company"})
    assert response.status_code == 200
    assert response.json()["company"] == "New Company"
    assert response.json()["name"] == "Ada Lovelace"


def test_contact_delete(client, contact_payload):
    created = client.post("/contacts", json=contact_payload()).json()
    assert client.delete(f"/contacts/{created['id']}").status_code == 204
    assert client.get(f"/contacts/{created['id']}").status_code == 404


def test_contact_not_found(client):
    assert client.get("/contacts/9999").status_code == 404
    assert client.put("/contacts/9999", json={"name": "X"}).status_code == 404
    assert client.delete("/contacts/9999").status_code == 404


def test_profile_to_contact_relationship(client, contact_payload, db_session):
    profile_response = client.post(
        "/profiles",
        json={
            "name": "Grace Hopper",
            "classification": "Software Engineers",
        },
    )
    assert profile_response.status_code == 201
    profile_id = profile_response.json()["id"]

    contact_response = client.post(
        "/contacts",
        json=contact_payload(name="Grace Hopper", profile_id=profile_id),
    )
    assert contact_response.status_code == 201
    assert contact_response.json()["profile_id"] == profile_id

    saved_contact = db_session.get(Contact, contact_response.json()["id"])
    assert saved_contact.profile is not None
    assert saved_contact.profile.id == profile_id
    profile = db_session.get(Profile, profile_id)
    assert any(c.id == saved_contact.id for c in profile.contacts)


def test_contact_with_unknown_profile_rejected(client, contact_payload):
    response = client.post("/contacts", json=contact_payload(profile_id=424242))
    assert response.status_code == 422