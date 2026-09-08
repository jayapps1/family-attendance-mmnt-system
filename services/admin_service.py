from models import UserRole
from repositories.user_repository import UserRepository
from services.base import Service
from utils.validators import ValidationError


class AdminService(Service):
    def list(self):
        with self.transaction() as session:
            return [{"id": row.id, "username": row.username, "email": row.email,
                     "role": row.role.value, "is_active": row.is_active,
                     "totp_enabled": row.totp_enabled, "last_login_at": row.last_login_at}
                    for row in UserRepository(session).list()]

    def update(self, identity, *, is_active, role):
        with self.transaction(super_admin=True) as session:
            repo = UserRepository(session)
            repo.lock_domain("administrator_setup")
            row = repo.get(identity, lock=True)
            kind = UserRole(role)
            if row.id == self.actor_id and (not is_active or kind is not UserRole.SUPER_ADMIN):
                raise ValidationError("You cannot deactivate or demote your own super administrator account")
            if row.role is UserRole.SUPER_ADMIN and (not is_active or kind is not UserRole.SUPER_ADMIN):
                others = [u for u in repo.list() if u.id != row.id and u.is_active
                          and u.totp_enabled and u.role is UserRole.SUPER_ADMIN]
                if not others:
                    raise ValidationError("Keep at least one active super administrator")
            row.is_active, row.role = bool(is_active), kind
            self.audit(session, "UPDATE_ADMIN", row)
