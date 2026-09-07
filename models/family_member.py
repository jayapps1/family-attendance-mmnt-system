from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, Enum as SAEnum, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base

if TYPE_CHECKING:
    from models.user import User


class Sex(enum.Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"


class MaritalStatus(enum.Enum):
    SINGLE = "SINGLE"
    MARRIED = "MARRIED"
    SEPARATED = "SEPARATED"
    DIVORCED = "DIVORCED"
    WIDOWED = "WIDOWED"


class LivingStatus(enum.Enum):
    LIVING = "LIVING"
    DECEASED = "DECEASED"
    UNKNOWN = "UNKNOWN"


class FamilyMember(Base):
    __tablename__ = "family_members"
    __table_args__ = (
        CheckConstraint(
            "date_of_death IS NULL OR date_of_birth IS NULL OR date_of_death >= date_of_birth",
            name="ck_family_members_death_after_birth",
        ),
        Index("ix_family_members_full_name", "last_name", "first_name", "middle_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    family_number: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    middle_name: Mapped[str | None] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    sex: Mapped[Sex] = mapped_column(
        SAEnum(Sex, name="sex_type", native_enum=True),
        nullable=False,
        index=True,
    )
    date_of_birth: Mapped[date | None] = mapped_column(Date)
    phone_number: Mapped[str | None] = mapped_column(String(30), index=True)
    current_residence: Mapped[str | None] = mapped_column(String(255), index=True)

    marital_status: Mapped[MaritalStatus] = mapped_column(
        SAEnum(MaritalStatus, name="marital_status_type", native_enum=True),
        nullable=False,
        default=MaritalStatus.SINGLE,
        server_default=MaritalStatus.SINGLE.value,
        index=True,
    )
    living_status: Mapped[LivingStatus] = mapped_column(
        SAEnum(LivingStatus, name="living_status_type", native_enum=True),
        nullable=False,
        default=LivingStatus.LIVING,
        server_default=LivingStatus.LIVING.value,
        index=True,
    )

    date_of_death: Mapped[date | None] = mapped_column(Date)
    profile_image_path: Mapped[str | None] = mapped_column(String(500))
    notes: Mapped[str | None] = mapped_column(Text)

    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true", index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    user_account: Mapped["User | None"] = relationship(
        "User", back_populates="family_member", uselist=False
    )

    def __repr__(self) -> str:
        return f"<FamilyMember {self.family_number}: {self.first_name} {self.last_name}>"
