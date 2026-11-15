"""The generated Station API reference and JSON Schema match the code (scripts/api/build.py).

If this fails, the protocol (src/station_protocol) changed: run `uv run python scripts/api/build.py` and commit the two files, so the backend
works from what the frontend actually sends.
"""

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _build_module():
    spec = importlib.util.spec_from_file_location("api_build", ROOT / "scripts" / "api" / "build.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_the_reference_and_schema_are_up_to_date():
    build = _build_module()
    schema_text, reference_text = build.build()
    assert build.SCHEMA.read_text(encoding="utf-8") == schema_text, "station_api.schema.json is stale"
    assert build.REFERENCE.read_text(encoding="utf-8") == reference_text, "STATION_API_REFERENCE.md is stale"


def test_the_schema_covers_every_method_and_event():
    from station_protocol.catalog import EVENTS, METHODS
    schema = json.loads((ROOT / "docs" / "station_api.schema.json").read_text(encoding="utf-8"))
    assert set(schema["methods"]) == {m.wire for m in METHODS}
    assert set(schema["events"]) == {e.name for e in EVENTS}
    assert all(m["params"].get("additionalProperties") is False for m in schema["methods"].values())
