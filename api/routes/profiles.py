from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from agent.logging import actions
from agent.services.activity_service import log_activity
from agent.validators import ProfileCreate, ProfileRead
from database.models import Profile
from database.session import get_db

router = APIRouter(prefix="/profiles", tags=["profiles"])


@router.post("/", response_model=ProfileRead, status_code=201)
def create_profile(payload: ProfileCreate, db: Session = Depends(get_db)):
    profile = Profile(**payload.model_dump(mode="json"))
    db.add(profile)
    db.flush()
    log_activity(
        db,
        actions.PROFILE_CREATED,
        {"profile_id": profile.id, "name": profile.name},
    )
    db.refresh(profile)
    return profile


@router.get("/", response_model=list[ProfileRead])
def list_profiles(
    classification: str | None = None,
    research_status: str | None = None,
    db: Session = Depends(get_db),
):
    stmt = select(Profile).order_by(Profile.created_at.desc(), Profile.id.desc())
    if classification:
        stmt = stmt.where(Profile.classification == classification)
    if research_status:
        stmt = stmt.where(Profile.research_status == research_status)
    return list(db.scalars(stmt).all())


@router.get("/{profile_id}", response_model=ProfileRead)
def get_profile(profile_id: int, db: Session = Depends(get_db)):
    profile = db.get(Profile, profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile