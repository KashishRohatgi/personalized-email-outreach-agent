from sqlalchemy.orm import Session

from agent.services.activity_service import log_activity
from database.models import ActivityLog


class ActivityLogger:
    def __init__(self, db: Session) -> None:
        self._db = db

    def log(self, action: str, details: dict | list | str | None = None) -> ActivityLog:
        return log_activity(self._db, action, details)