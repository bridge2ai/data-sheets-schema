"""One SchemaView per schema file (#926).

linkml_runtime 1.9.4 wraps 66 ``SchemaView`` methods in ``functools.lru_cache``
(64 of them unbounded, ``lru_cache(None)``). ``self`` is part of every cache
key, so once any cached method has been called a view is pinned for the life
of the process by its own method caches — ``del`` frees nothing, and
``gc.collect()`` finds nothing to collect. A view of the merged Dataset schema
holds 30–80 MB once induced slots have been computed. An ``execute()`` built
about 24 of them across the identifier, verifiable, claim, pair-consistency
and digest code, so the API-runner tests grew by ~0.7 GB per execute and the
suite peaked at 21 GB on a 69 GB laptop — and was killed on the 16 GB hosted
runner on every CI run, which read as "the runner has received a shutdown
signal" rather than as a test failure.

Every in-process construction site in this package takes its view from here
instead (linkml's own validator builds views of its own; see
``provenance._record_validator`` for the one on the execute path). The key
is the logical absolute path with a hash of the captured root and transitive import
bytes — not size and mtime,
which a same-length rewrite within one timestamp tick can collide on (#943)
— so a schema rewritten under a running process (``make regen-all``, the
sync test that tampers with the merged file and restores it) gets a fresh
view. The old one stays pinned by linkml whatever we do, so this module drops
its reference and does not pretend it was freed. Hashing a ~1 MB file costs
about a millisecond per call, against seconds to build a view.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
import yaml

from linkml_runtime import SchemaView
from linkml_runtime.linkml_model.meta import SchemaDefinition
from linkml_runtime.utils.yamlutils import DupCheckYamlLoader
from data_sheets_schema.schema_snapshot import SchemaSnapshot, capture_schema, resolve_import_path

_VIEWS: dict[tuple[str, str], SchemaView] = {}


def content_key(path: str | Path, *, content: bytes | None = None) -> tuple[str, str]:
    """(resolved path, blake2b of the bytes) — what a view is keyed by."""
    p = Path(path).resolve()
    data = p.read_bytes() if content is None else content
    return (str(p), hashlib.blake2b(data, digest_size=16).hexdigest())


def shared_view(path: str | Path, *, content: bytes | None = None,
                snapshot: SchemaSnapshot | None = None) -> SchemaView:
    """The shared view of captured root/import bytes at ``path`` (#1265)."""
    captured = capture_schema(path, content=content) if snapshot is None else snapshot
    key = captured.key
    view = _VIEWS.get(key)
    if view is None:
        for stale in [k for k in _VIEWS if k[0] == key[0]]:
            del _VIEWS[stale]
        # Hash and parse the same bytes. Loading the path after hashing it
        # can permanently store a different revision under this key (#1260).
        frozen = {p: data for _name, p, data in captured.sources}

        def parse(source):
            data = frozen[source]
            if isinstance(data, OSError):
                raise data
            # LinkML's loads still guesses whether a string names a file.
            # These bytes are already captured YAML, including one-line flow
            # documents without a final newline (#1277).
            schema = SchemaDefinition(**yaml.load(data.decode("utf-8"), Loader=DupCheckYamlLoader))
            schema.source_file = str(source)
            return schema

        root = captured.sources[0][1]
        view = SchemaView(parse(root))
        # Keep LinkML's lazy schema-map and namespace initialization order,
        # while satisfying every import from the captured bytes (#1270).
        def load_captured(imp, from_schema=None):
            source = Path((from_schema or view.schema).source_file)
            selected = resolve_import_path(imp, source, view.namespaces)
            try:
                return parse(selected)
            except KeyError as exc:
                raise ValueError(f"schema import {imp!r} is outside the captured closure") from exc
        view.load_import = load_captured
        _VIEWS[key] = view
    return view


def views_held() -> int:
    """How many views this module currently shares (for tests)."""
    return len(_VIEWS)
