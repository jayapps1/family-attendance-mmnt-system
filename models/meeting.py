from __future__ import annotations

import enum
import uuid
from datetime import date, datetime, time

from sqlalchemy import (
    Date,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    String,
    Text,
    Time,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


class MeetingStatus(enum.Enum):
    SCHEDULED = "SCHEDULED"
    ONGOING = "ONGOING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class MeetingType(enum.Enum):
    GENERAL = "GENERAL"
    ANNUAL = "ANNUAL"
    EMERGENCY = "EMERGENCY"
    SPECIAL = "SPECIAL"
    OTHER = "OTHER"


class Meeting(Base):
    __tablename__ = "meetings"

    __table_args__ = (
        Index(
            "ix_meetings_date_status",
            "meeting_date",
            "status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    meeting_number: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        unique=True,
        index=True,
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    meeting_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )

    start_time: Mapped[time | None] = mapped_column(
        Time,
        nullable=True,
    )

    end_time: Mapped[time | None] = mapped_column(
        Time,
        nullable=True,
    )

    venue: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    location: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    meeting_type: Mapped[MeetingType] = mapped_column(
        SAEnum(
            MeetingType,
            name="meeting_type_enum",
            native_enum=True,
        ),
        nullable=False,
        default=MeetingType.GENERAL,
        server_default=MeetingType.GENERAL.value,
        index=True,
    )

    status: Mapped[MeetingStatus] = mapped_column(
        SAEnum(
            MeetingStatus,
            name="meeting_status_enum",
            native_enum=True,
        ),
        nullable=False,
        default=MeetingStatus.SCHEDULED,
        server_default=MeetingStatus.SCHEDULED.value,
        index=True,
    )

    chairperson_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "family_members.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    secretary_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "family_members.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    agenda: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
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

    chairperson = relationship(
        "FamilyMember",
        foreign_keys=[chairperson_id],
    )

    secretary = relationship(
        "FamilyMember",
        foreign_keys=[secretary_id],
    )

    creator = relationship(
        "User",
        foreign_keys=[created_by],
    )

    attendance_records = relationship(
        "Attendance",
        back_populates="meeting",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return (
            f"<Meeting meeting_number='{self.meeting_number}' "
            f"title='{self.title}' "
            f"date='{self.meeting_date}'>"
        )
