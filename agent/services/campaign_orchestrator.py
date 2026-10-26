from dataclasses import dataclass
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from agent.logging import actions
from agent.models.states import AgentState
from agent.services.activity_service import log_activity
from agent.services.workflow_service import transition_workflow
from database.models import Campaign, Contact, EmailRecord, Workflow


class DraftGatewayError(RuntimeError):
    """A safe, non-secret failure from the draft-only browser gateway."""


class DraftGateway(Protocol):
    def create_and_verify_draft(self, email: EmailRecord) -> "DraftResult": ...


@dataclass(frozen=True)
class DraftResult:
    verified: bool
    draft_id: str | None = None


class WebcmdGmailDraftGateway:
    """Integration boundary for the installed Webcmd browser runtime.

    A Gmail adapter is intentionally not guessed here. Until a supported,
    authenticated Gmail flow is configured, execution fails closed.
    """

    def create_and_verify_draft(self, email: EmailRecord) -> DraftResult:
        raise DraftGatewayError("Webcmd Gmail draft integration is not configured")


def can_execute_email(email: EmailRecord) -> bool:
    """Return whether the persisted email status is approved for Phase 5."""

    return email.status == AgentState.APPROVED.value


def _workflow_for_email(db: Session, email: EmailRecord) -> Workflow | None:
    workflows = db.scalars(
        select(Workflow).where(Workflow.workflow_type == "OUTREACH")
    ).all()
    return next(
        (workflow for workflow in workflows if (workflow.context or {}).get("email_id") == email.id),
        None,
    )


class CampaignOrchestrator:
    """Coordinates persisted campaign work without approving or sending mail."""

    def __init__(self, draft_gateway: DraftGateway | None = None):
        self.draft_gateway = draft_gateway or WebcmdGmailDraftGateway()

    def execute_approved_email(self, db: Session, email: EmailRecord) -> EmailRecord:
        workflow = _workflow_for_email(db, email)
        if workflow is None or workflow.current_state != AgentState.APPROVED.value:
            raise DraftGatewayError("Email is not in the APPROVED workflow state")
        if not can_execute_email(email):
            raise DraftGatewayError("Only APPROVED emails may enter execution")

        log_activity(db, actions.EMAIL_EXECUTION_STARTED, {"email_id": email.id})
        try:
            transition_workflow(db, workflow.id, AgentState.EXECUTING)
            result = self.draft_gateway.create_and_verify_draft(email)
            if not result.verified:
                raise DraftGatewayError("Gmail draft verification failed")
            transition_workflow(db, workflow.id, AgentState.DRAFTED)
            log_activity(db, actions.GMAIL_DRAFT_CREATED, {"email_id": email.id})
            transition_workflow(db, workflow.id, AgentState.VERIFIED)
            email.status = AgentState.VERIFIED.value
            db.add(email)
            db.commit()
            log_activity(db, actions.GMAIL_DRAFT_VERIFIED, {"email_id": email.id})
            db.refresh(email)
            return email
        except Exception as exc:
            workflow = db.get(Workflow, workflow.id)
            if workflow and workflow.current_state == AgentState.EXECUTING.value:
                transition_workflow(db, workflow.id, AgentState.ERROR)
            email.status = AgentState.ERROR.value
            db.add(email)
            db.commit()
            log_activity(
                db,
                actions.EMAIL_EXECUTION_FAILED,
                {"email_id": email.id, "reason": type(exc).__name__},
            )
            raise

    def process_campaign(self, db: Session, campaign: Campaign) -> None:
        if campaign.status != "RUNNING":
            return
        emails = db.scalars(
            select(EmailRecord).where(EmailRecord.campaign_id == campaign.id)
        ).all()
        for email in emails:
            if campaign.status != "RUNNING":
                break
            if email.status in {AgentState.VERIFIED.value, AgentState.REJECTED.value}:
                continue
            if can_execute_email(email):
                try:
                    self.execute_approved_email(db, email)
                except Exception:
                    continue

        if campaign.status == "RUNNING" and emails and all(
            email.status in {AgentState.VERIFIED.value, AgentState.REJECTED.value}
            for email in emails
        ):
            campaign.status = "COMPLETED"
            db.add(campaign)
            db.commit()
            log_activity(db, actions.CAMPAIGN_COMPLETED, {"campaign_id": campaign.id})


def campaign_status(db: Session, campaign: Campaign) -> dict:
    emails = db.scalars(
        select(EmailRecord).where(EmailRecord.campaign_id == campaign.id)
    ).all()
    contact_ids = {email.contact_id for email in emails}
    contacts = db.scalars(select(Contact).where(Contact.id.in_(contact_ids))).all() if contact_ids else []
    return {
        "campaign_id": campaign.id,
        "total_profiles": sum(contact.profile is not None for contact in contacts),
        "relevant_profiles": sum(
            contact.profile is not None and (contact.profile.relevance_score or 0) > 0
            for contact in contacts
        ),
        "emails_generated": len(emails),
        "waiting_for_approval": sum(email.status == "READY_FOR_APPROVAL" for email in emails),
        "approved": sum(email.status == AgentState.APPROVED.value for email in emails),
        "rejected": sum(email.status == AgentState.REJECTED.value for email in emails),
        "drafts_created": sum(email.status in {"DRAFTED", AgentState.VERIFIED.value} for email in emails),
        "drafts_verified": sum(email.status == AgentState.VERIFIED.value for email in emails),
        "failed": sum(email.status == AgentState.ERROR.value for email in emails),
        "current_campaign_state": campaign.status,
    }
