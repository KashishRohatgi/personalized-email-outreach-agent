from database.models import ActivityLog, Workflow
from types import SimpleNamespace


def _setup(client, contact_payload):
    contact = client.post("/contacts", json=contact_payload()).json()
    campaign = client.post(
        "/campaigns", json={"name": "Summer Outreach", "objective": "Intro AI platform"}
    ).json()
    return contact, campaign


def _email_payload(contact, campaign):
    return {
        "contact_id": contact["id"],
        "campaign_id": campaign["id"],
        "recipient": "ada@example.com",
        "subject": "Intro to Acme AI",
        "body": "Hi Ada, I noticed your work on algorithmic computing.",
        "personalization_score": 82.0,
        "warnings": ["Relevance score below 90"],
        "status": "DRAFT",
    }


def _force_mock_generation(monkeypatch):
    monkeypatch.setattr(
        "api.routes.emails.get_settings",
        lambda: SimpleNamespace(gemini_api_key=None, gemini_model="gemini-2.5-flash"),
    )


def test_email_record_creation(client, contact_payload):
    contact, campaign = _setup(client, contact_payload)
    response = client.post("/emails", json=_email_payload(contact, campaign))
    assert response.status_code == 201
    data = response.json()
    assert data["recipient"] == "ada@example.com"
    assert data["campaign_id"] == campaign["id"]
    assert data["contact_id"] == contact["id"]
    assert data["status"] == "DRAFT"


def test_email_record_retrieval(client, contact_payload):
    contact, campaign = _setup(client, contact_payload)
    created = client.post("/emails", json=_email_payload(contact, campaign)).json()
    single = client.get(f"/emails/{created['id']}")
    assert single.status_code == 200
    assert single.json()["subject"] == "Intro to Acme AI"

    listed = client.get("/emails")
    assert listed.status_code == 200
    assert len(listed.json()) == 1


def test_email_record_filters(client, contact_payload):
    contact, campaign = _setup(client, contact_payload)
    client.post("/emails", json=_email_payload(contact, campaign))
    filtered = client.get("/emails", params={"campaign_id": campaign["id"]})
    assert len(filtered.json()) == 1
    miss = client.get("/emails", params={"campaign_id": 9999})
    assert len(miss.json()) == 0


def test_email_requires_existing_contact_and_campaign(client, contact_payload):
    contact, _ = _setup(client, contact_payload)
    missing_campaign = client.post(
        "/emails",
        json={
            "contact_id": contact["id"],
            "campaign_id": 9999,
            "recipient": "ada@example.com",
            "body": "hi",
        },
    )
    assert missing_campaign.status_code == 422

    missing_contact = client.post(
        "/emails",
        json={"contact_id": 9999, "campaign_id": 1, "recipient": "ada@example.com", "body": "hi"},
    )
    assert missing_contact.status_code == 422


def test_email_record_not_found(client):
    assert client.get("/emails/9999").status_code == 404


def test_mock_generation_persists_and_reaches_approval_state(
    client, db_session, contact_payload, monkeypatch
):
    _force_mock_generation(monkeypatch)
    contact, campaign = _setup(client, contact_payload)
    profile = client.post(
        "/profiles",
        json={
            "name": contact["name"],
            "role": "AI researcher",
            "company": "Analytical Engines",
            "professional_summary": "Researches computer vision",
            "relevant_points": ["computer vision"],
            "research_status": "COMPLETED",
        },
    ).json()
    updated = client.put(f"/contacts/{contact['id']}", json={"profile_id": profile["id"]})
    assert updated.status_code == 200
    email = client.post("/emails", json=_email_payload(contact, campaign)).json()

    generated = client.post(f"/emails/{email['id']}/generate")
    assert generated.status_code == 200
    assert generated.json()["status"] == "READY_FOR_APPROVAL"
    assert "MOCK_GENERATION" in generated.json()["warnings"][0]

    workflow = db_session.query(Workflow).filter_by(workflow_type="OUTREACH").first()
    assert workflow.current_state == "WAITING_FOR_APPROVAL"
    actions = [row.action for row in db_session.query(ActivityLog).all()]
    assert "EMAIL_GENERATION_STARTED" in actions
    assert "EMAIL_READY_FOR_APPROVAL" in actions


def test_human_approval_updates_email_and_workflow_without_execution(
    client, db_session, contact_payload, monkeypatch
):
    _force_mock_generation(monkeypatch)
    contact, campaign = _setup(client, contact_payload)
    email = client.post("/emails", json=_email_payload(contact, campaign)).json()
    generated = client.post(f"/emails/{email['id']}/generate")
    assert generated.status_code == 200

    approved = client.post(f"/emails/{email['id']}/approve")
    assert approved.status_code == 200
    assert approved.json()["status"] == "APPROVED"
    workflow = db_session.query(Workflow).filter_by(workflow_type="OUTREACH").first()
    assert workflow.current_state == "APPROVED"
    assert db_session.query(ActivityLog).filter_by(action="EMAIL_APPROVED").count() == 1

    assert client.post(f"/emails/{email['id']}/approve").status_code == 409


def test_human_rejection_records_reason_and_requires_review_state(
    client, db_session, contact_payload, monkeypatch
):
    _force_mock_generation(monkeypatch)
    contact, campaign = _setup(client, contact_payload)
    email = client.post("/emails", json=_email_payload(contact, campaign)).json()
    client.post(f"/emails/{email['id']}/generate")

    rejected = client.post(
        f"/emails/{email['id']}/reject", json={"reason": "Needs a more specific opening"}
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "REJECTED"
    workflow = db_session.query(Workflow).filter_by(workflow_type="OUTREACH").first()
    assert workflow.current_state == "REJECTED"
    activity = db_session.query(ActivityLog).filter_by(action="EMAIL_REJECTED").one()
    assert activity.details["reason"] == "Needs a more specific opening"


def test_human_review_can_edit_and_revalidate_email(client, db_session, contact_payload, monkeypatch):
    _force_mock_generation(monkeypatch)
    contact, campaign = _setup(client, contact_payload)
    email = client.post("/emails", json=_email_payload(contact, campaign)).json()
    client.post(f"/emails/{email['id']}/generate")

    edited = client.put(
        f"/emails/{email['id']}",
        json={"subject": "A more relevant introduction", "body": "Would you be open to connecting?"},
    )
    assert edited.status_code == 200
    assert edited.json()["subject"] == "A more relevant introduction"
    assert edited.json()["body"] == "Would you be open to connecting?"
    assert edited.json()["status"] == "READY_FOR_APPROVAL"
    workflow = db_session.query(Workflow).filter_by(workflow_type="OUTREACH").first()
    assert workflow.current_state == "WAITING_FOR_APPROVAL"


def test_human_review_edit_rejects_invalid_content_without_mutation(
    client, contact_payload, monkeypatch
):
    _force_mock_generation(monkeypatch)
    contact, campaign = _setup(client, contact_payload)
    email = client.post("/emails", json=_email_payload(contact, campaign)).json()
    generated = client.post(f"/emails/{email['id']}/generate").json()

    invalid = client.put(
        f"/emails/{email['id']}",
        json={"body": "I saw your presentation at the conference."},
    )
    assert invalid.status_code == 422
    current = client.get(f"/emails/{email['id']}").json()
    assert current["body"] == generated["body"]
