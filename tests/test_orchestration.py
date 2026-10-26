import pytest

from agent.models.states import AgentState
from agent.services.campaign_orchestrator import (
    CampaignOrchestrator,
    DraftGatewayError,
    DraftResult,
    can_execute_email,
)
from agent.services.workflow_service import create_workflow
from database.models import EmailRecord, Workflow


class SuccessfulGateway:
    def create_and_verify_draft(self, email):
        return DraftResult(verified=True, draft_id="draft-1")


class FailingGateway:
    def create_and_verify_draft(self, email):
        raise DraftGatewayError("draft creation failed")


def _approved_email(db_session, client, contact_payload):
    contact = client.post("/contacts", json=contact_payload()).json()
    campaign = client.post("/campaigns", json={"name": "Campaign"}).json()
    email = EmailRecord(
        contact_id=contact["id"],
        campaign_id=campaign["id"],
        recipient=contact["email"],
        subject="Hello",
        body="Let us connect.",
        status=AgentState.APPROVED.value,
    )
    db_session.add(email)
    db_session.flush()
    create_workflow(
        db_session,
        workflow_type="OUTREACH",
        context={"email_id": email.id},
        initial_state=AgentState.APPROVED,
    )
    db_session.commit()
    return email


def test_orchestrator_creates_and_verifies_draft_after_approval(
    client, db_session, contact_payload
):
    email = _approved_email(db_session, client, contact_payload)
    assert can_execute_email(email)

    updated = CampaignOrchestrator(SuccessfulGateway()).execute_approved_email(db_session, email)

    assert updated.status == AgentState.VERIFIED.value
    workflow = db_session.query(Workflow).filter_by(workflow_type="OUTREACH").one()
    assert workflow.current_state == AgentState.VERIFIED.value


def test_orchestrator_refuses_unapproved_email(db_session, client, contact_payload):
    email = _approved_email(db_session, client, contact_payload)
    email.status = "READY_FOR_APPROVAL"
    db_session.commit()

    with pytest.raises(DraftGatewayError, match="APPROVED"):
        CampaignOrchestrator(SuccessfulGateway()).execute_approved_email(db_session, email)


def test_orchestrator_marks_execution_failure_without_leaking_details(
    client, db_session, contact_payload
):
    email = _approved_email(db_session, client, contact_payload)

    with pytest.raises(DraftGatewayError, match="draft creation failed"):
        CampaignOrchestrator(FailingGateway()).execute_approved_email(db_session, email)

    assert email.status == AgentState.ERROR.value
    workflow = db_session.query(Workflow).filter_by(workflow_type="OUTREACH").one()
    assert workflow.current_state == AgentState.ERROR.value
