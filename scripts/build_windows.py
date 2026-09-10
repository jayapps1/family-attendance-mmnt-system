"""Build and archive the application without including private data."""
import argparse
import hashlib
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--assemble-only", action="store_true")
    args = parser.parse_args()
    output = (ROOT / "dist" / "FamilyManagement").resolve()
    if not output.is_relative_to(ROOT):
        raise SystemExit("Build output must stay inside this workspace.")
    allowed = {"_internal", "FamilyManagement.exe", "README.txt", ".env.example", "app-data-dir.txt"}
    if output.exists() and any(p.name not in allowed for p in output.iterdir()):
        raise SystemExit("Unexpected files in build output; move user data out before rebuilding.")
    if not args.assemble_only:
        subprocess.run([sys.executable, "-m", "PyInstaller", str(ROOT / "FamilyManagement.spec"),
                        "--distpath", str(ROOT / "dist"), "--workpath", str(ROOT / "build"),
                        "--noconfirm"], cwd=ROOT, check=True)
    if not (output / "FamilyManagement.exe").is_file():
        raise SystemExit("Build the executable first.")
    shutil.copyfile(ROOT / "docs" / "windows-build.md", output / "README.txt")
    shutil.copyfile(ROOT / ".env.example", output / ".env.example")
    (output / "app-data-dir.txt").write_text(str(ROOT), encoding="utf-8")
    archive_path = ROOT / "dist" / "FamilyManagement-Windows-x64.zip"
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(output.rglob("*")):
            if not path.is_file() or path.name == "app-data-dir.txt":
                continue
            relative = path.relative_to(output)
            if path.name == ".env" or any(p in {"media", "backups", "logs", "tests", "temporary"} for p in relative.parts):
                raise SystemExit("Private or test data unexpectedly found in the bundle.")
            archive.write(path, "FamilyManagement/" + relative.as_posix())
    with archive_path.open("rb") as source:
        digest = hashlib.file_digest(source, "sha256").hexdigest()
    (ROOT / "dist" / "FamilyManagement-Windows-x64.sha256").write_text(digest + "  " + archive_path.name + "\n")
    print(archive_path)
    print("SHA256:", digest)


if __name__ == "__main__":
    main()
