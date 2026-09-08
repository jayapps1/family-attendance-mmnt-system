from datetime import datetime, timedelta, timezone
import uuid
import pyotp
import pytest
from cryptography.fernet import Fernet
from models import User, LoginHistory, RecoveryCode
from repositories.base import Repository
from services.auth_service import AuthService
from tests.service_helpers import service_context
from utils.security import SecretBox


def configured_auth(db):
    factory, actor = service_context(db)
    box = SecretBox(Fernet.generate_key())
    clock = [datetime(2026, 9, 8, 12, 0, tzinfo=timezone.utc)]
    auth = AuthService(factory, lambda create=False: box, now=lambda: clock[0])
    ticket = auth.prepare_setup("auth_" + uuid.uuid4().hex, actor_id=actor)
    codes = auth.confirm_setup(ticket.token, pyotp.TOTP(ticket.secret).at(clock[0]))
    return auth, ticket, codes, clock, actor


def test_totp_encrypted_replay_and_recovery(db):
    auth, ticket, codes, clock, _ = configured_auth(db)
    user = Repository(db, User).get(ticket.user_id)
    assert ticket.secret not in user.totp_secret_encrypted
    clock[0] += timedelta(seconds=30)
    code = pyotp.TOTP(ticket.secret).at(clock[0])
    login = auth.login(ticket.username, code)
    assert login.user_id == ticket.user_id
    with pytest.raises(ValueError):
        auth.login(ticket.username, code)
    recovery_login = auth.login(ticket.username, codes[0], recovery=True)
    with pytest.raises(ValueError):
        auth.login(ticket.username, codes[0], recovery=True)
    auth.logout(recovery_login)
    db.expire_all()
    history = Repository(db, LoginHistory).get(recovery_login.login_id)
    assert history.logout_at is not None
    stored = Repository(db, RecoveryCode).list(RecoveryCode.user_id == ticket.user_id)
    assert all(row.code_hash not in codes for row in stored)
    assert sum(row.is_used for row in stored) == 1


def test_lockout_failures_persist_and_duplicate_admin(db):
    auth, ticket, _, clock, actor = configured_auth(db)
    with pytest.raises(ValueError):
        auth.prepare_setup(ticket.username, actor_id=actor)
    for _ in range(5):
        with pytest.raises(ValueError):
            auth.login(ticket.username, "bad")
    db.expire_all()
    user = Repository(db, User).get(ticket.user_id)
    assert user.locked_until == clock[0] + timedelta(minutes=15)
    clock[0] += timedelta(seconds=30)
    with pytest.raises(ValueError):
        auth.login(ticket.username, pyotp.TOTP(ticket.secret).at(clock[0]))
    clock[0] += timedelta(minutes=16)
    assert auth.login(ticket.username, pyotp.TOTP(ticket.secret).at(clock[0])).user_id == user.id


def test_public_registration_denied(db):
    auth, _, _, _, _ = configured_auth(db)
    with pytest.raises(PermissionError):
        auth.prepare_setup("unauthorized")


def test_inactive_account_cannot_sign_in(db):
    auth, ticket, codes, _, _ = configured_auth(db)
    row = Repository(db, User).get(ticket.user_id)
    row.is_active = False
    db.flush()
    with pytest.raises(ValueError):
        auth.login(ticket.username, codes[0], recovery=True)
