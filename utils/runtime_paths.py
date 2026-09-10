"""Keep writable application data separate from frozen program resources."""
import os
import sys
from pathlib import Path


def resource_root():
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))


def data_root():
    configured = os.getenv("FAMILY_APP_DATA_DIR")
    if configured:
        return Path(configured).expanduser().resolve()
    if getattr(sys, "frozen", False):
        pointer = Path(sys.executable).resolve().parent / "app-data-dir.txt"
        if pointer.is_file():
            path = Path(pointer.read_text(encoding="utf-8-sig").strip()).expanduser()
            if not path.is_absolute():
                raise ValueError("app-data-dir.txt must contain an absolute data-folder path.")
            return path.resolve()
        return Path(os.getenv("LOCALAPPDATA", str(Path.home()))) / "FamilyManagement"
    return resource_root()
