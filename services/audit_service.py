import platform
from models import AuditLog
from repositories.base import Repository
from services.base import Service, snapshot


def append_audit(session, user_id, action, entity_type, entity_id=None, description=None, details=None):
    return Repository(session, AuditLog).add(AuditLog(
        user_id=user_id, action=action, entity_type=entity_type, entity_id=entity_id,
        description=description, details=details, computer_name=platform.node()))


class AuditService(Service):
    def history(self, action=None, limit=500):
        with self.transaction() as session:
            criteria = [AuditLog.action == action] if action else []
            rows = Repository(session, AuditLog).list(*criteria)
            rows.sort(key=lambda row: row.created_at, reverse=True)
            return [snapshot(row) for row in rows[:limit]]
