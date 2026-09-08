import enum
import uuid
from sqlalchemy import Enum as SAEnum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from models.base import Base
from models.media_base import IdentityTimestamps


class MediaType(enum.Enum):
    IMAGE = "IMAGE"
    VIDEO = "VIDEO"
    DOCUMENT = "DOCUMENT"
    AUDIO = "AUDIO"


class HistoryMedia(IdentityTimestamps, Base):
    __tablename__ = "history_media"
    family_history_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("family_history.id", name="fk_history_media_history", ondelete="RESTRICT"), index=True)
    media_type: Mapped[MediaType] = mapped_column(
        SAEnum(MediaType, name="history_media_type_enum", validate_strings=True))
    file_path: Mapped[str] = mapped_column(String(500))
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", name="fk_history_media_uploader", ondelete="SET NULL"))
    history = relationship("FamilyHistory", back_populates="media")
    uploader = relationship("User")
