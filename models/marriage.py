from __future__ import annotations

import enum
import uuid
from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


class MarriageStatus(enum.Enum):
    MARRIED = "MARRIED"
    SEPARATED = "SEPARATED"
    DIVORCED = "DIVORCED"
    WIDOWED = "WIDOWED"


class Marriage(Base):
    __tablename__ = "marriages"

    __table_args__ = (
        CheckConstraint(
            "spouse_one_id <> spouse_two_id",
            name="ck_marriages_different_spouses",
        ),
        Index(
            "ix_marriages_spouses",
            "spouse_one_id",
            "spouse_two_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    spouse_one_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("family_members.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    spouse_two_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("family_members.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    marriage_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    marriage_location: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    status: Mapped[MarriageStatus] = mapped_column(
        SAEnum(
            MarriageStatus,
            name="marriage_status_type",
            native_enum=True,
        ),
        nullable=False,
        default=MarriageStatus.MARRIED,
        server_default=MarriageStatus.MARRIED.value,
        index=True,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    spouse_one = relationship(
        "FamilyMember",
        foreign_keys=[spouse_one_id],
    )

    spouse_two = relationship(
        "FamilyMember",
        foreign_keys=[spouse_two_id],
    )

    def __repr__(self) -> str:
        return (
            f"<Marriage spouse_one_id={self.spouse_one_id} "
            f"spouse_two_id={self.spouse_two_id} "
            f"status={self.status.value}>"
        )
