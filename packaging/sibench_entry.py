"""PyInstaller entry point (a plain script importing the package, so absolute imports work when frozen)."""

import sys

from sibench_ui.app.launch import main

if __name__ == "__main__":
    sys.exit(main())
