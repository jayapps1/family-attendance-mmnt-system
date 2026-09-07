from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, DateTime, Enum as SAEnum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base

if TYPE_CHECKING:
    from models.family_member import FamilyMember
    from models.login_history import LoginHistory
    from models.recovery_code import RecoveryCode


class UserRole(enum.Enum):
    SUPER_ADMIN = "SUPER_ADMIN"
    ADMIN = "ADMIN"


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "failed_login_attempts >= 0",
            name="ck_users_failed_login_attempts_non_negative",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    family_member_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("family_members.id", ondelete="SET NULL"),
        unique=True,
        index=True,
    )

    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, index=True)

    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, name="user_role_type", native_enum=True),
        nullable=False,
        default=UserRole.ADMIN,
        server_default=UserRole.ADMIN.value,
        index=True,
    )

    totp_secret_encrypted: Mapped[str | None] = mapped_column(Text)
    totp_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    authenticator_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true", index=True
    )
    failed_login_attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    family_member: Mapped["FamilyMember | None"] = relationship(
        "FamilyMember", back_populates="user_account"
    )
    recovery_codes: Mapped[list["RecoveryCode"]] = relationship(
        "RecoveryCode",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    login_history: Mapped[list["LoginHistory"]] = relationship(
        "LoginHistory",
        back_populates="user",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<User {self.username} ({self.role.value})>"
