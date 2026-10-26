from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from agent.logging import actions
from agent.services.activity_service import log_activity
from agent.services.campaign_orchestrator import CampaignOrchestrator, campaign_status
from agent.models.states import AgentState
from agent.services.workflow_service import transition_workflow
from agent.validators import CampaignCreate, CampaignRead, CampaignStatusRead
from database.models import Campaign, EmailRecord, Workflow
from database.session import get_db

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


@router.post("/", response_model=CampaignRead, status_code=201)
def create_campaign(payload: CampaignCreate, db: Session = Depends(get_db)):
    campaign = Campaign(**payload.model_dump(mode="json"))
    db.add(campaign)
    db.flush()
    log_activity(
        db,
        actions.CAMPAIGN_CREATED,
        {"campaign_id": campaign.id, "name": campaign.name},
    )
    db.refresh(campaign)
    return campaign


@router.get("/", response_model=list[CampaignRead])
def list_campaigns(db: Session = Depends(get_db)):
    stmt = select(Campaign).order_by(Campaign.created_at.desc(), Campaign.id.desc())
    return list(db.scalars(stmt).all())


@router.get("/{campaign_id}", response_model=CampaignRead)
def get_campaign(campaign_id: int, db: Session = Depends(get_db)):
    campaign = db.get(Campaign, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


def _get_campaign(campaign_id: int, db: Session) -> Campaign:
    campaign = db.get(Campaign, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


@router.get("/{campaign_id}/status", response_model=CampaignStatusRead)
def get_campaign_status(campaign_id: int, db: Session = Depends(get_db)):
    return campaign_status(db, _get_campaign(campaign_id, db))


@router.post("/{campaign_id}/start", response_model=CampaignStatusRead)
def start_campaign(campaign_id: int, db: Session = Depends(get_db)):
    campaign = _get_campaign(campaign_id, db)
    if campaign.status not in {"DRAFT", "PAUSED", "ERROR"}:
        raise HTTPException(status_code=409, detail="Campaign cannot be started from its current state")
    campaign.status = "RUNNING"
    db.add(campaign)
    db.commit()
    log_activity(db, actions.CAMPAIGN_STARTED, {"campaign_id": campaign.id})
    CampaignOrchestrator().process_campaign(db, campaign)
    return campaign_status(db, campaign)


@router.post("/{campaign_id}/pause", response_model=CampaignStatusRead)
def pause_campaign(campaign_id: int, db: Session = Depends(get_db)):
    campaign = _get_campaign(campaign_id, db)
    if campaign.status != "RUNNING":
        raise HTTPException(status_code=409, detail="Only running campaigns can be paused")
    campaign.status = "PAUSED"
    db.add(campaign)
    db.commit()
    log_activity(db, actions.CAMPAIGN_PAUSED, {"campaign_id": campaign.id})
    return campaign_status(db, campaign)


@router.post("/{campaign_id}/resume", response_model=CampaignStatusRead)
def resume_campaign(campaign_id: int, db: Session = Depends(get_db)):
    campaign = _get_campaign(campaign_id, db)
    if campaign.status != "PAUSED":
        raise HTTPException(status_code=409, detail="Only paused campaigns can be resumed")
    campaign.status = "RUNNING"
    db.add(campaign)
    db.commit()
    log_activity(db, actions.CAMPAIGN_RESUMED, {"campaign_id": campaign.id})
    CampaignOrchestrator().process_campaign(db, campaign)
    return campaign_status(db, campaign)


@router.post("/{campaign_id}/stop", response_model=CampaignStatusRead)
def stop_campaign(campaign_id: int, db: Session = Depends(get_db)):
    campaign = _get_campaign(campaign_id, db)
    if campaign.status in {"STOPPED", "COMPLETED"}:
        raise HTTPException(status_code=409, detail="Campaign is already terminal")
    campaign.status = "STOPPED"
    db.add(campaign)
    db.commit()
    log_activity(db, actions.CAMPAIGN_STOPPED, {"campaign_id": campaign.id})
    return campaign_status(db, campaign)


@router.post("/{campaign_id}/retry-failed", response_model=CampaignStatusRead)
def retry_failed_campaign(campaign_id: int, db: Session = Depends(get_db)):
    campaign = _get_campaign(campaign_id, db)
    emails = db.scalars(
        select(EmailRecord).where(
            EmailRecord.campaign_id == campaign.id,
            EmailRecord.status == AgentState.ERROR.value,
        )
    ).all()
    for email in emails:
        workflow = db.scalars(
            select(Workflow).where(Workflow.workflow_type == "OUTREACH")
        ).all()
        workflow = next(
            (item for item in workflow if (item.context or {}).get("email_id") == email.id),
            None,
        )
        if workflow and workflow.current_state == AgentState.ERROR.value:
            transition_workflow(db, workflow.id, AgentState.RECEIVED)
            email.status = "DRAFT"
            db.add(email)
    campaign.status = "RUNNING"
    db.add(campaign)
    db.commit()
    log_activity(db, actions.CAMPAIGN_STARTED, {"campaign_id": campaign.id, "retry_failed": True})
    return campaign_status(db, campaign)
