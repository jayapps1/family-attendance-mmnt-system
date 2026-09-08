"""Copy verified archives to the user's Google Drive for desktop folder."""
from pathlib import Path
import hashlib
import os
import shutil
import uuid

DRIVE_FOLDER_URL = "https://drive.google.com/drive/folders/1G_WIA9t2frW7Lr8TN035LXhPK12Mv0ZE"


def file_digest(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as reader:
        while chunk := reader.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def copy_to_drive(source, folder):
    source, folder = Path(source).resolve(), Path(folder)
    if not folder.is_dir():
        raise ValueError("Google Drive is unavailable. Start Google Drive for desktop and check the backup folder.")
    destination = folder / source.name
    if destination.resolve() == source:
        raise ValueError("Choose a Google Drive folder separate from local backups.")
    expected = file_digest(source)
    if destination.exists():
        if file_digest(destination) == expected:
            return str(destination)
        raise ValueError("A different file already uses this backup name in Google Drive.")
    partial = folder / (source.name + "." + uuid.uuid4().hex + ".partial")
    try:
        shutil.copyfile(source, partial)
        if file_digest(partial) != expected:
            raise ValueError("Google Drive copy failed checksum verification.")
        os.replace(partial, destination)
    finally:
        partial.unlink(missing_ok=True)
    return str(destination)
