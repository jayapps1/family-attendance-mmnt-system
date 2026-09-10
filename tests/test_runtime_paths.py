from pathlib import Path
import sys
from utils.runtime_paths import data_root, resource_root


def test_frozen_data_does_not_use_bundle_or_working_directory(monkeypatch, tmp_path):
    monkeypatch.delenv("FAMILY_APP_DATA_DIR", raising=False)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path / "bundle"), raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "FamilyManagement.exe"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))
    assert data_root() == tmp_path / "local" / "FamilyManagement"
    assert resource_root() == tmp_path / "bundle"
    (tmp_path / "app-data-dir.txt").write_text(str(tmp_path / "existing"))
    assert data_root() == tmp_path / "existing"
    monkeypatch.setenv("FAMILY_APP_DATA_DIR", str(tmp_path / "override"))
    assert data_root() == tmp_path / "override"
