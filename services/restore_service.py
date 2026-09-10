"""Explicit, administrator-only restore with preflight and a safety archive."""
from pathlib import Path
import json
import os
import re
import shutil
import subprocess
import tempfile
import zipfile
from services.drive_backup import file_digest
from utils.file_manager import FileManager


class RestoreService:
    def __init__(self, backup):
        self.backup = backup

    def preview_latest(self):
        path = self.backup.latest()
        manifest = self.backup.validate(path)
        return dict(path=str(path), name=path.name, created_at=manifest.get("created_at", "Unknown"),
                    media_count=sum(name.startswith("media/") for name in manifest["files"]),
                    size=path.stat().st_size, sha256=file_digest(path))

    def _client(self, args):
        dump = Path(self.backup.pg_dump())
        restore = dump.with_name("pg_restore.exe" if os.name == "nt" else "pg_restore")
        if not restore.is_file():
            found = shutil.which("pg_restore")
            if not found:
                raise ValueError("Install pg_restore alongside the PostgreSQL backup tools.")
            restore = Path(found)
        env = os.environ.copy()
        env["PGPASSWORD"] = self.backup.url.password or ""
        env["PGOPTIONS"] = "-c lock_timeout=10000 -c statement_timeout=600000"
        from utils.external_process import system_libraries
        with system_libraries():
            result = subprocess.run([str(restore), *args], env=env, capture_output=True, timeout=660,
                                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if result.returncode:
            raise ValueError("PostgreSQL could not complete the restore step. Check database access, other open applications and PostgreSQL client versions.")
        return result.stdout.decode("utf-8", errors="replace")

    def _check_dump(self, dump):
        from alembic.config import Config
        from alembic.script import ScriptDirectory
        from utils.runtime_paths import resource_root
        contents = self._client(["--list", str(dump)])
        if "TABLE DATA public alembic_version" not in contents:
            raise ValueError("Backup has no application schema version.")
        sql = self._client(["--data-only", "--table=alembic_version", "--file=-", str(dump)])
        match = re.search(r"COPY [^\n]*alembic_version[^\n]* FROM stdin;\r?\n(.*?)\r?\n\\\.", sql, re.S)
        revisions = set(match.group(1).splitlines()) if match else set()
        heads = set(ScriptDirectory.from_config(Config(str(resource_root() / "alembic.ini"))).get_heads())
        if revisions != heads:
            raise ValueError("This backup uses a different database version. Restore it with its matching application version first.")

    def _quiet_database(self):
        # Close this application's idle pooled connections before checking other clients.
        bind = self.backup.sessions.kw.get("bind")
        if not hasattr(bind, "dispose"):
            raise ValueError("Restore requires its own database connection pool.")
        bind.dispose()
        import psycopg
        url = self.backup.url
        with psycopg.connect(host=url.host or "localhost", port=url.port or 5432, user=url.username,
                             password=url.password, dbname=url.database, connect_timeout=10) as connection:
            count = connection.execute(
                "SELECT count(*) FROM pg_stat_activity WHERE datname=current_database() "
                "AND pid<>pg_backend_pid() AND backend_type='client backend'").fetchone()[0]
        if count:
            raise ValueError("Close other Family Management windows and database tools, then try restoring again.")

    def _restore_database(self, dump):
        url = self.backup.url
        self._client(["--host", url.host or "localhost", "--port", str(url.port or 5432),
                      "--username", url.username, "--dbname", url.database, "--no-password",
                      "--clean", "--if-exists", "--no-owner", "--no-privileges",
                      "--single-transaction", "--exit-on-error", str(dump)])

    def restore(self, path, expected_sha256, confirmation):
        if confirmation != "RESTORE":
            raise ValueError("Type RESTORE to confirm replacing current records.")
        with self.backup.transaction(super_admin=True):
            pass
        path = Path(path).resolve()
        if path.parent != self.backup.backup_root or not path.name.startswith("family_") or path.suffix != ".zip":
            raise ValueError("Select an application backup from the local backups folder.")
        if file_digest(path) != expected_sha256:
            raise ValueError("The selected backup changed. Open the restore preview again.")
        journal = self.backup.backup_root / "restore-in-progress.json"
        if journal.exists():
            raise ValueError("An interrupted restore needs review before another restore. See backups/restore-in-progress.json.")
        manifest = self.backup.validate(path)
        self.backup.media_root.mkdir(parents=True, exist_ok=True)
        # Stage on the media volume so each final file replacement is atomic.
        stage = Path(tempfile.mkdtemp(prefix=".family-restore-", dir=self.backup.media_root.parent)).resolve()
        installed, database_restored, journal_owned = [], False, False
        warnings = []
        try:
            archive_copy = stage / "source.zip"
            shutil.copyfile(path, archive_copy)
            if file_digest(archive_copy) != expected_sha256:
                raise ValueError("The selected backup changed while being read.")
            with zipfile.ZipFile(archive_copy) as archive:
                size = sum(info.file_size for info in archive.infolist())
                if shutil.disk_usage(stage).free < size * 2 + archive_copy.stat().st_size:
                    raise ValueError("Not enough free space to stage and protect this restore.")
                for name in manifest["files"]:
                    target = stage / name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with archive.open(name) as source, target.open("wb") as destination:
                        shutil.copyfileobj(source, destination)
            self._check_dump(stage / "database.dump")
            self._quiet_database()
            safety = self.backup.create(sync=False)
            if getattr(self.backup, "drive_folder", None):
                try:
                    self.backup.sync_to_drive(safety)
                except (OSError, ValueError) as exc:
                    from utils.logger import log_exception
                    log_exception("Restore completed with a recoverable issue", exc)
                    warnings.append("The safety backup is saved locally; its Google Drive copy is pending.")
            # create() opened a pooled connection; close it before pg_restore.
            self._quiet_database()
            plan = dict(source=str(path), safety_backup=safety, stage=str(stage), files=[])
            with journal.open("x", encoding="utf-8") as handle:
                journal_owned = True
                json.dump(plan, handle, indent=2)
            files = FileManager(self.backup.media_root)
            for name in manifest["files"]:
                if not name.startswith("media/"):
                    continue
                relative = name.removeprefix("media/")
                target = files.resolve(relative)
                original = stage / "original" / relative
                existed = target.exists()
                if existed:
                    original.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(target, original)
                plan["files"].append(dict(target=str(target), original=str(original) if existed else None))
                journal.write_text(json.dumps(plan, indent=2), encoding="utf-8")
                target.parent.mkdir(parents=True, exist_ok=True)
                installed.append((target, original if existed else None))
                os.replace(stage / name, target)
            self._restore_database(stage / "database.dump")
            database_restored = True
            try:
                from models import User
                from services.audit_service import append_audit
                with self.backup.sessions.begin() as session:
                    actor = session.get(User, self.backup.actor_id)
                    append_audit(session, actor.id if actor else None, "RESTORE_BACKUP", "backup",
                                 description="Restored " + path.name + "; safety backup " + Path(safety).name)
            except Exception as exc:
                from utils.logger import log_exception
                log_exception("Restore completed with a recoverable issue", exc)
                warnings.append("Restore succeeded, but its audit entry could not be saved.")
            try:
                journal.unlink()
            except OSError as exc:
                from utils.logger import log_exception
                log_exception("Restore completed with a recoverable issue", exc)
                warnings.append("Restore succeeded; the restore recovery journal needs cleanup before another restore.")
            return dict(restored=str(path), safety_backup=safety, media_count=len(installed), warnings=warnings)
        except Exception:
            if not database_restored:
                for target, original in reversed(installed):
                    if original:
                        os.replace(original, target)
                    else:
                        target.unlink(missing_ok=True)
                if journal_owned:
                    journal.unlink(missing_ok=True)
            raise
        finally:
            # Retain recovery evidence after any incomplete rollback.
            if (not journal_owned or not journal.exists()) and stage.is_relative_to(self.backup.media_root.parent):
                try:
                    shutil.rmtree(stage)
                except OSError as exc:
                    from utils.logger import log_exception
                    log_exception("Restore completed with a recoverable issue", exc)
                    warnings.append("Temporary restore files could not be removed; they are retained locally.")
