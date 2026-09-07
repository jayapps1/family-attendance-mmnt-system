from __future__ import annotations

import enum
import uuid
from datetime import datetime, time

from sqlalchemy import (
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


class AttendanceStatus(enum.Enum):
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    PERMISSION = "PERMISSION"
    LATE = "LATE"
    EXCUSED = "EXCUSED"


class Attendance(Base):
    __tablename__ = "attendance"

    __table_args__ = (
        UniqueConstraint(
            "meeting_id",
            "family_member_id",
            name="uq_attendance_meeting_member",
        ),
        Index(
            "ix_attendance_meeting_status",
            "meeting_id",
            "status",
        ),
        Index(
            "ix_attendance_member_status",
            "family_member_id",
            "status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    meeting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "meetings.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    family_member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "family_members.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    status: Mapped[AttendanceStatus] = mapped_column(
        SAEnum(
            AttendanceStatus,
            name="attendance_status_enum",
            native_enum=True,
        ),
        nullable=False,
        index=True,
    )

    reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    arrival_time: Mapped[time | None] = mapped_column(
        Time,
        nullable=True,
    )

    remarks: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    recorded_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    recorded_at: Mapped[datetime] = mapped_column(
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

    meeting = relationship(
        "Meeting",
        back_populates="attendance_records",
    )

    family_member = relationship(
        "FamilyMember",
        foreign_keys=[family_member_id],
    )

    recorded_by_user = relationship(
        "User",
        foreign_keys=[recorded_by],
    )

    def __repr__(self) -> str:
        return (
            f"<Attendance meeting_id={self.meeting_id} "
            f"member_id={self.family_member_id} "
            f"status={self.status.value}>"
        )
