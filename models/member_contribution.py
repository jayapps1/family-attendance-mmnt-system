from __future__ import annotations

import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint, DateTime, Enum as SAEnum, ForeignKey,
    Index, Numeric, UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


class ContributionStatus(enum.Enum):
    UNPAID = "UNPAID"
    PARTIALLY_PAID = "PARTIALLY_PAID"
    PAID = "PAID"


class MemberContribution(Base):
    """Member obligation; status is a cache to be synchronized by the service."""

    __tablename__ = "member_contributions"
    __table_args__ = (
        UniqueConstraint("contribution_period_id", "family_member_id", name="uq_member_contributions_period_member"),
        CheckConstraint("amount_due >= 0 AND amount_due <> 'NaN'::numeric", name="ck_member_contributions_amount"),
        Index("ix_member_contributions_period_status", "contribution_period_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contribution_period_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contribution_periods.id", name="fk_member_contributions_contribution_period_id", ondelete="RESTRICT"),
        nullable=False, index=True,
    )
    family_member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("family_members.id", name="fk_member_contributions_family_member_id", ondelete="RESTRICT"),
        nullable=False, index=True,
    )
    amount_due: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[ContributionStatus] = mapped_column(
        SAEnum(ContributionStatus, name="contribution_status_enum", validate_strings=True),
        nullable=False, default=ContributionStatus.UNPAID,
        server_default=ContributionStatus.UNPAID.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    contribution_period = relationship("ContributionPeriod", back_populates="member_contributions")
    family_member = relationship("FamilyMember", foreign_keys=[family_member_id])
    payments = relationship(
        "ContributionPayment", back_populates="member_contribution", passive_deletes="all"
    )
