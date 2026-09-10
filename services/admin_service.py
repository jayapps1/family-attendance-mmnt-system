from models import UserRole
from repositories.user_repository import UserRepository
from services.base import Service
from utils.validators import ValidationError


class AdminService(Service):
    def list(self):
        with self.transaction() as session:
            return [{"id": row.id, "username": row.username, "email": row.email, "phone_number": row.phone_number,
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

    def update_profile(self,identity,username,email=None,phone_number=None):
        from utils.validators import required
        username=required(username,'Username',100).lower()
        email=(email or '').strip().lower() or None
        phone_number=(phone_number or '').strip() or None
        if '@' in username or any(c.isspace() for c in username):
            raise ValidationError('Username cannot contain spaces or @')
        if email and ('@' not in email or len(email)>255): raise ValidationError('Enter a valid email address')
        if phone_number and len(phone_number)>30: raise ValidationError('Phone number is too long')
        with self.transaction(super_admin=True) as session:
            repo=UserRepository(session); repo.lock_domain('administrator_setup')
            row=repo.get(identity,lock=True)
            for identifier in (username,email):
                existing=repo.find_identifier(identifier) if identifier else None
                if existing and existing.id != identity: raise ValidationError('Username or email already exists')
            row.username,row.email,row.phone_number=username,email,phone_number
            self.audit(session,'UPDATE_ADMIN',row,'Updated administrator contact details')
