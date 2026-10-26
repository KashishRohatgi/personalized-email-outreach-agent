from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from agent.validators import ActivityRead
from database.models import ActivityLog
from database.session import get_db

router = APIRouter(prefix="/activity", tags=["activity"])


@router.get("/", response_model=list[ActivityRead])
def list_activity(
    action: str | None = None,
    limit: int = 200,
    db: Session = Depends(get_db),
):
    stmt = select(ActivityLog).order_by(ActivityLog.timestamp.desc(), ActivityLog.id.desc())
    if action:
        stmt = stmt.where(ActivityLog.action == action)
    return list(db.scalars(stmt.limit(limit)).all())