"""Opt-in real pg_dump smoke test; writes only a temporary backup artifact."""
import os
from pathlib import Path
import subprocess
import zipfile
import pytest
from services.backup_service import BackupService
from tests.service_helpers import service_context

pytestmark = pytest.mark.skipif(os.getenv("FAMILY_RUN_BACKUP_TESTS") != "1",
                                reason="Set FAMILY_RUN_BACKUP_TESTS=1 to exercise installed pg_dump")


def test_real_pg_dump_archive(db, tmp_path):
    from config.database import DATABASE_URL
    service = BackupService(*service_context(db), DATABASE_URL, tmp_path / "media", tmp_path / "backups")
    path = service.create()
    assert service.validate(path)["files"]["database.dump"]
    dump = tmp_path / "verified.dump"
    with zipfile.ZipFile(path) as archive:
        dump.write_bytes(archive.read("database.dump"))
    executable = Path(service.pg_dump()).with_name("pg_restore.exe" if os.name == "nt" else "pg_restore")
    result = subprocess.run([str(executable), "--list", str(dump)], capture_output=True, text=True,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), timeout=60)
    assert result.returncode == 0
    assert "contribution_payments" in result.stdout
    assert "audit_logs" in result.stdout
