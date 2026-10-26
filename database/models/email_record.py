from typing import Optional

from sqlalchemy import ForeignKey, Float, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base
from database.models.mixin import TimestampMixin


class EmailRecord(TimestampMixin, Base):
    __tablename__ = "email_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    contact_id: Mapped[int] = mapped_column(
        ForeignKey("contacts.id"), nullable=False
    )
    campaign_id: Mapped[int] = mapped_column(
        ForeignKey("campaigns.id"), nullable=False
    )
    recipient: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    body: Mapped[str] = mapped_column(Text, nullable=False)
    personalization_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    warnings: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="DRAFT")

    contact: Mapped["Contact"] = relationship(back_populates="emails")  # noqa: F821
    campaign: Mapped["Campaign"] = relationship(back_populates="emails")  # noqa: F821