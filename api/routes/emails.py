from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from agent.logging import actions
from agent.services.activity_service import log_activity
from agent.services.gemini.client import GeminiClient, GeminiError
from agent.services.gemini.generator import GeminiGenerator
from agent.services.gemini.models import GenerationInput
from agent.services.gemini.validator import EmailValidationError, validate_generated_email
from agent.models.states import AgentState
from agent.services.workflow_service import create_workflow, transition_workflow
from agent.validators import EmailCreate, EmailRead, EmailUpdate, ReviewDecision
from config.settings import get_settings
from database.models import Campaign, Contact, EmailRecord, Workflow
from database.session import get_db

router = APIRouter(prefix="/emails", tags=["emails"])


@router.post("/", response_model=EmailRead, status_code=201)
def create_email(payload: EmailCreate, db: Session = Depends(get_db)):
    if db.get(Contact, payload.contact_id) is None:
        raise HTTPException(status_code=422, detail="contact_id does not exist")
    if db.get(Campaign, payload.campaign_id) is None:
        raise HTTPException(status_code=422, detail="campaign_id does not exist")
    email = EmailRecord(**payload.model_dump(mode="json"))
    db.add(email)
    db.flush()
    log_activity(
        db,
        actions.EMAIL_GENERATED,
        {"email_id": email.id, "contact_id": email.contact_id, "campaign_id": email.campaign_id},
    )
    db.refresh(email)
    return email


@router.get("/", response_model=list[EmailRead])
def list_emails(
    contact_id: int | None = None,
    campaign_id: int | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
):
    stmt = select(EmailRecord).order_by(EmailRecord.created_at.desc(), EmailRecord.id.desc())
    if contact_id is not None:
        stmt = stmt.where(EmailRecord.contact_id == contact_id)
    if campaign_id is not None:
        stmt = stmt.where(EmailRecord.campaign_id == campaign_id)
    if status is not None:
        stmt = stmt.where(EmailRecord.status == status)
    return list(db.scalars(stmt).all())


@router.get("/{email_id}", response_model=EmailRead)
def get_email(email_id: int, db: Session = Depends(get_db)):
    email = db.get(EmailRecord, email_id)
    if email is None:
        raise HTTPException(status_code=404, detail="Email record not found")
    return email


@router.put("/{email_id}", response_model=EmailRead)
def update_email(email_id: int, payload: EmailUpdate, db: Session = Depends(get_db)):
    email = db.get(EmailRecord, email_id)
    if email is None:
        raise HTTPException(status_code=404, detail="Email record not found")
    workflow = _workflow_for_review(db, email)
    _require_review_state(email, workflow)

    subject = payload.subject if payload.subject is not None else email.subject
    body = payload.body if payload.body is not None else email.body
    contact = db.get(Contact, email.contact_id)
    if contact is None:
        raise HTTPException(status_code=422, detail="Contact not found")

    try:
        validated, _ = validate_generated_email(
            email.recipient,
            {
                "subject": subject,
                "body": body,
                "personalization_score": int(email.personalization_score or 0),
                "warnings": email.warnings or [],
            },
            _research_for(contact, workflow),
        )
    except EmailValidationError as exc:
        log_activity(db, actions.EMAIL_VALIDATION_BLOCKED, {"email_id": email.id, "reason": str(exc)})
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    email.subject = validated.subject
    email.body = validated.body
    email.warnings = validated.warnings
    email.status = "READY_FOR_APPROVAL"
    db.add(email)
    db.flush()
    log_activity(db, actions.EMAIL_EDITED, {"email_id": email.id})
    db.refresh(email)
    return email


def _workflow_for_review(db: Session, email: EmailRecord) -> Workflow:
    workflow = db.scalars(
        select(Workflow).where(Workflow.workflow_type == "OUTREACH")
    ).all()
    for candidate in workflow:
        if (candidate.context or {}).get("email_id") == email.id:
            return candidate
    raise HTTPException(status_code=409, detail="Email is not ready for human review")


def _require_review_state(email: EmailRecord, workflow: Workflow) -> None:
    if email.status != "READY_FOR_APPROVAL" or workflow.current_state != AgentState.WAITING_FOR_APPROVAL.value:
        raise HTTPException(status_code=409, detail="Email is not waiting for approval")


@router.post("/{email_id}/approve", response_model=EmailRead)
def approve_email(email_id: int, db: Session = Depends(get_db)):
    email = db.get(EmailRecord, email_id)
    if email is None:
        raise HTTPException(status_code=404, detail="Email record not found")
    workflow = _workflow_for_review(db, email)
    _require_review_state(email, workflow)

    transition_workflow(db, workflow.id, AgentState.APPROVED)
    email.status = "APPROVED"
    db.add(email)
    db.flush()
    log_activity(db, actions.EMAIL_APPROVED, {"email_id": email.id})
    db.refresh(email)
    return email


@router.post("/{email_id}/reject", response_model=EmailRead)
def reject_email(
    email_id: int,
    decision: ReviewDecision | None = None,
    db: Session = Depends(get_db),
):
    email = db.get(EmailRecord, email_id)
    if email is None:
        raise HTTPException(status_code=404, detail="Email record not found")
    workflow = _workflow_for_review(db, email)
    _require_review_state(email, workflow)

    transition_workflow(db, workflow.id, AgentState.REJECTED)
    email.status = "REJECTED"
    db.add(email)
    db.flush()
    details = {"email_id": email.id}
    if decision and decision.reason:
        details["reason"] = decision.reason
    log_activity(db, actions.EMAIL_REJECTED, details)
    db.refresh(email)
    return email


def _research_for(contact: Contact, workflow: Workflow | None) -> dict:
    profile = contact.profile
    if profile is None:
        return {}
    context = (workflow.context or {}) if workflow else {}
    return {
        "professional_summary": profile.professional_summary,
        "expertise": profile.role,
        "research_areas": profile.relevant_points or [],
        "projects": [],
        "achievements": [],
        "relevant_professional_interests": profile.relevant_points or [],
        "source_url": profile.profile_url or contact.public_url,
        "relevant_points": profile.relevant_points or [],
        "relevance_score": profile.relevance_score,
        "classification": profile.classification,
        "search_query": context.get("search_query"),
    }


def _workflow_for_email(db: Session, email: EmailRecord) -> Workflow:
    workflows = db.scalars(select(Workflow).where(Workflow.workflow_type == "OUTREACH")).all()
    for workflow in workflows:
        if (workflow.context or {}).get("email_id") == email.id:
            return workflow
    return create_workflow(
        db,
        workflow_type="OUTREACH",
        context={"email_id": email.id, "contact_id": email.contact_id, "campaign_id": email.campaign_id},
        initial_state=AgentState.PROFILE_RESEARCHED,
    )


@router.post("/{email_id}/generate", response_model=EmailRead)
def generate_email(email_id: int, db: Session = Depends(get_db)):
    email = db.get(EmailRecord, email_id)
    if email is None:
        raise HTTPException(status_code=404, detail="Email record not found")
    contact = db.get(Contact, email.contact_id)
    campaign = db.get(Campaign, email.campaign_id)
    if contact is None:
        raise HTTPException(status_code=422, detail="Contact not found")
    if campaign is None:
        raise HTTPException(status_code=422, detail="Campaign not found")

    workflow = _workflow_for_email(db, email)
    log_activity(db, actions.EMAIL_GENERATION_STARTED, {"email_id": email.id})
    try:
        if workflow.current_state == AgentState.PROFILE_RESEARCHED.value:
            workflow = transition_workflow(db, workflow.id, AgentState.GENERATING)
        settings = get_settings()
        log_activity(
            db,
            actions.GEMINI_REQUEST_STARTED,
            {"email_id": email.id, "provider": "gemini" if settings.gemini_api_key else "mock"},
        )
        generator = GeminiGenerator(
            GeminiClient(settings.gemini_api_key, settings.gemini_model)
        )
        research = _research_for(contact, workflow)
        generated, provider = generator.generate(
            GenerationInput(
                recipient={
                    "name": contact.name,
                    "email": contact.email,
                    "role": contact.role,
                    "company": contact.company,
                    "public_profile_url": contact.public_url,
                },
                research=research,
                campaign={
                    "objective": campaign.objective,
                    "sender_information": campaign.sender_info,
                    "tone": campaign.tone,
                    "instructions": campaign.instructions,
                },
            )
        )
        log_activity(db, actions.GEMINI_RESPONSE_RECEIVED, {"email_id": email.id, "provider": provider})
        workflow = transition_workflow(db, workflow.id, AgentState.VALIDATING)
        log_activity(db, actions.EMAIL_VALIDATION_STARTED, {"email_id": email.id})
        email.recipient = contact.email
        email.subject = generated.subject
        email.body = generated.body
        email.personalization_score = generated.personalization_score
        email.warnings = generated.warnings
        email.status = "READY_FOR_APPROVAL"
        db.add(email)
        db.flush()
        log_activity(db, actions.EMAIL_VALIDATED, {"email_id": email.id})
        if generated.warnings:
            log_activity(db, actions.EMAIL_VALIDATION_WARNING, {"email_id": email.id, "count": len(generated.warnings)})
        log_activity(db, actions.EMAIL_GENERATED, {"email_id": email.id, "provider": provider})
        transition_workflow(db, workflow.id, AgentState.WAITING_FOR_APPROVAL)
        log_activity(db, actions.EMAIL_READY_FOR_APPROVAL, {"email_id": email.id})
        log_activity(db, actions.EMAIL_WAITING_FOR_APPROVAL, {"email_id": email.id})
        db.refresh(email)
        return email
    except EmailValidationError as exc:
        log_activity(db, actions.EMAIL_VALIDATION_BLOCKED, {"email_id": email.id, "reason": str(exc)})
        if workflow.current_state in {AgentState.GENERATING.value, AgentState.VALIDATING.value}:
            transition_workflow(db, workflow.id, AgentState.ERROR)
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except GeminiError as exc:
        log_activity(db, actions.GEMINI_ERROR, {"email_id": email.id, "reason": str(exc)})
        if workflow.current_state == AgentState.GENERATING.value:
            transition_workflow(db, workflow.id, AgentState.ERROR)
        raise HTTPException(status_code=502, detail="Gemini generation failed") from exc
    except Exception as exc:
        log_activity(db, actions.EMAIL_GENERATION_FAILED, {"email_id": email.id, "reason": type(exc).__name__})
        if workflow.current_state in {AgentState.GENERATING.value, AgentState.VALIDATING.value}:
            transition_workflow(db, workflow.id, AgentState.ERROR)
        raise
