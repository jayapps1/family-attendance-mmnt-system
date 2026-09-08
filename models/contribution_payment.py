from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean, CheckConstraint, Date, DateTime, Enum as SAEnum, ForeignKey,
    Index, Numeric, String, Text, UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


class PaymentMethod(enum.Enum):
    CASH = "CASH"
    MOBILE_MONEY = "MOBILE_MONEY"
    BANK_TRANSFER = "BANK_TRANSFER"
    CHEQUE = "CHEQUE"
    OTHER = "OTHER"


class ContributionPayment(Base):
    """One installment, retained when reversed; payment methods are record-only."""

    __tablename__ = "contribution_payments"
    __table_args__ = (
        CheckConstraint("amount_paid > 0 AND amount_paid <> 'NaN'::numeric", name="ck_contribution_payments_amount"),
        UniqueConstraint("receipt_number", name="uq_contribution_payments_receipt"),
        CheckConstraint(
            "(is_reversed = false AND reversed_at IS NULL AND reversed_by IS NULL AND reversal_reason IS NULL) OR "
            "(is_reversed = true AND reversed_at IS NOT NULL AND reversed_by IS NOT NULL "
            "AND reversal_reason IS NOT NULL AND length(trim(reversal_reason)) > 0)",
            name="ck_contribution_payments_reversal",
        ),
        Index("ix_contribution_payments_obligation_reversed", "member_contribution_id", "is_reversed"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    member_contribution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("member_contributions.id", name="fk_contribution_payments_member_contribution_id", ondelete="RESTRICT"),
        nullable=False, index=True,
    )
    amount_paid: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    payment_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    payment_method: Mapped[PaymentMethod] = mapped_column(
        SAEnum(PaymentMethod, name="contribution_payment_method_enum", validate_strings=True),
        nullable=False,
    )
    reference: Mapped[str | None] = mapped_column(String(150))
    receipt_number: Mapped[str | None] = mapped_column(String(80))
    remarks: Mapped[str | None] = mapped_column(Text)
    received_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", name="fk_contribution_payments_received_by", ondelete="RESTRICT"),
        nullable=True, index=True,
    )
    recorded_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", name="fk_contribution_payments_recorded_by", ondelete="RESTRICT"),
        nullable=True, index=True,
    )
    is_reversed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    reversed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reversed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", name="fk_contribution_payments_reversed_by", ondelete="RESTRICT"),
        nullable=True, index=True,
    )
    reversal_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    member_contribution = relationship("MemberContribution", back_populates="payments")
    receiver = relationship("User", foreign_keys=[received_by])
    recorder = relationship("User", foreign_keys=[recorded_by])
    reverser = relationship("User", foreign_keys=[reversed_by])
