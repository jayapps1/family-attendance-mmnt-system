"""Session-scoped query helpers. Transactions belong to services."""
from typing import TypeVar, Generic
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from models.base import Base

T = TypeVar("T", bound=Base)


class Repository(Generic[T]):
    def __init__(self, session: Session, model: type[T]):
        self.session, self.model = session, model

    def get(self, identity: UUID, *, lock: bool = False) -> T:
        query = select(self.model).where(self.model.id == identity)
        if lock:
            query = query.with_for_update().execution_options(populate_existing=True)
        row = self.session.scalar(query)
        if row is None:
            raise ValueError("Record not found")
        return row

    def list(self, *criteria, limit: int | None = None) -> list[T]:
        query = select(self.model).where(*criteria).order_by(self.model.id)
        if limit is not None:
            query = query.limit(limit)
        return list(self.session.scalars(query))

    def add(self, row: T) -> T:
        self.session.add(row)
        self.session.flush()
        return row

    def lock_domain(self, name: str) -> None:
        # Transaction-scoped lock serializes graph traversal and number allocation.
        self.session.execute(select(func.pg_advisory_xact_lock(func.hashtext(name))))
