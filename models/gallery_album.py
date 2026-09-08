from datetime import date
import uuid
from sqlalchemy import Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from models.base import Base
from models.media_base import IdentityTimestamps


class GalleryAlbum(IdentityTimestamps, Base):
    __tablename__ = "gallery_albums"
    title: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    event_date: Mapped[date | None] = mapped_column(Date)
    location: Mapped[str | None] = mapped_column(String(255))
    cover_image_path: Mapped[str | None] = mapped_column(String(500))
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", name="fk_gallery_albums_creator", ondelete="SET NULL"), index=True)
    creator = relationship("User")
    items = relationship("GalleryItem", back_populates="album", passive_deletes="all")
