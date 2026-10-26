from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from agent.logging import actions
from agent.models.states import AgentState
from agent.services.activity_service import log_activity
from agent.services.workflow_service import create_workflow
from agent.validators import SearchJobCreate, SearchJobRead
from database.models import SearchJob
from database.session import get_db

router = APIRouter(prefix="/search", tags=["search"])


@router.post("/", response_model=SearchJobRead, status_code=201)
def create_search_job(payload: SearchJobCreate, db: Session = Depends(get_db)):
    job = SearchJob(
        classification=payload.classification,
        search_query=payload.search_query,
        source_urls=[str(url) for url in payload.source_urls],
        status=AgentState.RECEIVED.value,
        profiles_found=0,
        profiles_relevant=0,
    )
    db.add(job)
    db.flush()
    create_workflow(
        db,
        workflow_type="SEARCH",
        context={"search_job_id": job.id, "classification": job.classification},
        initial_state=AgentState.RECEIVED,
    )
    log_activity(
        db,
        actions.SEARCH_STARTED,
        {
            "search_job_id": job.id,
            "classification": job.classification,
            "search_query": job.search_query,
        },
    )
    db.refresh(job)
    return job


@router.get("/", response_model=list[SearchJobRead])
def list_search_jobs(
    classification: str | None = None,
    db: Session = Depends(get_db),
):
    stmt = select(SearchJob).order_by(SearchJob.created_at.desc(), SearchJob.id.desc())
    if classification:
        stmt = stmt.where(SearchJob.classification == classification)
    return list(db.scalars(stmt).all())


@router.get("/{job_id}", response_model=SearchJobRead)
def get_search_job(job_id: int, db: Session = Depends(get_db)):
    job = db.get(SearchJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Search job not found")
    return job