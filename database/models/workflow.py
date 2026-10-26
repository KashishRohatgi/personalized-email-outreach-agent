from typing import Optional

from sqlalchemy import Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base
from database.models.mixin import TimestampMixin


class Workflow(TimestampMixin, Base):
    __tablename__ = "workflows"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    workflow_type: Mapped[str] = mapped_column(String(128), nullable=False)
    current_state: Mapped[str] = mapped_column(String(64), nullable=False, default="RECEIVED")
    context: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)