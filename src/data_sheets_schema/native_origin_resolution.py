"""Fresh resolution for exact fixed owner-origin spellings only.

No path result is cached. Every call retains its physical observation, and
ordinary Python resolution remains the fallback for aliases and returned
native lookup failures. Python/FFI exceptions propagate after owned cleanup.
"""
from functools import lru_cache
import os
from pathlib import Path
import sys


_PYTHON_RESOLVE = Path.resolve
_CONCRETE_PATH = type(Path())
_CONCRETE_RESOLVE = _CONCRETE_PATH.resolve
_PYTHON_REALPATH = os.path.realpath
_PYTHON_LSTAT = os.lstat
_PYTHON_READLINK = os.readlink


@lru_cache(maxsize=1)
def _native_functions():
    """Retain only libc functions, never an origin, path or authority result."""
    if os.name != 'posix' or sys.platform not in ('darwin', 'linux'):
        return None
    try:
        import ctypes
        library = ctypes.CDLL(
            '/usr/lib/libSystem.B.dylib' if sys.platform == 'darwin' else None,
            use_errno=True)
        resolve, free = library.realpath, library.free
        resolve.argtypes = [ctypes.c_char_p, ctypes.c_void_p]
        resolve.restype = ctypes.c_void_p
        free.argtypes = [ctypes.c_void_p]
        free.restype = None
        return library, resolve, free
    except (ImportError, AttributeError, OSError):
        return None


def _matches_native_spelling(raw):
    functions = _native_functions()
    if functions is None:
        return False
    import ctypes
    _, resolve, free = functions
    pointer = resolve(raw, None)
    if not pointer:
        return False
    try:
        # realpath(NULL) owns a NUL-terminated allocation. Read it before the
        # corresponding libc free, including on read/comparison failure.
        return ctypes.string_at(pointer) == raw
    finally:
        free(pointer)


def resolve_fixed_origin(source, expected):
    """Resolve once, fast only when the fresh result is the fixed spelling.

    Callers retain their original number/order of calls: qualified origins
    resolve BOTH the actual and expected paths; a bare origin resolves the
    actual path against its retained loader spelling. This is not a verdict.
    """
    eligible = (
        type(source) is str and type(expected) is str and source == expected
        and source.startswith('/') and not source.startswith('//')
        and '\0' not in source and str(Path(source)) == source
        and Path.resolve is _PYTHON_RESOLVE
        and _CONCRETE_PATH.resolve is _CONCRETE_RESOLVE
        and os.path.realpath is _PYTHON_REALPATH
        and os.lstat is _PYTHON_LSTAT and os.readlink is _PYTHON_READLINK)
    if eligible:
        try:
            raw = os.fsencode(source)
        except (UnicodeError, ValueError):
            pass
        else:
            if _matches_native_spelling(raw):
                return Path(source)
    # Preserve Python's strict=False behavior for missing paths, symlink
    # loops, unsupported platforms, spelling changes and returned failures.
    return Path(source).resolve()
