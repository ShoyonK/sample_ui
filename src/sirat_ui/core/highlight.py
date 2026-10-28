"""Python syntax highlighting to Qt rich text (req 13 View dialog, req 16 code dialog).

Colors follow req 16: keywords blue and bold, strings orange, comments green, functions purple,
numbers cyan. There is one palette per theme so the code stays readable in dark mode.
"""

from __future__ import annotations

import html
import io
import keyword
import token
import tokenize
from typing import Dict, List, Tuple

LIGHT = {"keyword": "#1F4FD8", "string": "#B4561D", "comment": "#2B8A3E", "function": "#7048E8",
         "number": "#0B7285", "text": "#1C1C1C"}
DARK = {"keyword": "#569CD6", "string": "#CE9178", "comment": "#6A9955", "function": "#C586C0",
        "number": "#4EC9B0", "text": "#D8D8D8"}


def _classify(tokens: List[tokenize.TokenInfo], i: int) -> str:
    tok = tokens[i]
    if tok.type == token.COMMENT:
        return "comment"
    if tok.type == token.STRING:
        return "string"
    if tok.type == token.NUMBER:
        return "number"
    if tok.type == token.NAME:
        if keyword.iskeyword(tok.string) or tok.string in ("True", "False", "None", "self"):
            return "keyword"
        following = next((t for t in tokens[i + 1:] if t.type not in (token.NL, token.NEWLINE)), None)
        if following is not None and following.string == "(":
            return "function"
    return "text"


def _spans(code: str) -> List[Tuple[str, str]]:
    """(kind, text) pieces covering the whole source, gaps included, so whitespace is preserved."""
    lines = code.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))

    def pos(row: int, col: int) -> int:
        return offsets[row - 1] + col if row - 1 < len(offsets) else len(code)

    tokens = list(tokenize.generate_tokens(io.StringIO(code).readline))
    spans: List[Tuple[str, str]] = []
    cursor = 0
    for i, tok in enumerate(tokens):
        if tok.type in (token.ENDMARKER, token.INDENT, token.DEDENT):
            continue
        start, end = pos(*tok.start), pos(*tok.end)
        if start > cursor:
            spans.append(("text", code[cursor:start]))
        spans.append((_classify(tokens, i), code[start:end]))
        cursor = max(cursor, end)
    if cursor < len(code):
        spans.append(("text", code[cursor:]))
    return spans


def highlight_python(code: str, dark: bool = False) -> str:
    palette: Dict[str, str] = DARK if dark else LIGHT
    try:
        spans = _spans(code)
    except (tokenize.TokenError, IndentationError, SyntaxError):
        spans = [("text", code)]
    parts = []
    for kind, text in spans:
        escaped = html.escape(text)
        style = f"color:{palette[kind]};" + ("font-weight:bold;" if kind == "keyword" else "")
        parts.append(f'<span style="{style}">{escaped}</span>')
    return '<pre style="font-family:Consolas,monospace;margin:0;">' + "".join(parts) + "</pre>"
