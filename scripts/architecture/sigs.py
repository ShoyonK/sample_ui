"""Prints mermaid classDiagram member lines for classes: public methods with signatures, Qt slots, properties.

Used by build.py. As a script: sigs.py module.path:ClassName ...   (run from the repo root)
"""

import ast
import re
import sys
from pathlib import Path

SRC = Path("src")


def simplify(t: str) -> str:
    """Mermaid-safe types: Optional[X] -> X?, one generic level with ~ ~, deeper levels dropped."""
    if not t:
        return ""
    t = t.replace("'", "").replace('"', "").replace(" ", "")

    def parse(s, i=0):
        """-> ((name, [args]), next index)"""
        j = i
        while j < len(s) and s[j] not in "[],":
            j += 1
        name, args = s[i:j], []
        if j < len(s) and s[j] == "[":
            j += 1
            while True:
                arg, j = parse(s, j)
                args.append(arg)
                if s[j] == ",":
                    j += 1
                    continue
                j += 1   # ]
                break
        return (name, args), j

    def inner(node):
        name, args = node
        if name == "Optional" and len(args) == 1:
            return inner(args[0]) + "?"
        if name == "Callable" or not args:
            return name
        return f"{name} of {','.join(inner(a) for a in args)}"

    def outer(node):
        name, args = node
        if name == "Optional" and len(args) == 1:
            return outer(args[0]) + "?"
        if name == "Callable" or not args:
            return name
        return f"{name}~{','.join(inner(a) for a in args)}~"

    return outer(parse(t)[0])


def default_text(node) -> str:
    s = ast.unparse(node)
    return s if len(s) <= 12 else "…"


def signature(fn: ast.FunctionDef) -> str:
    args = fn.args
    params = []
    positional = args.posonlyargs + args.args
    defaults = [None] * (len(positional) - len(args.defaults)) + list(args.defaults)
    for a, d in zip(positional, defaults):
        if a.arg in ("self", "cls", "parent"):
            continue
        ann = simplify(ast.unparse(a.annotation)) if a.annotation else ""
        params.append(f"{a.arg}{': ' + ann if ann else ''}{'=' + default_text(d) if d is not None else ''}")
    for a, d in zip(args.kwonlyargs, args.kw_defaults):
        ann = simplify(ast.unparse(a.annotation)) if a.annotation else ""
        params.append(f"{a.arg}{': ' + ann if ann else ''}{'=' + default_text(d) if d is not None else ''}")
    ret = simplify(ast.unparse(fn.returns)) if fn.returns else ""
    if ret == "None":
        ret = ""
    return f"{fn.name}({', '.join(params)}) {ret}".rstrip()


def members(module: str, cls_name: str, include_private: bool = False):
    path = SRC / (module.replace(".", "/") + ".py")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    cls = next(n for n in ast.walk(tree) if isinstance(n, ast.ClassDef) and n.name == cls_name)
    out = []
    for n in cls.body:
        if isinstance(n, ast.FunctionDef):
            decos = [ast.unparse(d) for d in n.decorator_list]
            is_prop = any(d.startswith("pyqtProperty") or d == "property" for d in decos)
            if n.name.startswith("_") and n.name != "__init__":
                if not include_private:
                    continue
            if n.name == "__init__":
                continue
            if is_prop:
                ret = simplify(ast.unparse(n.returns)) if n.returns else ""
                out.append(f"+{n.name} {ret}".rstrip())
            else:
                out.append(f"+{signature(n)}")
        elif isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name):
            name = n.targets[0].id
            src = ast.unparse(n.value)
            if src.startswith("qprop(") or src.startswith("pyqtProperty("):
                typ = ast.unparse(n.value.args[0]).strip("'\"")
                out.append(f"+{name} {simplify(typ)}")
        elif isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name) and not n.target.id.startswith("_"):
            out.append(f"+{n.target.id} {simplify(ast.unparse(n.annotation))}")
    return out


def ctor(module: str, cls_name: str) -> str:
    path = SRC / (module.replace(".", "/") + ".py")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    cls = next(n for n in ast.walk(tree) if isinstance(n, ast.ClassDef) and n.name == cls_name)
    init = next((n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "__init__"), None)
    return signature(init).replace("__init__", cls_name) if init else cls_name + "()"


def main() -> None:
    for spec in sys.argv[1:]:
        mod, cls = spec.split(":")
        ms = members(mod, cls)
        if cls.endswith("ViewModel"):   # slots only, plus how many bindable properties
            props = [m for m in ms if "(" not in m]
            ms = [m for m in ms if "(" in m] + ([f"+{len(props)} bindable properties"] if props else [])
        print(f"    class {cls} {{")
        for m in ms:
            print("        " + m)
        print("    }")
        print(f"    %% {ctor(mod, cls)}")


if __name__ == "__main__":
    main()
