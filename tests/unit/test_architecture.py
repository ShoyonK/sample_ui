"""Architecture rules, checked statically so they can't erode."""

import ast
import re
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[2] / "src" / "sirat_ui"
FORBIDDEN_EVERYWHERE = ("pandas", "nidaqmx", "pyvisa", "BenchUtils", "SwitchUtils", "dut_control")


def _imports(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name
        elif isinstance(node, ast.ImportFrom) and node.module:
            yield node.module


def _py_files(sub: str):
    return sorted((PACKAGE / sub).rglob("*.py"))


def test_core_has_no_qt():
    offenders = [(p.name, m) for p in _py_files("core") for m in _imports(p) if m.startswith("PyQt5")]
    assert offenders == []


MODEL_DEPENDENCIES = ("sirat_ui.models", "sirat_ui.core.bits", "sirat_ui.core.formatting", "sirat_ui.gateway.errors")


def test_models_import_only_the_standard_library_and_each_other():
    """Any layer can use models/ without import cycles, so models/ must not reach back up into them."""
    def imported(path: Path):   # "from sirat_ui.core import bits" counts as sirat_ui.core.bits
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                yield from (a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                yield from (f"{node.module}.{a.name}" for a in node.names)

    offenders = [(p.name, m) for p in _py_files("models") for m in imported(p)
                 if m.startswith(("sirat_ui", "PyQt5", "pydantic")) and not m.startswith(MODEL_DEPENDENCIES)]
    assert offenders == []


def test_only_the_composition_root_and_backends_see_the_whole_station():
    """Services depend on the area interface they use (gateway/port.py), so a change stays in its area."""
    offenders = [p.relative_to(PACKAGE).as_posix() for p in PACKAGE.rglob("*.py")
                 if "StationGateway" in p.read_text(encoding="utf-8")
                 and p.relative_to(PACKAGE).parts[0] not in ("app", "gateway")]
    assert offenders == []


def test_one_way_to_declare_a_qt_property():
    """qprop(...) for a stored value, @pyqtProperty for a computed one; no lambda properties."""
    helper = PACKAGE / "shared" / "viewmodel.py"   # qprop itself
    offenders = [f"{p.relative_to(PACKAGE).as_posix()}:{n}" for p in PACKAGE.rglob("*.py") if p != helper
                 for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1)
                 if re.search(r"pyqtProperty\(.*\blambda\s+self", line)]
    assert offenders == []


def test_viewmodels_reach_the_station_only_through_services():
    """Errors have one owner: services make station calls and report unexpected failures (ErrorPresenter);
    ViewModels show results inline or toast input and file problems, and never call the gateway."""
    offenders = [(p.name, m) for p in PACKAGE.rglob("*viewmodel*.py") for m in _imports(p)
                 if m.startswith(("sirat_ui.gateway.port", "sirat_ui.shared.error_presenter"))]
    assert offenders == []


def test_services_state_stores_and_gateway_have_no_qt():
    files = _py_files("state") + _py_files("stores") + _py_files("gateway") + [
        p for p in _py_files("domains") if p.name in ("service.py", "catalog.py")]
    offenders = [(p.name, m) for p in files for m in _imports(p) if m.startswith("PyQt5")]
    assert offenders == []


def test_frontend_never_imports_hardware_or_test_libraries():
    """API doc: the GUI never imports BenchUtils, SwitchUtils, dut_control, NI drivers or pandas."""
    offenders = [(p.name, m) for p in PACKAGE.rglob("*.py") for m in _imports(p)
                 if m.split(".")[0] in FORBIDDEN_EVERYWHERE]
    assert offenders == []


def test_viewmodels_never_touch_the_gateway_directly():
    vm_files = [p for p in PACKAGE.rglob("*viewmodel*.py")]
    offenders = [(p.name, m) for p in vm_files for m in _imports(p) if m.startswith("sirat_ui.gateway.fake")]
    assert offenders == []


def test_no_python_file_is_huge():
    sizes = {p.relative_to(PACKAGE).as_posix(): len(p.read_text(encoding="utf-8").splitlines())
             for p in PACKAGE.rglob("*.py")}
    assert {k: v for k, v in sizes.items() if v > 600} == {}


# ---- Design Studio rules for .ui.qml forms (docs/FRONTEND_PLAN.md section 5) ---------------

UI_FILES = sorted((PACKAGE / "qml").rglob("*.ui.qml"))
INTERACTIVE = ("AppButton", "IconButton", "AppTextField", "SegmentedControl", "AppCheckBox", "AppComboBox")


def test_there_are_forms_to_check():
    assert len(UI_FILES) >= 15


def test_forms_have_no_logic():
    problems = []
    for path in UI_FILES:
        text = re.sub(r"//.*", "", path.read_text(encoding="utf-8"))
        for pattern, why in ((r"\bfunction\b", "function"), (r"\bon[A-Z]\w*\s*:", "signal handler"),
                             (r"\bConnections\b", "Connections"), (r"\bapp\.", "ViewModel reference"),
                             (r"\bvm\.", "ViewModel reference"), (r"=>", "arrow function")):
            if re.search(pattern, text):
                problems.append(f"{path.name}: {why}")
    assert problems == []


def test_interactive_elements_in_forms_have_object_names():
    problems = []
    for path in UI_FILES:
        text = path.read_text(encoding="utf-8")
        for match in re.finditer(r"\b(%s)\s*\{" % "|".join(INTERACTIVE), text):
            depth, i = 1, match.end()
            while depth and i < len(text):
                depth += {"{": 1, "}": -1}.get(text[i], 0)
                i += 1
            if "objectName" not in text[match.end():i]:
                line = text[: match.start()].count("\n") + 1
                problems.append(f"{path.name}:{line} {match.group(1)}")
    assert problems == []


def test_every_form_has_a_wrapper():
    missing = [p.name for p in UI_FILES if not p.with_name(p.name.replace("Form.ui.qml", ".qml")).exists()]
    assert missing == []


def test_font_sizes_come_from_the_theme():
    """All text sizes go through Theme tokens so Theme.fontScale controls them in one place."""
    offenders = []
    for path in (PACKAGE / "qml").rglob("*.qml"):
        if path.parent.name == "theme":
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if re.search(r"pixelSize:\s*\d", line):
                offenders.append(f"{path.name}:{number}")
    assert offenders == []
