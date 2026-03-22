"""
GravLang — Scoped variable environment.

Each Environment has an optional *parent* pointer, enabling nested scopes
for blocks and function calls.
"""

from __future__ import annotations
from errors import GravLangRuntimeError


class Environment:
    """Variable store with lexical scope chain."""

    def __init__(self, parent: Environment | None = None):
        self.parent = parent
        self._store: dict[str, object] = {}

    # ── define a new variable in the current scope ───────────────────

    def set(self, name: str, value: object) -> None:
        """Create (or overwrite) a binding in *this* scope."""
        self._store[name] = value

    # ── look up a variable walking up the scope chain ────────────────

    def get(self, name: str) -> object:
        """Return the value bound to *name*, or raise if undefined."""
        if name in self._store:
            return self._store[name]
        if self.parent is not None:
            return self.parent.get(name)
        raise GravLangRuntimeError(f"Undefined variable: '{name}'")

    # ── re-assign an existing variable (walk up scopes) ──────────────

    def assign(self, name: str, value: object) -> None:
        """Update an existing binding.  Raises if the variable was never declared."""
        if name in self._store:
            self._store[name] = value
            return
        if self.parent is not None:
            self.parent.assign(name, value)
            return
        raise GravLangRuntimeError(f"Cannot assign to undefined variable: '{name}'")

    def __repr__(self) -> str:
        return f"Environment({self._store}, parent={'...' if self.parent else 'None'})"
