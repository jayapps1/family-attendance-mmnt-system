from datetime import date, datetime
import uuid
from sqlalchemy import Date, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from models.base import Base
from models.media_base import IdentityTimestamps


class GalleryItem(IdentityTimestamps, Base):
    __tablename__ = "gallery_items"
    album_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("gallery_albums.id", name="fk_gallery_items_album", ondelete="RESTRICT"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    file_path: Mapped[str] = mapped_column(String(500))
    event_date: Mapped[date | None] = mapped_column(Date)
    location: Mapped[str | None] = mapped_column(String(255))
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", name="fk_gallery_items_uploader", ondelete="SET NULL"))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    album = relationship("GalleryAlbum", back_populates="items")
    uploader = relationship("User")
