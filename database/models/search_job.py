import datetime
from typing import Optional

from sqlalchemy import Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base
from database.models.mixin import TimestampMixin


class SearchJob(TimestampMixin, Base):
    __tablename__ = "search_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    classification: Mapped[str] = mapped_column(String(255), nullable=False)
    search_query: Mapped[str] = mapped_column(Text, nullable=False)
    source_urls: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="RECEIVED")
    profiles_found: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    profiles_relevant: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        "completed_at", nullable=True
    )