"""Integration fixtures never commit test records."""
import os
import pytest
from sqlalchemy.orm import Session


@pytest.fixture
def db():
    if os.getenv("FAMILY_RUN_DB_TESTS") != "1":
        pytest.skip("Set FAMILY_RUN_DB_TESTS=1 for rollback-only PostgreSQL tests")
    from config.database import engine
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
                yield session
        finally:
            transaction.rollback()
