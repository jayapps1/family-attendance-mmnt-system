"""Opt-in fresh-install/reversibility test in a uniquely named disposable schema."""
import os
import uuid
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect
from sqlalchemy.schema import CreateSchema, DropSchema
import config.database as database

pytestmark = pytest.mark.skipif(os.getenv("FAMILY_RUN_MIGRATION_TESTS") != "1",
                                reason="Requires permission to create a disposable PostgreSQL schema")


def test_fresh_upgrade_and_new_phase_downgrade(monkeypatch):
    name = "family_test_" + uuid.uuid4().hex
    assert name.startswith("family_test_") and len(name) == 44
    with database.engine.begin() as connection:
        connection.execute(CreateSchema(name))
    url = database.DATABASE_URL.update_query_dict({"options": "-csearch_path=" + name})
    isolated = create_engine(url)
    try:
        monkeypatch.setattr(database, "DATABASE_URL", url)
        config = Config("alembic.ini")
        command.upgrade(config, "474a79f1f1db")
        from sqlalchemy import text
        member_id = uuid.uuid4()
        with isolated.begin() as connection:
            connection.execute(text("INSERT INTO family_members (id, family_number, first_name, last_name, sex) VALUES (:id, 'MIGRATION-1', 'Existing', 'Preserved', 'MALE')"), {'id': member_id})
        command.upgrade(config, "head")
        with isolated.connect() as connection:
            inspector = inspect(connection)
            assert inspector.default_schema_name == name
            assert "contribution_payments" in inspector.get_table_names()
            assert 'marriage_children' in inspector.get_table_names()
            assert connection.scalar(text('SELECT affiliation_type FROM family_members WHERE id=:id'), {'id': member_id}) == 'LINEAGE_MEMBER'
            constraints = inspector.get_unique_constraints('marriage_children')
            assert {tuple(c['column_names']) for c in constraints} == {('marriage_id','child_id'),('marriage_id','birth_order')}
            assert "last_totp_step" in {c["name"] for c in inspector.get_columns("users")}
        # Reverse only this work's new phases, never the application's real schema.
        command.downgrade(config, "6dd251ef35d1")
        command.upgrade(config, "head")
        with isolated.connect() as connection:
            assert "audit_logs" in inspect(connection).get_table_names()
    finally:
        isolated.dispose()
        with database.engine.begin() as connection:
            connection.execute(DropSchema(name, cascade=True))
