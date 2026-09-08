from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch
import hashlib
import json
import zipfile
import pytest
from PIL import Image
from services.backup_service import BackupService
from services.restore_service import RestoreService
from services.drive_backup import copy_to_drive, file_digest
from utils.profile_image import prepare_portrait, crop_portrait, load_portrait


def archive_at(path, files):
    manifest = {"created_at": "2026-09-08T06:36:20+00:00",
                "files": {name: hashlib.sha256(data).hexdigest() for name, data in files.items()}}
    with zipfile.ZipFile(path, "w") as archive:
        for name, data in files.items():
            archive.writestr(name, data)
        archive.writestr("manifest.json", json.dumps(manifest))
    return path


def test_portrait_crop_size_and_original(tmp_path):
    path = tmp_path / "portrait.png"
    source = Image.new("RGB", (800, 400), "red")
    source.paste("blue", (400, 0, 800, 400))
    source.save(path)
    original = path.read_bytes()
    loaded = load_portrait(path)
    assert crop_portrait(loaded, horizontal=0).getpixel((256, 256))[0] > 200
    assert crop_portrait(loaded, horizontal=1).getpixel((256, 256))[2] > 200
    photo = prepare_portrait(loaded, size=1024, zoom=2, horizontal=1)
    from io import BytesIO
    with Image.open(BytesIO(photo.data)) as result:
        assert result.size == (1024, 1024)
        assert not result.getexif()
    assert path.read_bytes() == original
    with pytest.raises(ValueError):
        prepare_portrait(loaded, size=400)


@pytest.mark.parametrize("name", ["../outside.txt", "media/../../outside.txt", "/media/a", "media/../a",
                                  "media/a:stream", "media\\a", "media/a.", "media//a"])
def test_restore_rejects_unsafe_archives(tmp_path, name):
    backup = archive_at(tmp_path / "bad.zip", {"database.dump": b"db", name: b"bad"})
    with pytest.raises(ValueError):
        BackupService.validate(backup)


def test_drive_copy_and_collision(tmp_path):
    source = tmp_path / "backup.zip"
    source.write_bytes(b"verified archive")
    folder = tmp_path / "drive"
    folder.mkdir()
    target = Path(copy_to_drive(source, folder))
    assert file_digest(target) == file_digest(source)
    assert copy_to_drive(source, folder) == str(target)
    source.write_bytes(b"other archive")
    with pytest.raises(ValueError, match="different file"):
        copy_to_drive(source, folder)
    assert not list(folder.glob("*.partial"))
    with pytest.raises(ValueError, match="unavailable"):
        copy_to_drive(source, tmp_path / "not-connected")
    assert not (tmp_path / "not-connected").exists()


def test_prepared_photo_member_save_and_failure_cleanup(db, tmp_path):
    from services.family_service import FamilyService
    from tests.service_helpers import service_context
    service = FamilyService(*service_context(db))
    photo = prepare_portrait(Image.new("RGB", (600, 800), "blue"))
    member = service.save_with_photo(dict(first_name="Photo", last_name="Test", sex="FEMALE", profile_image_path=photo), tmp_path)
    target = tmp_path / member["profile_image_path"]
    assert target.is_file()
    before = set(tmp_path.rglob("*.jpg"))
    with pytest.raises(ValueError):
        service.save_with_photo(dict(first_name="", last_name="Test", sex="FEMALE", profile_image_path=photo), tmp_path)
    assert set(tmp_path.rglob("*.jpg")) == before
    service.save_with_photo({"profile_image_path": None}, tmp_path, identity=member["id"])
    assert target.exists()  # Old originals remain available to backups.


class FakeBackup:
    def __init__(self, root):
        self.backup_root, self.media_root = root / "backups", root / "media"
        self.backup_root.mkdir()
        self.media_root.mkdir()
        self.safety_created = False
    @contextmanager
    def transaction(self, **kwargs):
        assert kwargs["super_admin"]
        yield
    validate = staticmethod(BackupService.validate)
    def create(self, **kwargs):
        assert kwargs == {"sync": False}
        self.safety_created = True
        return str(self.backup_root / "safety.zip")


def test_restore_failure_rolls_media_back(tmp_path):
    backup = FakeBackup(tmp_path)
    (backup.media_root / "old.txt").write_bytes(b"current")
    path = archive_at(backup.backup_root / "family_test.zip", {"database.dump": b"dump",
                      "media/old.txt": b"old", "media/new.txt": b"restored"})
    service = RestoreService(backup)
    with patch.object(service, "_check_dump"), patch.object(service, "_quiet_database"), \
         patch.object(service, "_restore_database", side_effect=ValueError("restore failed")):
        with pytest.raises(ValueError, match="restore failed"):
            service.restore(path, file_digest(path), "RESTORE")
    assert backup.safety_created
    assert (backup.media_root / "old.txt").read_bytes() == b"current"
    assert not (backup.media_root / "new.txt").exists()
    assert not (backup.backup_root / "restore-in-progress.json").exists()
    assert not list(tmp_path.glob(".family-restore-*"))


def test_restore_confirmation_and_changed_backup(tmp_path):
    backup = FakeBackup(tmp_path)
    path = archive_at(backup.backup_root / "family_test.zip", {"database.dump": b"dump"})
    service = RestoreService(backup)
    with pytest.raises(ValueError, match="Type RESTORE"):
        service.restore(path, file_digest(path), "")
    with pytest.raises(ValueError, match="changed"):
        service.restore(path, "wrong hash", "RESTORE")
    assert not backup.safety_created


def test_restore_preserves_existing_journal(tmp_path):
    backup = FakeBackup(tmp_path)
    path = archive_at(backup.backup_root / "family_test.zip", {"database.dump": b"dump"})
    journal = backup.backup_root / "restore-in-progress.json"
    journal.write_text("existing recovery record")
    with pytest.raises(ValueError, match="interrupted"):
        RestoreService(backup).restore(path, file_digest(path), "RESTORE")
    assert journal.read_text() == "existing recovery record"


def test_latest_backup_downloads_newer_drive_copy(tmp_path):
    backup = FakeBackup(tmp_path)
    backup.drive_folder = tmp_path / "drive"
    backup.drive_folder.mkdir()
    archive_at(backup.backup_root / "family_20260101_120000_a.zip", {"database.dump": b"old"})
    remote = archive_at(backup.drive_folder / "family_20260908_120000_b.zip", {"database.dump": b"new"})
    latest = BackupService.latest(backup)
    assert latest.parent == backup.backup_root
    assert latest.name == remote.name
    assert file_digest(latest) == file_digest(remote)
    assert remote.exists()


def test_latest_backup_works_when_drive_missing(tmp_path):
    backup = FakeBackup(tmp_path)
    backup.drive_folder = tmp_path / "offline-drive"
    local = archive_at(backup.backup_root / "family_20260101_120000_a.zip", {"database.dump": b"old"})
    assert BackupService.latest(backup) == local
