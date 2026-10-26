from typing import Optional

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base
from database.models.mixin import TimestampMixin


class Contact(TimestampMixin, Base):
    __tablename__ = "contacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    company: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    context: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    public_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    profile_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("profiles.id"), nullable=True
    )

    profile: Mapped[Optional["Profile"]] = relationship(back_populates="contacts")  # noqa: F821
    emails: Mapped[list["EmailRecord"]] = relationship(back_populates="contact")  # noqa: F821