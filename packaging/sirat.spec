# PyInstaller spec for SiRAT. Run it with build_exe.py.
#
# Startup depends on bundle size, so only the Qt the app uses goes in. A new QML import needs adding to KEEP below.

import re
from pathlib import Path

ROOT = Path(SPECPATH).parent
SRC = ROOT / "src"

# Paths inside PyQt5/Qt5 that ship; everything else from Qt is dropped
KEEP = re.compile(r"""^(
    bin/(Qt5(Core|Gui|Widgets|Network|Qml|QmlModels|QmlWorkerScript|Quick|QuickControls2|QuickTemplates2)
         |libEGL|libGLESv2|d3dcompiler_47|MSVCP140|VCRUNTIME140)
  | plugins/(platforms/qwindows|styles/)
  | qml/(QtQml|QtQuick\.2|QtQuick/(Controls\.2|Templates\.2|Layouts|Window\.2))/
)""", re.VERBOSE | re.IGNORECASE)
DROPPED_STYLES = re.compile(r"Controls\.2/(Fusion|Imagine|Material|Universal|designer)/", re.IGNORECASE)
DROPPED_FILES = re.compile(r"^(hypothesis|_ssl|_hashlib|libssl|libcrypto|_lzma|_bz2)", re.IGNORECASE)
QT_PREFIX = "pyqt5/qt5/"


def wanted(entry):
    name = entry[0].replace("\\", "/")
    if name.lower().startswith(QT_PREFIX):
        qt_path = name[len(QT_PREFIX):]
        return bool(KEEP.match(qt_path)) and not DROPPED_STYLES.search(qt_path)
    return not DROPPED_FILES.match(name)


a = Analysis(
    [str(ROOT / "packaging" / "sirat_entry.py")],
    pathex=[str(SRC)],
    datas=[(str(SRC / "sirat_ui" / "qml"), "sirat_ui/qml"), (str(ROOT / "docs" / "samples"), "samples")],
    # QML files import these at runtime; PyInstaller can't see that from Python imports alone.
    hiddenimports=["PyQt5.QtQuick", "PyQt5.QtQml", "PyQt5.sip"],
    excludes=["tkinter", "pandas", "numpy", "unittest", "pydoc", "pytest", "hypothesis", "ssl", "asyncio",
              "PyQt5.QtQuickWidgets"],
)
a.binaries = [b for b in a.binaries if wanted(b)]
a.datas = [d for d in a.datas if wanted(d)]
pyz = PYZ(a.pure)

exe = EXE(pyz, a.scripts, a.binaries, a.datas, name="SiRAT", icon=str(ROOT / "packaging" / "sirat.ico"),
          console=False, upx=False)
