from pathlib import Path
from decimal import Decimal
from unittest.mock import patch
import json
import zipfile
import pytest
from openpyxl import load_workbook
from services.report_service import ReportService
from services.backup_service import BackupService
from services.family_service import FamilyService
from services.gallery_service import GalleryService
from tests.service_helpers import service_context
from utils.file_manager import FileManager, relative_media_path


def test_pdf_excel_and_formula_safety(db, tmp_path):
    context = service_context(db)
    FamilyService(*context).create(first_name="=1+1", last_name="Export", sex="FEMALE")
    reports = ReportService(*context, tmp_path)
    pdf = Path(reports.export("Family register", "PDF"))
    excel = Path(reports.export("Family register", "Excel"))
    assert pdf.read_bytes().startswith(b"%PDF")
    book = load_workbook(excel)
    cells = [cell for row in book.active for cell in row if cell.value == "=1+1"]
    assert cells and all(cell.data_type == "s" for cell in cells)


@pytest.mark.parametrize("path", ["../secret", "C:/secret", "/etc/passwd", "gallery/../../secret", "file:stream"])
def test_media_path_rejects_escape(path):
    with pytest.raises(ValueError):
        relative_media_path(path)


def test_media_import_and_transaction_cleanup(db, tmp_path):
    context = service_context(db)
    source = tmp_path / "source.txt"
    source.write_text("Test")
    service = GalleryService(*context, tmp_path / "media")
    album = service.save_album("Test album")
    row = service.upload(album["id"], source, "Test attachment")
    assert not Path(row["file_path"]).is_absolute()
    assert service.files.resolve(row["file_path"]).read_text() == "Test"
    before = set((tmp_path / "media").rglob("*"))
    with pytest.raises(ValueError):
        service.upload(album["id"], source, "")
    assert set((tmp_path / "media").rglob("*")) == before


def test_backup_manifest_and_failed_dump_cleanup(db, tmp_path):
    from config.database import DATABASE_URL
    context = service_context(db)
    media = tmp_path / "media"
    media.mkdir()
    (media / "sample.txt").write_text("Preserved")
    service = BackupService(*context, DATABASE_URL, media, tmp_path / "backups")
    def fake_dump(command, **kwargs):
        assert "PGPASSWORD" in kwargs["env"]
        assert DATABASE_URL.password not in command
        Path(command[command.index("--file") + 1]).write_bytes(b"PGDMP-test")
        from subprocess import CompletedProcess
        return CompletedProcess(command, 0)
    with patch.object(service, "pg_dump", return_value="pg_dump"), patch("services.backup_service.subprocess.run", side_effect=fake_dump):
        path = service.create()
    manifest = service.validate(path)
    assert "media/sample.txt" in manifest["files"]
    assert not service.due("DAILY")
    assert not list((tmp_path / "backups").glob("*.dump"))
    with zipfile.ZipFile(path, "a") as archive:
        manifest["files"]["database.dump"] = "bad"
        # Build a separate malformed archive without modifying the verified one.
        bad = tmp_path / "bad.zip"
        with zipfile.ZipFile(bad, "w") as broken:
            broken.writestr("manifest.json", json.dumps(manifest))
            broken.writestr("database.dump", b"PGDMP-test")
    with pytest.raises(ValueError):
        service.validate(bad)


@pytest.mark.parametrize("name", ReportService.REPORTS)
@pytest.mark.parametrize("format", ["PDF", "Excel"])
def test_all_report_routes(db, tmp_path, name, format):
    from services.contribution_service import ContributionService
    context = service_context(db)
    member = FamilyService(*context).create(first_name="Report", last_name="Coverage", sex="MALE")
    finance = ContributionService(*context)
    kind = finance.create_type("Reports " + str(member["id"]), "ANNUAL")
    period = finance.create_period(kind["id"], "Report period", "10")
    finance.assign_members(period["id"], [member["id"]])
    path = ReportService(*context, tmp_path).export(name, format, member_id=member["id"], period_id=period["id"])
    assert Path(path).stat().st_size > 0
