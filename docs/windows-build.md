# Windows executable

This is a 64-bit Windows folder build. Python does not need to be installed on the target computer. Keep `FamilyManagement.exe` beside its `_internal` folder; do not copy the executable alone.

## On this computer

Open `dist/FamilyManagement/FamilyManagement.exe`. The local `app-data-dir.txt` points to the existing project data folder, preserving its `.env`, encryption key, media, reports and backups. The build does not migrate/reset the database or copy secrets into the executable. Close the previous Python app when switching to the executable; restore requires other database clients to be closed.

## On another computer

Extract the entire `FamilyManagement-Windows-x64.zip` to a suitable program folder. The shareable ZIP excludes this computer's data pointer, `.env`, records, images, backups, logs, debug scripts and tests.

By default, writable data is under `%LOCALAPPDATA%/FamilyManagement`. Before launching, configure `.env` there using `.env.example` as a template. PostgreSQL must be installed/reachable and have the application's existing schema. When using an existing database, preserve its original `APP_ENCRYPTION_KEY` and matching media folder; do not generate a replacement key. For a new database, apply the repository's Alembic migrations using the source setup before launching this build.

To use another existing data directory, place its absolute path on one line in `app-data-dir.txt` beside the executable, or set `FAMILY_APP_DATA_DIR`. Environment override takes priority. Keep writable data outside the executable folder so replacing the build does not replace records or configuration.

PostgreSQL server and client programs are external dependencies. For backup/restore, install compatible `pg_dump.exe` and `pg_restore.exe`; configure `PG_DUMP_PATH` if automatic detection cannot find them. Google Drive copies require Google Drive for desktop and the configured sync folder. Cloud upload follows the desktop client's status.

The executable is not code-signed. No installer or signing certificate is included.

## Verification

Run `FamilyManagement.exe --self-check` and wait for it to exit. Results are written to the selected data folder's `logs/packaging-check.json`; errors are recorded in `logs/application.log`. This diagnostic connects read-only to PostgreSQL, creates a temporary database dump, checks its schema version, generates temporary PDF/Excel/QR files and opens/closes the real login screen. It does not restore data, enroll users or bypass sign-in. A normal launch remains at the sign-in screen.

## Rebuild

From the project root:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.venv\Scripts\python.exe scripts/build_windows.py
```

The script rebuilds the folder, copies this guide and the example configuration, creates the local data pointer, and writes a shareable ZIP plus SHA-256 checksum. Build outputs remain ignored by Git.

Implementation references: [PyInstaller runtime paths](https://pyinstaller.org/en/stable/runtime-information.html) and [external program DLL handling](https://pyinstaller.org/en/stable/common-issues-and-pitfalls.html#launching-external-programs-from-the-frozen-application).

## Latest rebuild: 9 September 2026

Rebuilt after the contribution eligibility and period/payment screen updates. Confirmed the new contribution modules are present in the executable. Packaged self-check passed database/schema, encryption, QR, PDF/Excel, backup/restore preflight and the real Tkinter login screen. ZIP integrity, SHA-256 and private configuration exclusion passed.

ZIP SHA-256: `ce9c3deec5332b2f0b93124e6bec8f6a9e899f24da72b2f001f8e64d8650d1ea`.
