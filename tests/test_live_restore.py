"""Real restore in a disposable PostgreSQL cluster, never the configured database."""
import os
import socket
import subprocess
from pathlib import Path
import pytest

pytestmark = pytest.mark.skipif(os.getenv("FAMILY_RUN_RESTORE_TESTS") != "1",
                                reason="Set FAMILY_RUN_RESTORE_TESTS=1 for an isolated PostgreSQL restore test")


def test_live_restore_roundtrip(tmp_path):
    from sqlalchemy import create_engine, text
    from sqlalchemy.engine import URL
    from sqlalchemy.orm import sessionmaker
    from services.backup_service import BackupService
    from services.restore_service import RestoreService
    from services.family_service import FamilyService
    from services.drive_backup import file_digest
    from models import Base, User, UserRole
    from alembic.script import ScriptDirectory
    from alembic.config import Config
    from config.settings import BASE_DIR
    from uuid import uuid4
    tools = Path(BackupService.pg_dump()).parent
    suffix = ".exe" if os.name == "nt" else ""
    data = tmp_path / "postgres"
    def command(name, *args):
        output = tmp_path / (name + "-" + uuid4().hex + ".log")
        with output.open("wb") as log:
            result = subprocess.run([str(tools / (name + suffix)), *map(str, args)], stdout=log, stderr=log,
                                    stdin=subprocess.DEVNULL, timeout=90,
                                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        assert result.returncode == 0, output.read_text(errors="replace")
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    command("initdb", "-D", data, "-A", "trust", "-U", "restore_test", "--no-locale", "--encoding=UTF8")
    command("pg_ctl", "-D", data, "-l", tmp_path / "server.log", "-o", f"-h 127.0.0.1 -p {port}", "-w", "start")
    engine = None
    try:
        url = URL.create("postgresql+psycopg", username="restore_test", host="127.0.0.1", port=port, database="postgres")
        engine = create_engine(url)
        Base.metadata.create_all(engine)
        heads = ScriptDirectory.from_config(Config(str(BASE_DIR / "alembic.ini"))).get_heads()
        with engine.begin() as connection:
            connection.execute(text("CREATE TABLE alembic_version (version_num varchar(32) PRIMARY KEY)"))
            for head in heads:
                connection.execute(text("INSERT INTO alembic_version VALUES (:head)"), {"head": head})
        sessions = sessionmaker(bind=engine)
        actor_id = uuid4()
        with sessions.begin() as session:
            session.add(User(id=actor_id, username="restore_verification", role=UserRole.SUPER_ADMIN,
                             totp_enabled=True, is_active=True))
        family = FamilyService(sessions, actor_id)
        member = family.create(first_name="Before", last_name="Restore", sex="FEMALE")
        media = tmp_path / "media"
        media.mkdir()
        (media / "portrait.txt").write_text("original")
        backup = BackupService(sessions, actor_id, url, media, tmp_path / "backups")
        original = Path(backup.create())
        family.update(member["id"], first_name="After")
        (media / "portrait.txt").write_text("changed")
        restore = RestoreService(backup)
        result = restore.restore(original, file_digest(original), "RESTORE")
        assert family.list()[0]["first_name"] == "Before"
        assert (media / "portrait.txt").read_text() == "original"
        assert Path(result["safety_backup"]).is_file()
        assert Path(result["safety_backup"]) != original
        assert not (backup.backup_root / "restore-in-progress.json").exists()
    finally:
        if engine is not None:
            engine.dispose()
        command("pg_ctl", "-D", data, "-m", "fast", "-w", "stop")
