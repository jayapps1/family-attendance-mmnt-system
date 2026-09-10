"""Explicit read-only frozen-build diagnostics: FamilyManagement.exe --self-check."""
import json
from pathlib import Path
import tempfile
import time
from utils.runtime_paths import data_root, resource_root


def run_check():
    results = {}
    app = None
    try:
        from cryptography.fernet import Fernet
        from utils.security import SecretBox
        box = SecretBox(Fernet.generate_key())
        assert box.decrypt(box.encrypt("build-check")) == "build-check"
        import pyotp
        import qrcode
        from PIL import Image
        from reportlab.pdfgen.canvas import Canvas
        from openpyxl import Workbook, load_workbook
        from alembic.config import Config
        from alembic.script import ScriptDirectory
        heads = ScriptDirectory.from_config(Config(str(resource_root() / "alembic.ini"))).get_heads()
        assert len(heads) == 1
        results["bundled_schema_head"] = heads[0]
        with tempfile.TemporaryDirectory(prefix="family-build-check-") as folder:
            folder = Path(folder)
            qrcode.make(pyotp.TOTP(pyotp.random_base32()).provisioning_uri("build-check")).save(folder / "qr.png")
            with Image.open(folder / "qr.png") as picture:
                picture.load()
            pdf = Canvas(str(folder / "check.pdf"))
            pdf.drawString(50, 750, "Family Management build verification")
            pdf.save()
            book = Workbook()
            book.active.append(["Build check", 60])
            book.save(folder / "check.xlsx")
            loaded = load_workbook(folder / "check.xlsx")
            assert loaded.active["B1"].value == 60
            loaded.close()
            assert (folder / "check.pdf").read_bytes().startswith(b"%PDF")
            results["crypto_qr_pdf_excel"] = "passed"
            from config.database import engine, DATABASE_URL
            from sqlalchemy import text
            with engine.connect() as connection:
                assert connection.execute(text("SELECT 1")).scalar_one() == 1
                assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == heads[0]
            results["database_and_schema"] = "passed"
            from services.backup_service import BackupService
            from services.restore_service import RestoreService
            from utils.external_process import system_libraries
            from types import SimpleNamespace
            import os
            import subprocess
            dump = folder / "check.dump"
            env = os.environ.copy()
            env["PGPASSWORD"] = DATABASE_URL.password or ""
            with system_libraries():
                completed = subprocess.run([BackupService.pg_dump(), "--host", DATABASE_URL.host or "localhost",
                    "--port", str(DATABASE_URL.port or 5432), "--username", DATABASE_URL.username,
                    "--dbname", DATABASE_URL.database, "--no-password", "--format=custom", "--file", str(dump)],
                    env=env, capture_output=True, timeout=120, creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
            assert completed.returncode == 0, "PostgreSQL dump client failed"
            RestoreService(SimpleNamespace(pg_dump=BackupService.pg_dump, url=DATABASE_URL))._check_dump(dump)
            results["frozen_backup_restore_preflight"] = "passed"
        from ui.app import Application
        from ui.auth.login_window import LoginView
        from tkinter import messagebox
        errors = []
        original_error = messagebox.showerror
        messagebox.showerror = lambda *args, **kwargs: errors.append("UI error")
        try:
            app = Application()
            app.report_callback_exception = lambda *args: errors.append("Tk callback error")
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                app.update()
                if not app.pending and isinstance(app.screen, LoginView):
                    break
                time.sleep(0.05)
            assert isinstance(app.screen, LoginView) and not app.pending and not errors
            results["tk_login_screen"] = "passed"
        finally:
            messagebox.showerror = original_error
        results["status"] = "passed"
    except Exception as exc:
        from utils.logger import log_exception
        log_exception("Frozen build check failed", exc)
        results["status"] = "failed"
        results["error_type"] = type(exc).__name__
    finally:
        if app:
            app.executor.shutdown(wait=True, cancel_futures=True)
            app.destroy()
        path = data_root() / "logs" / "packaging-check.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    if results["status"] != "passed":
        raise SystemExit(1)
