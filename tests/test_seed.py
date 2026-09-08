"""Seeder tests run in a disposable schema, never against real administrator rows."""
import os
import uuid
from datetime import datetime, timedelta, timezone
import pytest
import pyotp
from alembic import command
from alembic.config import Config
from cryptography.fernet import Fernet
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.schema import CreateSchema, DropSchema
from models import User, UserRole, RecoveryCode, AuditLog
from services.seed_service import SeedService
from services.auth_service import AuthService
from utils.security import SecretBox


@pytest.fixture(scope="module")
def seed_engine():
    if os.getenv("FAMILY_RUN_DB_TESTS") != "1":
        pytest.skip("Set FAMILY_RUN_DB_TESTS=1 for isolated PostgreSQL seed tests")
    import config.database as database
    name = "family_seed_test_" + uuid.uuid4().hex
    with database.engine.begin() as connection:
        connection.execute(CreateSchema(name))
    url = database.DATABASE_URL.update_query_dict({"options": "-csearch_path=" + name})
    isolated = create_engine(url)
    try:
        with pytest.MonkeyPatch.context() as patch:
            patch.setattr(database, "DATABASE_URL", url)
            command.upgrade(Config("alembic.ini"), "head")
        yield isolated
    finally:
        isolated.dispose()
        with database.engine.begin() as connection:
            connection.execute(DropSchema(name, cascade=True))


@pytest.fixture
def sessions(seed_engine):
    with seed_engine.connect() as connection:
        transaction = connection.begin()
        try:
            yield sessionmaker(bind=connection, join_transaction_mode="create_savepoint")
        finally:
            transaction.rollback()


def test_seed_is_idempotent_and_requires_enrollment(sessions):
    seeder = SeedService(sessions)
    first = seeder.super_admin("owner@example.com", "0540000000")
    second = seeder.super_admin("owner@example.com", "0540000000")
    assert first["id"] == second["id"]
    assert first["created"] and not second["created"]
    assert first["username"] == "owner"
    assert first["enrollment_required"]
    with sessions() as session:
        users = list(session.scalars(select(User)))
        assert len(users) == 1
        assert users[0].role is UserRole.SUPER_ADMIN
        assert users[0].phone_number == "0540000000"
        assert users[0].totp_secret_encrypted is None
        assert len(list(session.scalars(select(AuditLog)))) == 1


def test_seed_enrollment_login_and_preservation(sessions):
    seed = SeedService(sessions)
    seed.super_admin("owner@example.com", "0540000000")
    now = [datetime(2026, 9, 8, 12, 0, tzinfo=timezone.utc)]
    box = SecretBox(Fernet.generate_key())
    auth = AuthService(sessions, lambda create=False: box, now=lambda: now[0])
    assert auth.needs_bootstrap()
    profile = auth.bootstrap_profile()
    assert profile == {"username": "owner", "email": "owner@example.com"}
    ticket = auth.prepare_setup(**profile)
    codes = auth.confirm_setup(ticket.token, pyotp.TOTP(ticket.secret).at(now[0]))
    with sessions() as session:
        user = session.get(User, ticket.user_id)
        encrypted = user.totp_secret_encrypted
        hashes = list(session.scalars(select(RecoveryCode.code_hash)))
    result = seed.super_admin("owner@example.com", "0540000001")
    assert not result["enrollment_required"]
    assert not auth.needs_bootstrap()
    with sessions() as session:
        user = session.get(User, ticket.user_id)
        assert user.totp_secret_encrypted == encrypted
        assert list(session.scalars(select(RecoveryCode.code_hash))) == hashes
    now[0] += timedelta(seconds=30)
    assert auth.login("owner@example.com", pyotp.TOTP(ticket.secret).at(now[0])).user_id == ticket.user_id
    assert len(codes) == 10


def test_seed_preserves_disabled_state_and_lockout(sessions):
    result = SeedService(sessions).super_admin("owner@example.com", "0540000000")
    locked = datetime.now(timezone.utc) + timedelta(minutes=15)
    with sessions() as session, session.begin():
        user = session.get(User, uuid.UUID(result["id"]))
        user.is_active, user.locked_until, user.failed_login_attempts = False, locked, 3
    SeedService(sessions).super_admin("owner@example.com", "0540000000")
    with sessions() as session:
        user = session.get(User, uuid.UUID(result["id"]))
        assert not user.is_active and user.locked_until == locked and user.failed_login_attempts == 3


def test_seed_refuses_other_existing_account(sessions):
    with sessions() as session, session.begin():
        session.add(User(username="existing", email="existing@example.com", role=UserRole.ADMIN))
    with pytest.raises(ValueError):
        SeedService(sessions).super_admin("owner@example.com", "0540000000")
    with pytest.raises(ValueError):
        SeedService(sessions).super_admin("existing@example.com", "0540000000")


@pytest.mark.parametrize("email,phone", [("invalid", "0540000000"), ("owner@example.com", "bad")])
def test_seed_validates_contacts(sessions, email, phone):
    with pytest.raises(ValueError):
        SeedService(sessions).super_admin(email, phone)
