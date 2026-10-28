"""The whole package type-checks with pyrefly, so typed boundaries (gateway port, models, services) stay typed.

Config: [tool.pyrefly] in pyproject.toml. Run it yourself with `uv run pyrefly check`.
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_pyrefly_finds_no_type_errors():
    result = subprocess.run([sys.executable, "-m", "pyrefly", "check", "--output-format", "min-text"],
                            cwd=ROOT, capture_output=True, text=True, timeout=300)
    errors = [line for line in result.stdout.splitlines() + result.stderr.splitlines() if line.startswith("ERROR")]
    assert errors == [], "pyrefly found type errors:\n" + "\n".join(errors)
    assert result.returncode == 0, result.stdout + result.stderr
