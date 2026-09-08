from __future__ import annotations

import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean, CheckConstraint, DateTime, Enum as SAEnum, ForeignKey,
    Numeric, String, Text, UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


class ContributionFrequency(enum.Enum):
    ANNUAL = "ANNUAL"
    ONE_TIME = "ONE_TIME"
    MONTHLY = "MONTHLY"
    OTHER = "OTHER"


class ContributionType(Base):
    """Configurable contribution category; amounts are never fixed in code."""

    __tablename__ = "contribution_types"
    __table_args__ = (
        UniqueConstraint("name", name="uq_contribution_types_name"),
        CheckConstraint("default_amount >= 0 AND default_amount <> 'NaN'::numeric", name="ck_contribution_types_amount"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    default_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    frequency: Mapped[ContributionFrequency] = mapped_column(
        SAEnum(ContributionFrequency, name="contribution_frequency_enum", validate_strings=True),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true", index=True
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", name="fk_contribution_types_created_by", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    creator = relationship("User", foreign_keys=[created_by])
    periods = relationship("ContributionPeriod", back_populates="contribution_type", passive_deletes="all")
