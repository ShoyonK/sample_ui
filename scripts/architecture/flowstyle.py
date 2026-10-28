"""Turns Mermaid class diagrams into flowcharts that look like class diagrams, and gives every flowchart
right-angled arrows.

Mermaid draws class-diagram arrows as curves and has no setting to change that; flowcharts accept a curve.
A class becomes a node: bold name, an optional «stereotype», a divider, then its members, left-aligned.
Name-only classes (stubs) get a dashed border.

Curves, measured over every arrow in ARCHITECTURE.md: `step` bends at the middle of each routing segment
(2.7 bends per arrow); `stepAfter` turns once per segment and ends vertically, so top-down diagrams use it
(1.5 bends, arrowheads point down); `stepBefore` ends horizontally, so left-to-right diagrams use it.
"""

import re


def curve_line(direction: str) -> str:
    curve = "stepBefore" if direction in ("LR", "RL") else "stepAfter"
    return '%%{init: {"flowchart": {"curve": "' + curve + '"}}}%%'
STYLES = ["    classDef box text-align:left,fill:#f8f8ff,stroke:#6a6ab0,color:#1c1c1c",
          "    classDef stub fill:#ffffff,stroke:#6a6ab0,stroke-dasharray:4 3,color:#1c1c1c"]
RELATION = re.compile(r"^\s*(\w+)\s*(<\|--|<\|\.\.|\*--|o--|-->|\.\.>|--|\.\.)\s*(\w+)\s*(?::\s*(.+))?\s*$")


def _text(s: str) -> str:
    s = re.sub(r"~([^~]*)~", r"[\1]", s)          # Call~Foo~ -> Call[Foo]
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "#quot;")


def _edge(a: str, op: str, b: str, label: str) -> str:
    """Labels are quoted, so parentheses and colons in them (with_children(children)) parse."""
    label = _text(label or "")
    if op == "<|--":    # b extends a
        return f'    {b} -->|"extends"| {a}'
    if op == "<|..":    # b implements a
        return f'    {b} -.->|"implements"| {a}'
    if op in ("*--", "o--"):
        word = "owns" if op == "*--" else "has"
        return f'    {a} -->|"{word} {label}"| {b}' if label else f'    {a} -->|"{word}"| {b}'
    if op == "..>":
        return f'    {a} -.->|"{label}"| {b}' if label else f"    {a} -.-> {b}"
    if op in ("--", ".."):
        return f"    {a} --- {b}"
    return f'    {a} -->|"{label}"| {b}' if label else f"    {a} --> {b}"


def class_to_flowchart(code: str) -> str:
    lines = code.splitlines()
    direction = "TB"
    nodes, edges, current, members = [], [], None, []
    stereotype = ""
    wrap = 0          # "%% wrap N": ViewModel boxes in rows of N instead of one long row
    for line in lines:
        s = line.strip()
        m = re.match(r"^%%\s*wrap\s+(\d+)$", s)
        if m:
            wrap = int(m.group(1))
            continue
        if not s or s == "classDiagram" or s.startswith("%%"):
            continue
        if s.startswith("direction "):
            direction = s.split()[1]
            continue
        if current is not None:
            if s == "}":
                head = f"<b>{_text(current)}</b>" + (f"<br/><i>«{_text(stereotype)}»</i>" if stereotype else "")
                body = "<br/>".join(_text(m) for m in members)
                label = head + (f"<hr/>{body}" if body else "")
                nodes.append(f'    {current}["{label}"]:::box')
                current, members, stereotype = None, [], ""
            elif s.startswith("<<") and s.endswith(">>"):
                stereotype = s[2:-2]
            else:
                members.append(s)
            continue
        m = re.match(r"^class\s+(\w+)\s*\{$", s)
        if m:
            current = m.group(1)
            continue
        m = re.match(r"^class\s+(\w+)$", s)
        if m:
            nodes.append(f'    {m.group(1)}["<b>{_text(m.group(1))}</b>"]:::stub')
            continue
        m = RELATION.match(s)
        if m:
            edges.append(_edge(*m.groups()))
            continue
        raise ValueError(f"can't convert class-diagram line: {s}")
    rows = []
    if wrap:   # invisible links push each box one rank below the box `wrap` places before it
        vms = [n.split("[", 1)[0].strip() for n in nodes if n.split("[", 1)[0].strip().endswith("ViewModel")]
        rows = [f"    {vms[i - wrap]} ~~~ {vms[i]}" for i in range(wrap, len(vms))]
    return "\n".join([curve_line(direction), f"flowchart {direction}"] + STYLES + nodes + edges + rows)


def restyle(markdown: str) -> str:
    """Every ```mermaid block: class diagrams -> flowcharts; flowcharts get right-angled arrows."""
    def one(m: re.Match) -> str:
        code = m.group(1)
        first = code.lstrip().splitlines()[0] if code.strip() else ""
        if first.startswith("classDiagram"):
            code = class_to_flowchart(code) + "\n"
        elif first.startswith("flowchart") and "%%{init" not in code:
            code = curve_line(first.split()[1] if len(first.split()) > 1 else "TB") + "\n" + code
        return "```mermaid\n" + code + "```"
    return re.sub(r"```mermaid\n(.*?)```", one, markdown, flags=re.S)
