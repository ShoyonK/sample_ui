"""Live Python highlighting for editable QML text (req 15 "Syntax Highlighting").

Same colors as the read-only code views (core/highlight.py): keywords blue and bold, strings orange,
comments green, function calls purple, numbers cyan. Triple-quoted strings may span lines.
"""

from __future__ import annotations

import keyword
from typing import Dict, List, Optional, Tuple

from PyQt5.QtCore import QObject, QRegularExpression
from PyQt5.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat, QTextDocument

from sirat_ui.core.highlight import DARK, LIGHT

_WORDS = sorted(set(keyword.kwlist) | {"True", "False", "None", "self"})
_RULES: List[Tuple[str, str]] = [
    ("number", r"\b(0[xX][0-9A-Fa-f_]+|\d[\d_]*\.?\d*([eE][-+]?\d+)?)\b"),
    ("function", r"\b[A-Za-z_]\w*(?=\s*\()"),
    ("keyword", r"\b(" + "|".join(_WORDS) + r")\b"),
    ("string", r"[rbfuRBFU]{0,2}(\"([^\"\\]|\\.)*\"|'([^'\\]|\\.)*')"),
    ("comment", r"#[^\n]*"),
]
_TRIPLE = ('"""', "'''")


class PythonHighlighter(QSyntaxHighlighter):
    def __init__(self, document: QTextDocument, dark: bool = False) -> None:
        super().__init__(document)
        self._rules = [(kind, QRegularExpression(pattern)) for kind, pattern in _RULES]
        self._formats: Dict[str, QTextCharFormat] = {}
        self.set_dark(dark)

    def set_dark(self, dark: bool) -> None:
        palette = DARK if dark else LIGHT
        self._formats = {}
        for kind in ("keyword", "string", "comment", "function", "number"):
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(palette[kind]))
            if kind == "keyword":
                fmt.setFontWeight(QFont.Bold)
            self._formats[kind] = fmt
        self.rehighlight()

    def highlightBlock(self, text: Optional[str]) -> None:  # noqa: N802 (Qt API)
        text = text or ""
        for kind, regex in self._rules:   # later rules win, so strings and comments override the rest
            matches = regex.globalMatch(text)
            while matches.hasNext():
                m = matches.next()
                self.setFormat(m.capturedStart(), m.capturedLength(), self._formats[kind])
        self._triple_quotes(text)

    def _triple_quotes(self, text: str) -> None:
        """Block state: 0 = normal, 1 = inside \"\"\", 2 = inside '''."""
        state, start = self.previousBlockState(), 0
        if state not in (1, 2):
            state = 0
        pos = 0
        while True:
            if state == 0:
                found = [(text.find(q, pos), i + 1) for i, q in enumerate(_TRIPLE) if text.find(q, pos) >= 0]
                if not found:
                    break
                start, state = min(found)
                pos = start + 3
            else:
                end = text.find(_TRIPLE[state - 1], pos)
                if end < 0:
                    self.setFormat(start, len(text) - start, self._formats["string"])
                    break
                self.setFormat(start, end + 3 - start, self._formats["string"])
                pos, state = end + 3, 0
        self.setCurrentBlockState(state)


class HighlighterHost:
    """Keeps one highlighter per document alive (Qt doesn't own it from Python's side)."""

    def __init__(self) -> None:
        self._highlighters: List[PythonHighlighter] = []

    def attach(self, quick_document: QObject, dark: bool) -> None:
        document = quick_document.textDocument() if hasattr(quick_document, "textDocument") else None
        if not isinstance(document, QTextDocument):
            return
        for h in self._highlighters:
            if h.document() is document:
                h.set_dark(dark)
                return
        self._highlighters.append(PythonHighlighter(document, dark))
