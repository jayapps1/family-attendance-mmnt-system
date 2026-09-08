"""Union-specific ordering metadata; parent links remain authoritative."""
import uuid
from datetime import datetime
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from models.base import Base


class MarriageChild(Base):
    __tablename__ = 'marriage_children'
    __table_args__ = (
        UniqueConstraint('marriage_id', 'child_id', name='uq_marriage_children_child'),
        UniqueConstraint('marriage_id', 'birth_order', name='uq_marriage_children_order'),
        CheckConstraint('birth_order > 0', name='ck_marriage_children_positive'),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    marriage_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('marriages.id', ondelete='CASCADE'), index=True)
    child_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('family_members.id', ondelete='RESTRICT'), index=True)
    birth_order: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
