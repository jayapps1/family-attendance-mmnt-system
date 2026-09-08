"""Non-destructive database/media backup; no restore operation is exposed."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import uuid
import zipfile
from services.base import Service
from services.audit_service import append_audit


class BackupService(Service):
    def __init__(self, sessions, actor_id, database_url, media_root, backup_root):
        super().__init__(sessions, actor_id)
        self.url = database_url
        self.media_root, self.backup_root = Path(media_root).resolve(), Path(backup_root).resolve()

    @staticmethod
    def pg_dump():
        configured = os.getenv("PG_DUMP_PATH")
        if configured and Path(configured).is_file():
            return configured
        found = shutil.which("pg_dump")
        if found:
            return found
        root = Path(os.getenv("ProgramFiles", "C:/Program Files")) / "PostgreSQL"
        candidates = list(root.glob("*/bin/pg_dump.exe"))
        if candidates:
            return str(sorted(candidates, key=lambda p: int(p.parents[1].name) if p.parents[1].name.isdigit() else 0)[-1])
        raise ValueError("Install PostgreSQL client tools or set PG_DUMP_PATH to pg_dump.exe")

    def create(self):
        with self.transaction(super_admin=True):
            pass
        self.backup_root.mkdir(parents=True, exist_ok=True)
        stem = datetime.now(timezone.utc).strftime("family_%Y%m%d_%H%M%S_") + uuid.uuid4().hex[:8]
        dump = self.backup_root / (stem + ".dump")
        partial = self.backup_root / (stem + ".partial")
        final = self.backup_root / (stem + ".zip")
        env = os.environ.copy()
        env["PGPASSWORD"] = self.url.password or ""
        command = [self.pg_dump(), "--host", self.url.host or "localhost", "--port", str(self.url.port or 5432),
                   "--username", self.url.username, "--dbname", self.url.database, "--no-password",
                   "--format=custom", "--file", str(dump)]
        try:
            result = subprocess.run(command, env=env, capture_output=True, timeout=600,
                                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            if result.returncode:
                raise ValueError("pg_dump failed. Check client/server versions and database access.")
            manifest = {"created_at": datetime.now(timezone.utc).isoformat(), "files": {}}
            with zipfile.ZipFile(partial, "w", zipfile.ZIP_DEFLATED) as archive:
                sources = [(dump, "database.dump")]
                if self.media_root.exists():
                    sources += [(p, "media/" + p.relative_to(self.media_root).as_posix())
                                for p in self.media_root.rglob("*")
                                if p.is_file() and not p.is_symlink() and "temporary" not in p.relative_to(self.media_root).parts
                                and p.resolve().is_relative_to(self.media_root)]
                for source, name in sources:
                    digest = hashlib.sha256()
                    with source.open("rb") as reader, archive.open(name, "w") as writer:
                        while chunk := reader.read(1024 * 1024):
                            digest.update(chunk)
                            writer.write(chunk)
                    manifest["files"][name] = digest.hexdigest()
                archive.writestr("manifest.json", json.dumps(manifest, indent=2))
            self.validate(partial)
            partial.replace(final)
            with self.transaction(super_admin=True) as session:
                append_audit(session, self.actor_id, "BACKUP", "backup", description=final.name)
            return str(final)
        finally:
            dump.unlink(missing_ok=True)
            partial.unlink(missing_ok=True)

    @staticmethod
    def validate(path):
        with zipfile.ZipFile(path) as archive:
            manifest = json.loads(archive.read("manifest.json"))
            if "database.dump" not in manifest["files"]:
                raise ValueError("Backup is missing its database archive")
            for name, expected in manifest["files"].items():
                digest = hashlib.sha256()
                with archive.open(name) as source:
                    while chunk := source.read(1024 * 1024):
                        digest.update(chunk)
                if digest.hexdigest() != expected:
                    raise ValueError("Backup checksum verification failed")
        return manifest

    def due(self, frequency):
        days = {"DAILY": 1, "WEEKLY": 7, "MONTHLY": 30}.get(frequency)
        if days is None:
            return False
        files = list(self.backup_root.glob("family_*.zip"))
        if not files:
            return True
        latest = max(p.stat().st_mtime for p in files)
        return datetime.now(timezone.utc).timestamp() - latest >= days * 86400
