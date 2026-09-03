"""One SchemaView per schema file (#926).

linkml_runtime 1.9.4 wraps 66 ``SchemaView`` methods in ``functools.lru_cache``
(64 of them unbounded, ``lru_cache(None)``). ``self`` is part of every cache key, so a view
is pinned for the life of the process by its own method caches — ``del``
frees nothing, and ``gc.collect()`` finds nothing to collect. A view of the
merged Dataset schema holds 30–80 MB once induced slots have been computed.
An ``execute()`` built about 24 of them across the identifier, verifiable,
claim, pair-consistency and digest code, so the API-runner tests grew by
~0.7 GB per execute and the suite peaked at 21 GB on a 69 GB laptop — and was
killed at ~7 GB on every CI run, which read as "the runner has received a
shutdown signal" rather than as a test failure.

Every in-process construction site takes its view from here instead. The
key is the resolved path with the file's size and mtime, so a schema
rewritten under a running process (``make regen-all``, the sync test that
tampers with the merged file and restores it) gets a fresh view; the old one
stays pinned by linkml whatever we do, so this module drops its reference and
does not pretend it was freed.
"""

from __future__ import annotations

from pathlib import Path

from linkml_runtime import SchemaView

_VIEWS: dict[tuple[str, int, int], SchemaView] = {}


def shared_view(path: str | Path) -> SchemaView:
    """The one ``SchemaView`` for the schema file at ``path``."""
    p = Path(path).resolve()
    st = p.stat()
    key = (str(p), st.st_size, st.st_mtime_ns)
    view = _VIEWS.get(key)
    if view is None:
        for stale in [k for k in _VIEWS if k[0] == key[0]]:
            del _VIEWS[stale]
        view = _VIEWS[key] = SchemaView(str(p))
    return view


def views_held() -> int:
    """How many views this module currently shares (for tests)."""
    return len(_VIEWS)
