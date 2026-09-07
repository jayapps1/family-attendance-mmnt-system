from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base

if TYPE_CHECKING:
    from models.user import User


class LoginHistory(Base):
    __tablename__ = "login_history"
    __table_args__ = (
        CheckConstraint(
            "logout_at IS NULL OR logout_at >= login_at",
            name="ck_login_history_logout_after_login",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
    )

    attempted_identifier: Mapped[str | None] = mapped_column(String(255), index=True)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, index=True)
    failure_reason: Mapped[str | None] = mapped_column(Text)
    computer_name: Mapped[str | None] = mapped_column(String(255))

    login_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    logout_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped["User | None"] = relationship("User", back_populates="login_history")
