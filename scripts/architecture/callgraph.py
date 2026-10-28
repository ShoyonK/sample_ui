"""Which station API methods each ViewModel can trigger, following real calls:
VM slot -> self._dep.method() -> ... -> self._gateway.<port method> -> API name ("registers.read").

compute() -> (ViewModel -> endpoints, gateway method -> API name, service -> endpoints).
"""

import ast
import json
import re
from collections import defaultdict
from pathlib import Path

SRC = Path("src/sirat_ui")

# ---- gateway method -> API name, from the fake (which names every call it answers)
api_name = {}
for f in ("gateway/fake/fake_station.py", "gateway/fake/advanced.py"):
    tree = ast.parse((SRC / f).read_text(encoding="utf-8"))
    for fn in ast.walk(tree):
        if isinstance(fn, ast.FunctionDef):
            for c in ast.walk(fn):
                if (isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)
                        and c.func.attr in ("_respond", "_instrument_call") and c.args
                        and isinstance(c.args[0], ast.Constant) and isinstance(c.args[0].value, str)):
                    api_name.setdefault(fn.name, c.args[0].value)

# ---- every class: constructor deps (attr -> type name) and method -> calls
classes = {}   # name -> {"deps": {attr: Type}, "methods": {name: set(("self"|attr, method))}, "file": rel}
for path in SRC.rglob("*.py"):
    if "fake" in path.parts or "__pycache__" in path.parts:
        continue
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for cls in [n for n in tree.body if isinstance(n, ast.ClassDef)]:
        init = next((n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "__init__"), None)
        param_types = {}
        if init:
            for a in init.args.args + init.args.kwonlyargs:
                if a.annotation is not None:
                    t = ast.unparse(a.annotation).strip("'\"")
                    t = re.sub(r"Optional\[(.+)\]", r"\1", t)
                    param_types[a.arg] = t
        deps = {}
        if init:
            for st in ast.walk(init):
                if (isinstance(st, ast.Assign) and isinstance(st.targets[0], ast.Attribute)
                        and isinstance(st.targets[0].value, ast.Name) and st.targets[0].value.id == "self"
                        and isinstance(st.value, ast.Name) and st.value.id in param_types):
                    deps[st.targets[0].attr] = param_types[st.value.id]
        methods = {}
        for fn in [n for n in cls.body if isinstance(n, ast.FunctionDef)]:
            calls = set()
            for c in ast.walk(fn):
                if isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute):
                    v = c.func.value
                    if isinstance(v, ast.Name) and v.id == "self":
                        calls.add(("self", c.func.attr))
                    elif (isinstance(v, ast.Attribute) and isinstance(v.value, ast.Name) and v.value.id == "self"):
                        calls.add((v.attr, c.func.attr))
                    elif isinstance(v, ast.Name) and v.id in param_types:   # gateway.x() used in __init__
                        calls.add(("@" + v.id, c.func.attr))
            # lambdas / bound methods passed around: self._dep.method referenced without a call
            for a in ast.walk(fn):
                if (isinstance(a, ast.Attribute) and isinstance(a.value, ast.Attribute)
                        and isinstance(a.value.value, ast.Name) and a.value.value.id == "self"):
                    calls.add((a.value.attr, a.attr))
                if isinstance(a, ast.Attribute) and isinstance(a.value, ast.Name) and a.value.id == "self":
                    calls.add(("self", a.attr))
            methods[fn.name] = calls
        classes[cls.name] = {"deps": deps, "methods": methods, "params": param_types,
                             "file": path.relative_to(SRC).as_posix()}

PORTS = {"StationGateway", "SystemPort", "DutPort", "RfPort", "RegistersPort", "ActivityPort", "AutomationPort",
         "InstrumentsPort", "MemoryPort", "AdvancedPort", "ConnectionGateway", "EventSource"}


def endpoints_of(cls_name, method, seen=None):
    seen = seen or set()
    key = (cls_name, method)
    if key in seen or cls_name not in classes:
        return set()
    seen.add(key)
    info = classes[cls_name]
    out = set()
    for target, m in info["methods"].get(method, ()):
        if target == "self":
            out |= endpoints_of(cls_name, m, seen)
            continue
        t = info["deps"].get(target) or (info["params"].get(target[1:]) if target.startswith("@") else None)
        if t is None:
            continue
        if t in PORTS:
            if m in api_name:
                out.add(api_name[m])
        else:
            out |= endpoints_of(t, m, seen)
    return out


def compute():
    vms, services = {}, {}
    for name, info in classes.items():
        eps = set()
        for m in info["methods"]:
            eps |= endpoints_of(name, m)
        if not eps:
            continue
        if name.endswith("ViewModel") and info["file"].startswith("domains"):
            vms[name] = sorted(eps)
        elif not name.endswith("ViewModel"):
            services[name] = sorted(eps)
    return vms, api_name, services


if __name__ == "__main__":
    v, a, s = compute()
    print(json.dumps({"vms": v, "api": a, "services": s}, indent=1))

# Endpoints services call on their own (startup, timers, state changes), and when. The trace above only
# follows ViewModel slots, so these are listed by hand; build.py and backend_doc.py both use them.
SERVICE_CALLS = {
    "sys.hello": ("ConnectionService", "startup"), "sys.subscribe": ("ConnectionService", "startup"),
    "sys.status": ("ConnectionService", "startup, after connect"),
    "registers.watch": ("WatchService, DataLoggerService", "Live / Record"),
    "registers.unwatch": ("WatchService, DataLoggerService", "Pause / Stop"),
    "rf.paths": ("RfSwitchService", "RF switch connects"),
    "instruments.eca.sources": ("EcaService", "ECA connects"),
    "rf.prs_signals": ("PrsService", "DUT connects"),
    "dut.info": ("SystemInfoViewModel via ConnectionService", "DUT connects"),
}
