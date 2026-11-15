"""Safe evaluation of field formulas (req §11). Only `x`, numbers, arithmetic and a few math functions."""

from __future__ import annotations

import ast
import math
from typing import Any, Callable, Dict, Optional

# Exactly the names in the original safe_dict (req 11), so formulas work in the old and new GUIs.
_FUNCTIONS: Dict[str, Callable[..., Any]] = {
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "pow": pow,
}
_CONSTANTS = {"pi": math.pi, "e": math.e}

_BINARY: Dict[type, Callable[[Any, Any], Any]] = {
    ast.Add: lambda a, b: a + b,
    ast.Sub: lambda a, b: a - b,
    ast.Mult: lambda a, b: a * b,
    ast.Div: lambda a, b: a / b,
    ast.FloorDiv: lambda a, b: a // b,
    ast.Mod: lambda a, b: a % b,
    ast.Pow: lambda a, b: a ** b,
    ast.BitAnd: lambda a, b: int(a) & int(b),
    ast.BitOr: lambda a, b: int(a) | int(b),
    ast.BitXor: lambda a, b: int(a) ^ int(b),
    ast.LShift: lambda a, b: int(a) << int(b),
    ast.RShift: lambda a, b: int(a) >> int(b),
}
_UNARY: Dict[type, Callable[[Any], Any]] = {
    ast.USub: lambda a: -a,
    ast.UAdd: lambda a: +a,
    ast.Invert: lambda a: ~int(a),
}
_MAX_EXPONENT = 256


class FormulaError(ValueError):
    """A formula that can't be parsed or evaluated; the message is shown to the user."""


def _parse(expr: str) -> ast.Expression:
    if not expr or not expr.strip():
        raise FormulaError("Enter a formula that uses x")
    try:
        return ast.parse(expr.strip(), mode="eval")
    except SyntaxError as exc:
        raise FormulaError(f"That isn't a valid expression ({exc.msg})") from None


def _eval(node: ast.AST, x: float) -> Any:
    # Recursive on purpose: a formula is a tree, and one case per node type reads far better than a loop with its
    # own stack. Real formulas are a few levels deep; one nested too deep is caught in evaluate() as "too long".
    if isinstance(node, ast.Expression):
        return _eval(node.body, x)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
        return node.value
    if isinstance(node, ast.Name):
        if node.id == "x":
            return x
        if node.id in _CONSTANTS:
            return _CONSTANTS[node.id]
        raise FormulaError(f"Unknown name '{node.id}'. Use x, pi, e, abs, round, min, max or pow")
    if isinstance(node, ast.BinOp) and type(node.op) in _BINARY:
        left, right = _eval(node.left, x), _eval(node.right, x)
        if isinstance(node.op, (ast.Pow, ast.LShift)) and abs(right) > _MAX_EXPONENT:
            raise FormulaError("Exponent is too large")
        return _BINARY[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
        return _UNARY[type(node.op)](_eval(node.operand, x))
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _FUNCTIONS and not node.keywords:
        args = [_eval(a, x) for a in node.args]
        if node.func.id == "pow" and len(args) >= 2 and abs(args[1]) > _MAX_EXPONENT:
            raise FormulaError("Exponent is too large")
        return _FUNCTIONS[node.func.id](*args)
    raise FormulaError(f"'{type(node).__name__}' isn't allowed in a formula")


def evaluate(expr: str, x: float) -> float:
    """Evaluates a field formula for one raw value.

    Raises:
        FormulaError: The formula is invalid or fails for this x (division by zero, too large, ...).
    """
    try:
        return float(_eval(_parse(expr), x))
    except FormulaError:   # already user-facing; FormulaError is a ValueError, so it must pass before the next line
        raise
    except (ArithmeticError, ValueError, TypeError) as exc:
        raise FormulaError(f"Couldn't evaluate: {exc}") from None
    except (RecursionError, MemoryError):   # nested past what the parser or _eval can walk, e.g. x+x+... 1000 times
        raise FormulaError("That formula is too long") from None


def validate(expr: str) -> Optional[str]:
    """Returns an error message, or None when the formula is usable."""
    try:
        evaluate(expr, 1)
        return None
    except FormulaError as exc:
        return str(exc)


def format_result(value: float, unit: str = "") -> str:
    """Req 11: 3 decimals when |value| >= 1, otherwise 6 ("2440.125 MHz")."""
    text = f"{value:.3f}" if abs(value) >= 1 else f"{value:.6f}"
    return f"{text} {unit}".strip()
