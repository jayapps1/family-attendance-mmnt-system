from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint, Date, DateTime, Enum as SAEnum, ForeignKey,
    Index, Integer, Numeric, String, Text, func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


class ContributionPeriodStatus(enum.Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"


class ContributionPeriod(Base):
    """Period-specific amount, independent of subsequent category default changes."""

    __tablename__ = "contribution_periods"
    __table_args__ = (
        CheckConstraint("amount_per_member >= 0 AND amount_per_member <> 'NaN'::numeric", name="ck_contribution_periods_amount"),
        CheckConstraint("due_date >= start_date", name="ck_contribution_periods_dates"),
        Index("ix_contribution_periods_type_status", "contribution_type_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contribution_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contribution_types.id", name="fk_contribution_periods_contribution_type_id", ondelete="RESTRICT"),
        nullable=False, index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    year: Mapped[int | None] = mapped_column(Integer)
    amount_per_member: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    start_date: Mapped[date | None] = mapped_column(Date)
    due_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[ContributionPeriodStatus] = mapped_column(
        SAEnum(ContributionPeriodStatus, name="contribution_period_status_enum", validate_strings=True),
        nullable=False, default=ContributionPeriodStatus.DRAFT,
        server_default=ContributionPeriodStatus.DRAFT.value,
    )
    description: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", name="fk_contribution_periods_created_by", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    contribution_type = relationship("ContributionType", back_populates="periods")
    creator = relationship("User", foreign_keys=[created_by])
    member_contributions = relationship(
        "MemberContribution", back_populates="contribution_period", passive_deletes="all"
    )
