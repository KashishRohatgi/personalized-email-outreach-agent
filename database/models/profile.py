from typing import Optional

from sqlalchemy import Float, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base
from database.models.mixin import TimestampMixin


class Profile(TimestampMixin, Base):
    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    profile_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    role: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    company: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    classification: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    relevance_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    professional_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    relevant_points: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    research_status: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    contacts: Mapped[list["Contact"]] = relationship(back_populates="profile")  # noqa: F821