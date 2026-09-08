"""Explicit operator-run bootstrap; never called automatically at application startup."""
import re
from sqlalchemy.exc import IntegrityError
from models import User, UserRole
from repositories.user_repository import UserRepository
from services.audit_service import append_audit
from utils.validators import ValidationError, required


class SeedService:
    def __init__(self, sessions):
        self.sessions = sessions

    def super_admin(self, email: str, phone_number: str, username: str | None = None) -> dict:
        """Create the first administrator idempotently without issuing login credentials."""
        email = required(email, "Email", 255).lower()
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
            raise ValidationError("Enter a valid email address")
        phone_number = required(phone_number, "Phone number", 30)
        if not re.fullmatch(r"\+?[0-9]{7,15}", phone_number):
            raise ValidationError("Phone number must contain 7 to 15 digits and an optional leading +")
        username = required(username or email.split("@", 1)[0], "Username", 100).lower()
        if "@" in username or any(character.isspace() for character in username):
            raise ValidationError("Username cannot contain spaces or @")
        try:
            with self.sessions() as session, session.begin():
                repo = UserRepository(session)
                repo.lock_domain("administrator_setup")
                row = repo.find_identifier(email, lock=True)
                created = row is None
                if row is not None:
                    if (row.email or "").lower() != email or row.role is not UserRole.SUPER_ADMIN:
                        raise ValidationError("Email belongs to a different account; use administrator management")
                    changed = row.phone_number != phone_number
                    row.phone_number = phone_number
                else:
                    if repo.list():
                        raise ValidationError("Initial seeding requires an empty user table; use administrator management")
                    row = repo.add(User(username=username, email=email, phone_number=phone_number,
                                        role=UserRole.SUPER_ADMIN, is_active=True, totp_enabled=False))
                    changed = True
                if changed:
                    append_audit(session, None, "SEED_SUPER_ADMIN", "users", row.id,
                                 "Created initial administrator" if created else "Updated administrator contact phone")
                session.flush()
                return {"id": str(row.id), "username": row.username, "email": row.email,
                        "phone_number": row.phone_number, "created": created,
                        "enrollment_required": not row.totp_enabled}
        except IntegrityError as exc:
            raise ValidationError("Seed conflicts with an existing administrator") from exc
