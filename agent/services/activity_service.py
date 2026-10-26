from sqlalchemy.orm import Session

from database.models import ActivityLog


def log_activity(db: Session, action: str, details: dict | list | str | None = None) -> ActivityLog:
    entry = ActivityLog(action=action, details=details)
    db.add(entry)
    db.commit()
    return entry