"""One parse of a schema file per process, keyed on the bytes that were parsed.

`data_sheets_schema_all.yaml` is 1.4 MB and `yaml.safe_load` takes about four
seconds on it. Three production paths parsed it from disk on every call —
`grounding.declared_bases`, `identifiers.declared_prefixes` and the enum alias
table in `api_runner` — and a single record write reaches them seven times, so
every phase of every run, every `backfill-checks` over 282 records and every
runner test paid roughly 25 seconds re-reading a file that had not changed
(CI profile, 2026-09-11: 25 of a 39-second test in `safe_load`).

The key includes the resolved path, file identity, `st_mtime_ns` and size.
An edit or atomic replacement invalidates the entry; a copy is a separate
entry. Writers explicitly forget their file, including hard-link aliases,
without evicting unchanged schemas. Returned documents are deep copies, so
one caller cannot poison the next caller's read. The cache holds at most
1,024 files, with one parsed version per path.
"""
from __future__ import annotations

import copy
from collections import OrderedDict
import functools
import hashlib
from pathlib import Path
from threading import RLock
from typing import Any

import yaml


_MAX_PARSED_FILES = 1024
_PARSED: OrderedDict[Path, tuple[tuple[int, ...], Any]] = OrderedDict()
_PARSE_LOCK = RLock()


def _file_state(path: Path) -> tuple[int, ...]:
    st = path.stat()
    return st.st_dev, st.st_ino, st.st_mtime_ns, st.st_size


def load_yaml(path: Path) -> Any:
    """The parsed YAML document at `path`, cached until the file changes.

    Not only schemas: `d4d runs check` parsed each provenance record about
    twenty times — once per status function, each reading the file for
    itself — 5,431 parses for 277 records, 245 of its 248 profiled seconds
    (#1203). Raises `FileNotFoundError` like a read would; callers that
    tolerated a missing file before still test `path.exists()` first.
    """
    from data_sheets_schema.resources import resource_path
    p = resource_path(path).resolve()
    # Coordinate reads and invalidation: an in-flight parse must not reinsert
    # the old document after its writer has returned from forget().
    with _PARSE_LOCK:
        state = _file_state(p)
        cached = _PARSED.get(p)
        if cached is None or cached[0] != state:
            document = yaml.safe_load(p.read_text(encoding="utf-8"))
            _PARSED[p] = state, document
            if len(_PARSED) > _MAX_PARSED_FILES:
                _PARSED.popitem(last=False)
        else:
            document = cached[1]
        _PARSED.move_to_end(p)
    return copy.deepcopy(document)


load_schema = load_yaml


def forget(path: Path) -> None:
    """Drop the written file's parsed YAML and any cached aliases (#1869).

    Same-size, same-timestamp writes still need explicit invalidation. Both
    the cached and current inode matter when a writer atomically replaces
    the file. A deleted file can also be forgotten using its cached identity.
    Unrelated schemas and records remain cached.
    """
    from data_sheets_schema.resources import resource_path
    p = resource_path(path).resolve()
    with _PARSE_LOCK:
        cached = _PARSED.pop(p, None)
        identities = {cached[0][:2]} if cached is not None else set()
        try:
            identities.add(_file_state(p)[:2])
        except FileNotFoundError:
            pass
        for other, (state, _) in list(_PARSED.items()):
            if state[:2] in identities:
                del _PARSED[other]
        # Hashing is cheap compared with parsing; the small independent hash
        # cache must also see same-timestamp rewrites and their aliases.
        _digest.cache_clear()


@functools.lru_cache(maxsize=32)
def _digest(path: str, state: tuple[int, ...]) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_of(path: Path) -> str:
    """sha256 of the file, cached until it changes."""
    from data_sheets_schema.resources import resource_path
    p = resource_path(path).resolve()
    with _PARSE_LOCK:
        return _digest(str(p), _file_state(p))


def tree_fingerprint(directory: Path, pattern: str = "*.yaml", exclude: tuple[str, ...] = ()) -> tuple:
    """(name, mtime_ns, size) for every matching file, sorted — the key for a
    result derived from a whole directory of sources."""
    out = []
    for f in sorted(Path(directory).glob(pattern)):
        if f.name in exclude:
            continue
        st = f.stat()
        out.append((f.name, st.st_mtime_ns, st.st_size))
    return tuple(out)


def clear() -> None:
    """Forget every entry, the rebuilt-schema cache included — for tests
    that replace a file's bytes with the same size inside one mtime tick,
    where the key cannot see the edit."""
    with _PARSE_LOCK:
        _PARSED.clear()
        _digest.cache_clear()
    from data_sheets_schema import schema_sync
    schema_sync.forget_rebuilds()
