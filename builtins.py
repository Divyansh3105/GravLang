"""
GravLang — Built-in functions.

Each built-in is a plain Python callable.  ``register_builtins``
injects them into the global Environment so user code can call them
directly.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from environment import Environment


# ── I/O ──────────────────────────────────────────────────────────────

def _builtin_print(*args):
    """print(value) → outputs to console (or captured output)."""
    print(*args)


def _builtin_input(prompt=""):
    """input(prompt) → reads a line from stdin."""
    return input(prompt)


# ── Introspection ────────────────────────────────────────────────────

def _builtin_len(value):
    """len(string_or_array) → integer length."""
    if isinstance(value, (str, list)):
        return len(value)
    raise TypeError(f"len() expects a string or array, got {type(value).__name__}")


def _builtin_type(value):
    """type(value) → string name of the GravLang type."""
    from gravlang_class import GravLangInstance
    if value is None:
        return "null"
    if isinstance(value, GravLangInstance):
        return value.klass.name
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    return "unknown"


def _builtin_hasAttr(obj, attr_name):
    """hasAttr(obj, name) → true/false whether the attribute exists."""
    from gravlang_class import GravLangInstance
    if not isinstance(obj, GravLangInstance):
        raise TypeError("hasAttr() expects an object instance as first argument")
    return attr_name in obj.fields


# ── Type conversion ──────────────────────────────────────────────────

def _builtin_toInt(value):
    """toInt(value) → convert to int."""
    try:
        return int(value)
    except (ValueError, TypeError):
        raise TypeError(f"Cannot convert {value!r} to int")


def _builtin_toFloat(value):
    """toFloat(value) → convert to float."""
    try:
        return float(value)
    except (ValueError, TypeError):
        raise TypeError(f"Cannot convert {value!r} to float")


def _builtin_toString(value):
    """toString(value) → convert to string."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list):
        parts = []
        for v in value:
            if isinstance(v, str):
                parts.append(f'"{v}"')
            elif isinstance(v, bool):
                parts.append("true" if v else "false")
            elif v is None:
                parts.append("null")
            else:
                parts.append(str(v))
        return "[" + ", ".join(parts) + "]"
    return str(value)


# ── Array operations ─────────────────────────────────────────────────

def _builtin_push(arr, value):
    """push(arr, value) → append value to end of array."""
    if not isinstance(arr, list):
        raise TypeError("push() expects an array as first argument")
    arr.append(value)
    return arr  # FIXED: return the array after mutation


def _builtin_pop(arr):
    """pop(arr) → remove and return the last element."""
    if not isinstance(arr, list):
        raise TypeError("pop() expects an array as first argument")
    if len(arr) == 0:
        raise IndexError("pop() on empty array")
    return arr.pop()


def _builtin_remove(arr, index):
    """remove(arr, index) → remove and return element at index."""
    if not isinstance(arr, list):
        raise TypeError("remove() expects an array as first argument")
    if not isinstance(index, int):
        raise TypeError("remove() expects an integer index as second argument")
    try:
        return arr.pop(index)
    except IndexError:
        raise IndexError(f"remove() index {index} out of range (length {len(arr)})")


def _builtin_contains(arr, value):
    """contains(arr, value) → true if value is in array."""
    if not isinstance(arr, list):
        raise TypeError("contains() expects an array as first argument")
    return value in arr


def _builtin_reverse(arr):
    """reverse(arr) → reverse array in place."""
    if not isinstance(arr, list):
        raise TypeError("reverse() expects an array as first argument")
    arr.reverse()
    return arr  # FIXED: return the array after mutation


def _builtin_sort(arr):
    """sort(arr) → sort array in place."""
    if not isinstance(arr, list):
        raise TypeError("sort() expects an array as first argument")
    try:
        arr.sort()
    except TypeError:
        raise TypeError("sort() cannot compare mixed types")


# ── registry ────────────────────────────────────────────────────────

BUILTINS: dict[str, callable] = {
    "print":    _builtin_print,
    "input":    _builtin_input,
    "len":      _builtin_len,
    "type":     _builtin_type,
    "hasAttr":  _builtin_hasAttr,
    "toInt":    _builtin_toInt,
    "toFloat":  _builtin_toFloat,
    "toString": _builtin_toString,
    "push":     _builtin_push,
    "pop":      _builtin_pop,
    "remove":   _builtin_remove,
    "contains": _builtin_contains,
    "reverse":  _builtin_reverse,
    "sort":     _builtin_sort,
}


def register_builtins(env: "Environment") -> None:
    """Inject every built-in function into *env*."""
    for name, fn in BUILTINS.items():
        env.set(name, fn)
