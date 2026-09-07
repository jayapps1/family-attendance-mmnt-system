from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


class RelationshipType(enum.Enum):
    FATHER = "FATHER"
    MOTHER = "MOTHER"
    GUARDIAN = "GUARDIAN"


class FamilyRelationship(Base):
    __tablename__ = "family_relationships"

    __table_args__ = (
        UniqueConstraint(
            "parent_id",
            "child_id",
            name="uq_family_relationships_parent_child",
        ),
        CheckConstraint(
            "parent_id <> child_id",
            name="ck_family_relationships_not_self_parent",
        ),
        Index(
            "ix_family_relationships_parent_child",
            "parent_id",
            "child_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    parent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("family_members.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    child_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("family_members.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    relationship_type: Mapped[RelationshipType] = mapped_column(
        SAEnum(
            RelationshipType,
            name="family_relationship_type",
            native_enum=True,
        ),
        nullable=False,
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

    parent = relationship(
        "FamilyMember",
        foreign_keys=[parent_id],
    )

    child = relationship(
        "FamilyMember",
        foreign_keys=[child_id],
    )

    def __repr__(self) -> str:
        return (
            f"<FamilyRelationship "
            f"parent_id={self.parent_id} "
            f"child_id={self.child_id} "
            f"type={self.relationship_type.value}>"
        )
