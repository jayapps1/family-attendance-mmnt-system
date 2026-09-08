import uuid
from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from models.base import Base
from models.media_base import IdentityTimestamps


class ApplicationSetting(IdentityTimestamps, Base):
    __tablename__ = "application_settings"
    __table_args__ = (UniqueConstraint("setting_key", name="uq_application_settings_key"),)
    setting_key: Mapped[str] = mapped_column(String(100))
    setting_value: Mapped[str] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", name="fk_application_settings_updater", ondelete="SET NULL"))
    updater = relationship("User")
