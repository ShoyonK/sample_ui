"""Shared data types: the vocabulary the layers pass to each other.

Each module groups one area. These modules import only the standard library, other models,
and stdlib-only helpers (core.bits, core.formatting, gateway.errors), so any layer can use them
without import cycles. tests/unit/test_architecture.py checks this.
"""
