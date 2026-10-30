"""Builds dist/SiRAT.exe, a single file that runs on its own: uv run python build_exe.py"""

from pathlib import Path

import PyInstaller.__main__

ROOT = Path(__file__).resolve().parent


def main() -> None:
    PyInstaller.__main__.run([str(ROOT / "packaging" / "sirat.spec"), "--noconfirm", "--clean",
                              "--distpath", str(ROOT / "dist"), "--workpath", str(ROOT / "build")])
    exe = ROOT / "dist" / "SiRAT.exe"
    print(f"Built {exe} ({exe.stat().st_size / 1e6:.0f} MB)")


if __name__ == "__main__":
    main()
