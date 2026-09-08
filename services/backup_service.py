"""Verified database/media archives with optional Google Drive desktop copies."""
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
    def __init__(self, sessions, actor_id, database_url, media_root, backup_root, *, drive_folder=None):
        super().__init__(sessions, actor_id)
        self.url = database_url
        self.drive_folder = Path(drive_folder) if drive_folder else None
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

    def create(self, *, sync=True):
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
            if sync and self.drive_folder:
                self.sync_to_drive(final)
            return str(final)
        finally:
            dump.unlink(missing_ok=True)
            partial.unlink(missing_ok=True)

    @staticmethod
    def validate(path):
        from pathlib import PurePosixPath
        import stat
        try:
            with zipfile.ZipFile(path) as archive:
                names = archive.namelist()
                if len({name.casefold() for name in names}) != len(names):
                    raise ValueError("Backup contains duplicate file names")
                if archive.getinfo("manifest.json").file_size > 8 * 1024 * 1024:
                    raise ValueError("Backup manifest is too large")
                manifest = json.loads(archive.read("manifest.json"))
                files = manifest.get("files")
                if not isinstance(files, dict) or "database.dump" not in files:
                    raise ValueError("Backup is missing its database archive")
                if set(names) != set(files) | {"manifest.json"}:
                    raise ValueError("Backup contains missing or unlisted files")
                for name, expected in files.items():
                    parts = PurePosixPath(name).parts
                    if (not name or "\\" in name or ":" in name or name.startswith("/")
                            or any(part in ("", ".", "..") or part.endswith((".", " ")) for part in name.split("/"))
                            or name != "database.dump" and (len(parts) < 2 or parts[0] != "media")):
                        raise ValueError("Backup contains an unsafe file path")
                    info = archive.getinfo(name)
                    if stat.S_ISLNK(info.external_attr >> 16) or info.is_dir():
                        raise ValueError("Backup contains unsupported file entries")
                    if not isinstance(expected, str) or len(expected) != 64:
                        raise ValueError("Backup checksum verification failed")
                    digest = hashlib.sha256()
                    with archive.open(name) as source:
                        while chunk := source.read(1024 * 1024):
                            digest.update(chunk)
                    if digest.hexdigest() != expected:
                        raise ValueError("Backup checksum verification failed")
            return manifest
        except (zipfile.BadZipFile, KeyError, TypeError, json.JSONDecodeError) as exc:
            raise ValueError("Backup is incomplete or invalid") from exc

    def due(self, frequency):
        days = {"DAILY": 1, "WEEKLY": 7, "MONTHLY": 30}.get(frequency)
        if days is None:
            return False
        files = list(self.backup_root.glob("family_*.zip"))
        if not files:
            return True
        latest = max(p.stat().st_mtime for p in files)
        return datetime.now(timezone.utc).timestamp() - latest >= days * 86400

    def sync_to_drive(self, path):
        from services.drive_backup import copy_to_drive
        with self.transaction(super_admin=True):
            pass
        if not self.drive_folder:
            raise ValueError("Choose your Google Drive desktop backup folder in Settings first.")
        path = Path(path).resolve()
        if path.parent != self.backup_root or path.suffix != ".zip":
            raise ValueError("Choose a local application backup.")
        self.validate(path)
        try:
            return copy_to_drive(path, self.drive_folder)
        except (OSError, ValueError) as exc:
            raise ValueError(f"Local backup is safe at {path}. Google Drive copy is pending: {exc}") from exc

    def sync_all(self):
        with self.transaction(super_admin=True):
            pass
        files = sorted(self.backup_root.glob("family_*.zip"))
        if not files:
            raise ValueError("Create a local backup first.")
        for path in files:
            self.sync_to_drive(path)
        return len(files)

    def scheduled(self, frequency):
        result = self.create() if self.due(frequency) else None
        if self.drive_folder and list(self.backup_root.glob("family_*.zip")):
            self.sync_all()
        return result

    def latest(self):
        with self.transaction(super_admin=True):
            pass
        files = list(self.backup_root.glob("family_*.zip"))
        if self.drive_folder:
            try:
                files += list(self.drive_folder.glob("family_*.zip"))
            except OSError:
                pass
        if not files:
            raise ValueError("No backups found locally or in the configured Google Drive folder.")
        # Generated names contain UTC timestamps, independent of download/copy times.
        latest = max(files, key=lambda p: p.name)
        self.validate(latest)
        if latest.parent.resolve() == self.backup_root:
            return latest
        self.backup_root.mkdir(parents=True, exist_ok=True)
        destination = self.backup_root / latest.name
        partial = self.backup_root / (latest.name + ".download.partial")
        try:
            shutil.copyfile(latest, partial)
            self.validate(partial)
            partial.replace(destination)
        finally:
            partial.unlink(missing_ok=True)
        return destination
