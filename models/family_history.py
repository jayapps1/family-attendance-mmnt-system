import uuid
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from models.base import Base
from models.media_base import IdentityTimestamps


class FamilyHistory(IdentityTimestamps, Base):
    __tablename__ = "family_history"
    title: Mapped[str] = mapped_column(String(255), index=True)
    summary: Mapped[str | None] = mapped_column(Text)
    content: Mapped[str] = mapped_column(Text)
    historical_period: Mapped[str | None] = mapped_column(String(150))
    author: Mapped[str | None] = mapped_column(String(255))
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", name="fk_family_history_creator", ondelete="SET NULL"))
    creator = relationship("User")
    media = relationship("HistoryMedia", back_populates="history", passive_deletes="all")
