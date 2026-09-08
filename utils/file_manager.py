"""Managed media import with relative paths and safe generated filenames."""
from pathlib import Path, PureWindowsPath
import shutil
import uuid

ALLOWED = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".mp4", ".mov", ".mp3", ".wav", ".pdf", ".txt", ".docx"}


def relative_media_path(value: str) -> str:
    value = value.replace("\\", "/")
    path = Path(value)
    if value.startswith("/") or path.is_absolute() or PureWindowsPath(value).drive or ".." in path.parts or not value or ":" in value:
        raise ValueError("Media paths must be relative and stay inside the media directory")
    return path.as_posix()


class FileManager:
    def __init__(self, root: Path):
        self.root = Path(root).resolve()

    def resolve(self, relative: str) -> Path:
        path = (self.root / relative_media_path(relative)).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError("Media path escapes the media directory")
        return path

    def import_file(self, source: Path, folder: str) -> str:
        source = Path(source)
        if not source.is_file() or source.suffix.lower() not in ALLOWED:
            raise ValueError("Choose a supported image, video, audio or document file")
        relative = relative_media_path(folder + "/" + uuid.uuid4().hex + source.suffix.lower())
        target = self.resolve(relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        return relative

    def discard_import(self, relative: str) -> None:
        # Only used for a newly imported file after a failed database transaction.
        self.resolve(relative).unlink(missing_ok=True)
