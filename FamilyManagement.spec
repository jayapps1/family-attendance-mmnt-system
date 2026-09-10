# Build with: .venv\Scripts\python.exe -m PyInstaller FamilyManagement.spec
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules
root = Path(SPECPATH)
datas = [(str(root / "alembic.ini"), ".")]
datas += [(str(p), str(p.parent.relative_to(root))) for p in (root / "migrations").rglob("*")
          if p.is_file() and p.suffix in {".py", ".mako"} and "__pycache__" not in p.parts]
a = Analysis([str(root / "main.py")], pathex=[str(root)], binaries=[], datas=datas,
    hiddenimports=collect_submodules("sqlalchemy.dialects.postgresql") + collect_submodules("psycopg_binary"),
    hookspath=[], runtime_hooks=[], excludes=["pytest", "matplotlib", "IPython"], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="FamilyManagement",
          debug=False, bootloader_ignore_signals=False, strip=False, upx=False, console=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="FamilyManagement")
