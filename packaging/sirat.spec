# PyInstaller spec for SiRAT.
#
#   uv run pyinstaller packaging/sirat.spec --noconfirm
#
# Produces dist/SiRAT/SiRAT.exe (one-folder build: fast startup, easy to inspect).
# For a single file, set ONEFILE = True (slower to start: it unpacks to a temp folder each launch).

from pathlib import Path

ONEFILE = False

ROOT = Path(SPECPATH).parent
SRC = ROOT / "src"
QML = SRC / "sirat_ui" / "qml"
ICON = ROOT / "packaging" / "sirat.ico"

a = Analysis(
    [str(ROOT / "packaging" / "sirat_entry.py")],
    pathex=[str(SRC)],
    datas=[(str(QML), "sirat_ui/qml")],
    # QML files import these at runtime; PyInstaller can't see that from Python imports alone.
    hiddenimports=["PyQt5.QtQuick", "PyQt5.QtQml", "PyQt5.QtQuickWidgets", "PyQt5.sip"],
    excludes=["tkinter", "pandas", "numpy", "PyQt5.QtWebEngineCore", "PyQt5.QtWebEngineWidgets",
              "PyQt5.QtWebEngine", "PyQt5.Qt3DCore", "PyQt5.QtBluetooth", "PyQt5.QtNfc",
              "PyQt5.QtMultimedia", "PyQt5.QtLocation", "PyQt5.QtPositioning", "PyQt5.QtSensors"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe_options = dict(
    name="SiRAT",
    icon=str(ICON) if ICON.exists() else None,
    console=False,
    upx=False,
    version=None,
)

if ONEFILE:
    exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], **exe_options)
else:
    exe = EXE(pyz, a.scripts, [], exclude_binaries=True, **exe_options)
    coll = COLLECT(exe, a.binaries, a.datas, upx=False, name="SiRAT")
