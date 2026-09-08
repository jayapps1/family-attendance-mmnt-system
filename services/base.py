"""Services own transaction boundaries and return detached-safe dictionaries."""
from contextlib import contextmanager
from enum import Enum
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from models import User, UserRole
from repositories.base import Repository
from utils.validators import ValidationError


def snapshot(row) -> dict:
    result = {}
    for column in inspect(row).mapper.column_attrs:
        value = getattr(row, column.key)
        result[column.key] = value.value if isinstance(value, Enum) else value
    return result


class Service:
    def __init__(self, sessions, actor_id=None):
        self.sessions, self.actor_id = sessions, actor_id

    @contextmanager
    def transaction(self, *, super_admin=False):
        try:
            with self.sessions() as session:
                with session.begin():
                    if self.actor_id is None:
                        raise PermissionError("Sign in first")
                    actor = Repository(session, User).get(self.actor_id)
                    if not actor.is_active or not actor.totp_enabled:
                        raise PermissionError("Account is not active")
                    if super_admin and actor.role is not UserRole.SUPER_ADMIN:
                        raise PermissionError("Super administrator access required")
                    yield session
        except IntegrityError as exc:
            raise ValidationError("This change conflicts with an existing record or required relationship") from exc

    def audit(self, session, action, row, description=None):
        from services.audit_service import append_audit
        append_audit(session, self.actor_id, action, row.__tablename__, row.id, description)
