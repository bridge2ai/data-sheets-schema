"""One parse of a schema file per process, keyed on the bytes that were parsed.

`data_sheets_schema_all.yaml` is 1.4 MB and `yaml.safe_load` takes about four
seconds on it. Three production paths parsed it from disk on every call —
`grounding.declared_bases`, `identifiers.declared_prefixes` and the enum alias
table in `api_runner` — and a single record write reaches them seven times, so
every phase of every run, every `backfill-checks` over 282 records and every
runner test paid roughly 25 seconds re-reading a file that had not changed
(CI profile, 2026-09-11: 25 of a 39-second test in `safe_load`).

The key is the resolved path, its `st_mtime_ns` and its size, so an edit in
place invalidates the entry and a copy edited in a temporary directory is a
different entry. The parsed document is returned as a deep copy: the cache
holds one tree per file, and a caller that mutates what it was handed must
not be able to poison the next caller's read.
"""
from __future__ import annotations

import copy
import functools
import hashlib
from pathlib import Path
from typing import Any

import yaml


@functools.lru_cache(maxsize=1024)
def _parsed(path: str, mtime_ns: int, size: int) -> Any:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def load_yaml(path: Path) -> Any:
    """The parsed YAML document at `path`, cached until the file changes.

    Not only schemas: `d4d runs check` parsed each provenance record about
    twenty times — once per status function, each reading the file for
    itself — 5,431 parses for 277 records, 245 of its 248 profiled seconds
    (#1203). Raises `FileNotFoundError` like a read would; callers that
    tolerated a missing file before still test `path.exists()` first.
    """
    from data_sheets_schema.resources import resource_path
    p = resource_path(path)
    st = p.stat()
    return copy.deepcopy(_parsed(str(p.resolve()), st.st_mtime_ns, st.st_size))


load_schema = load_yaml


def forget(path: Path) -> None:
    """A writer has just replaced `path`: drop the whole parse cache.

    The whole cache, not one entry — `lru_cache` has no per-key eviction,
    and a write is rare next to a read, so paying a few re-parses is cheaper
    than a second index. The argument names the file for the reader of the
    call site; it does not narrow the eviction (#1204 review, S3). Called by
    every writer of a record or artifact, so a rewrite that lands with the
    same size inside one mtime tick — the one edit the key cannot see — is
    never served stale.
    """
    del path
    _parsed.cache_clear()


@functools.lru_cache(maxsize=32)
def _digest(path: str, mtime_ns: int, size: int) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_of(path: Path) -> str:
    """sha256 of the file, cached until it changes."""
    from data_sheets_schema.resources import resource_path
    p = resource_path(path)
    st = p.stat()
    return _digest(str(p.resolve()), st.st_mtime_ns, st.st_size)


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
    _parsed.cache_clear()
    _digest.cache_clear()
    from data_sheets_schema import schema_sync
    schema_sync.forget_rebuilds()
