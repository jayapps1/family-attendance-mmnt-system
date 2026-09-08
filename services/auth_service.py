from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import platform
import secrets
import time
import uuid
import pyotp
from sqlalchemy.exc import IntegrityError
from models import User, UserRole, RecoveryCode, LoginHistory
from repositories.user_repository import UserRepository
from repositories.base import Repository
from services.audit_service import append_audit
from utils.security import recovery_codes, recovery_hash, matches_recovery
from utils.validators import required, ValidationError


@dataclass
class AuthSession:
    user_id: uuid.UUID
    username: str
    role: str
    login_id: uuid.UUID
    last_activity: float = field(default_factory=time.monotonic)

    def expired(self, minutes: int) -> bool:
        return time.monotonic() - self.last_activity >= minutes * 60

    def touch(self):
        self.last_activity = time.monotonic()


@dataclass
class SetupTicket:
    token: str
    user_id: uuid.UUID
    username: str
    secret: str = field(repr=False)

    @property
    def uri(self):
        return pyotp.TOTP(self.secret).provisioning_uri(self.username, issuer_name="Family Management")


class AuthService:
    def __init__(self, sessions, box_provider, now=None):
        self.sessions, self.box_provider = sessions, box_provider
        self.now = now or (lambda: datetime.now(timezone.utc))
        self.pending = {}

    def needs_bootstrap(self):
        with self.sessions() as session:
            users = UserRepository(session).list()
            return not users or (len(users) == 1 and users[0].authenticator_verified_at is None and not users[0].totp_enabled)

    def bootstrap_profile(self) -> dict:
        """Return only contact fields for a resumable initial enrollment."""
        with self.sessions() as session:
            users = UserRepository(session).list()
            if len(users) == 1 and users[0].authenticator_verified_at is None and not users[0].totp_enabled:
                return {"username": users[0].username, "email": users[0].email}
            return {}

    def prepare_setup(self, username, email=None, *, actor_id=None, role="ADMIN", reset_id=None):
        username = required(username, "Username", 100).lower()
        email = (email or "").strip().lower() or None
        if email and ("@" not in email or len(email) > 255):
            raise ValidationError("Enter a valid email address")
        if "@" in username or any(ch.isspace() for ch in username):
            raise ValidationError("Username cannot contain spaces or @")
        try:
            with self.sessions() as session, session.begin():
                repo = UserRepository(session)
                repo.lock_domain("administrator_setup")
                users = repo.list()
                bootstrap = not users or (len(users) == 1 and users[0].authenticator_verified_at is None and not users[0].totp_enabled)
                if not bootstrap:
                    if actor_id is None:
                        raise PermissionError("An administrator must create accounts")
                    actor = repo.get(actor_id, lock=True)
                    if not actor.is_active or not actor.totp_enabled:
                        raise PermissionError("Administrator account is inactive")
                    if (role == "SUPER_ADMIN" or reset_id) and actor.role is not UserRole.SUPER_ADMIN:
                        raise PermissionError("Super administrator access required")
                kind = UserRole.SUPER_ADMIN if bootstrap else UserRole(role)
                if reset_id:
                    row = repo.get(reset_id, lock=True)
                    if row.id == actor_id:
                        raise ValidationError("Use a second super administrator to reset this account")
                    username = row.username
                elif bootstrap and users:
                    if len(users) != 1:
                        raise ValidationError("Administrator setup requires operator review")
                    row = users[0]
                    username = row.username
                else:
                    if repo.find_identifier(username) or email and repo.find_identifier(email):
                        raise ValidationError("Username or email already exists")
                    row = repo.add(User(username=username, email=email, role=kind))
                secret = pyotp.random_base32()
                row.totp_secret_encrypted = self.box_provider(bootstrap).encrypt(secret)
                row.totp_enabled, row.last_totp_step = False, None
                row.failed_login_attempts, row.locked_until = 0, None
                for code in repo.recovery_codes(row.id):
                    code.is_used, code.used_at = True, self.now()
                append_audit(session, actor_id, "UPDATE_ADMIN" if reset_id else "CREATE_ADMIN", "users", row.id)
                ticket = SetupTicket(secrets.token_urlsafe(32), row.id, username, secret)
            self.pending[ticket.token] = (ticket, time.monotonic() + 600, 0)
            return ticket
        except IntegrityError as exc:
            raise ValidationError("Username or email already exists") from exc

    def confirm_setup(self, token, code):
        pending = self.pending.get(token)
        if not pending or time.monotonic() > pending[1] or pending[2] >= 5:
            self.pending.pop(token, None)
            raise ValidationError("Setup expired; restart administrator setup")
        ticket, expiry, failures = pending
        self.pending[token] = (ticket, expiry, failures + 1)
        now = self.now()
        step = self._matching_step(ticket.secret, code, now)
        if step is None:
            raise ValidationError("Invalid authenticator code")
        codes = recovery_codes()
        with self.sessions() as session, session.begin():
            repo = UserRepository(session)
            row = repo.get(ticket.user_id, lock=True)
            if self.box_provider(False).decrypt(row.totp_secret_encrypted) != ticket.secret:
                raise ValidationError("Setup was superseded")
            row.totp_enabled, row.authenticator_verified_at, row.last_totp_step = True, now, step
            for plain in codes:
                Repository(session, RecoveryCode).add(RecoveryCode(user_id=row.id, code_hash=recovery_hash(plain)))
            append_audit(session, row.id, "AUTHENTICATOR_SETUP", "users", row.id)
        self.pending.pop(token, None)
        return codes

    @staticmethod
    def _matching_step(secret, code, now):
        if len(code) != 6 or not code.isdigit():
            return None
        totp = pyotp.TOTP(secret)
        step = int(now.timestamp()) // totp.interval
        for candidate in (step, step - 1, step + 1):
            if secrets.compare_digest(totp.at(candidate * totp.interval), code):
                return candidate
        return None

    def login(self, identifier, code, *, recovery=False):
        identifier = required(identifier, "Username or email", 255)
        now, authenticated = self.now(), None
        with self.sessions() as session, session.begin():
            repo = UserRepository(session)
            user = repo.find_identifier(identifier, lock=True)
            reason = "Invalid credentials"
            permitted = user and user.is_active and user.totp_enabled
            if permitted and user.locked_until and user.locked_until > now:
                permitted, reason = False, "Temporarily locked"
            valid = False
            if permitted:
                if recovery:
                    for stored in repo.recovery_codes(user.id):
                        if matches_recovery(code, stored.code_hash):
                            stored.is_used, stored.used_at, valid = True, now, True
                            break
                else:
                    secret = self.box_provider(False).decrypt(user.totp_secret_encrypted)
                    step = self._matching_step(secret, code, now)
                    valid = step is not None and (user.last_totp_step is None or step > user.last_totp_step)
                    if valid:
                        user.last_totp_step = step
            if valid:
                user.failed_login_attempts, user.locked_until, user.last_login_at = 0, None, now
            elif user and permitted:
                user.failed_login_attempts += 1
                if user.failed_login_attempts >= 5:
                    user.locked_until = now + timedelta(minutes=15)
                    user.failed_login_attempts = 0
            history = Repository(session, LoginHistory).add(LoginHistory(
                user_id=user.id if user else None, attempted_identifier=identifier, success=valid,
                failure_reason=None if valid else reason, computer_name=platform.node(), login_at=now))
            append_audit(session, user.id if user else None, "LOGIN" if valid else "FAILED_LOGIN",
                         "login_history", history.id)
            if valid:
                authenticated = AuthSession(user.id, user.username, user.role.value, history.id)
        # Raise only after failed-attempt counters and history commit.
        if authenticated is None:
            raise ValidationError("Sign-in failed. Check your code or wait if the account is locked.")
        return authenticated

    def logout(self, auth_session):
        with self.sessions() as session, session.begin():
            row = Repository(session, LoginHistory).get(auth_session.login_id, lock=True)
            if row.logout_at is None:
                row.logout_at = self.now()
                append_audit(session, auth_session.user_id, "LOGOUT", "login_history", row.id)
