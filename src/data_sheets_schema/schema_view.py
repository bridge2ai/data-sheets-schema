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

One kind of view is not shared and is freed: `version_view`, a view of
another version of a file read by its hash (#3931). It is built with
linkml's method caches on the instance rather than the class, and those
caches are dropped when its `with` block exits (#4082).
"""

from __future__ import annotations

import functools
import hashlib
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Iterator

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


class _InstanceCached:
    """One of linkml's method caches, kept on the view instead of the class.

    A non-data descriptor: the first lookup on a view stores an `lru_cache`
    of the bound, undecorated method in the view's `__dict__`, which every
    later lookup finds first. The cache is keyed on the arguments alone and
    belongs to that view, so it goes when the view goes."""

    __slots__ = ("name", "function", "maxsize", "typed")

    def __init__(self, name: str, function: Callable[..., Any], maxsize: int | None, typed: bool):
        self.name, self.function, self.maxsize, self.typed = name, function, maxsize, typed

    def __get__(self, view: SchemaView | None, owner: type | None = None) -> Any:
        if view is None:
            return self
        cached = functools.lru_cache(maxsize=self.maxsize, typed=self.typed)(self.function.__get__(view, owner))
        view.__dict__[self.name] = cached
        return cached


class _ReleasableView(SchemaView):
    """A SchemaView whose method caches belong to it, not to its class.

    linkml's caches are class-level and keyed on `self`, so any view whose
    cached methods have run is pinned for the life of the process (#926).
    Here each of those methods is cached on the instance, and `release`
    drops the caches. Each cache holds its bound method, which holds the
    view, so dropping them is what lets the view's last reference free it.
    Nothing else differs: the functions and arguments are linkml's own."""

    def release(self) -> None:
        """Drop this view's method caches and their references to it."""
        for name in _INSTANCE_CACHED:
            self.__dict__.pop(name, None)


def _lru_cached_methods(cls: type) -> dict[str, Any]:
    """{name: its `functools.lru_cache` wrapper} for every method of `cls`,
    inherited ones included, that attribute lookup reaches through one.

    The wrapper is the innermost one on the method's `__wrapped__` chain. It
    is not always the attribute itself: five deprecated aliases (`all_class`
    and the like) put a `deprecated` wrapper outside the cache, and that
    wrapper answers `cache_parameters` for the cache it holds. A cached
    static or class method takes no instance and is left alone."""
    found: dict[str, Any] = {}
    for klass in cls.__mro__:
        for name, attr in vars(klass).items():
            found.setdefault(name, attr)
    out: dict[str, Any] = {}
    for name, attr in found.items():
        if isinstance(attr, (staticmethod, classmethod)):
            continue
        chain, seen = [attr], {id(attr)}
        while hasattr(chain[-1], "__wrapped__") and id(chain[-1].__wrapped__) not in seen:
            chain.append(chain[-1].__wrapped__)
            seen.add(id(chain[-1]))
        caches = [link for link in chain[:-1] if callable(getattr(link, "cache_parameters", None))]
        if caches:
            out[name] = caches[-1]
    return out


def _cache_on_instances() -> tuple[str, ...]:
    """Give `_ReleasableView` an instance cache for every method linkml
    caches on `SchemaView`, of the function that cache wraps, with its size
    and typing; their names. A wrapper outside linkml's cache (the
    deprecation warning on five aliases) is not carried over."""
    caches = _lru_cached_methods(SchemaView)
    for name, cache in caches.items():
        params = cache.cache_parameters()
        setattr(_ReleasableView, name,
                _InstanceCached(name, cache.__wrapped__, params["maxsize"], params["typed"]))
    return tuple(caches)


#: The SchemaView methods linkml wraps in `lru_cache` (66 in linkml_runtime
#: 1.9.4), re-cached per instance on `_ReleasableView`.
_INSTANCE_CACHED: tuple[str, ...] = _cache_on_instances()


def version_document(content: bytes) -> dict[str, Any]:
    """The mapping `content` parses to, parsed as `shared_view` parses a
    file, for `version_view`. `content` is another version of a schema file
    (the merged schema a run recorded, #3931). Refused unless it is a
    mapping."""
    doc = yaml.load(content.decode("utf-8"), Loader=DupCheckYamlLoader)
    if not isinstance(doc, dict):
        raise ValueError("the bytes are not a schema mapping")
    return doc


@contextmanager
def version_view(path: str | Path, document: dict[str, Any]) -> Iterator[SchemaView]:
    """A view of `document` (`version_document`), another version of the
    schema at `path`, for the `with` block only.

    This is not `shared_view`. That keeps one view per logical path and
    drops it when the bytes change, which is right for a file rewritten
    under a running process. For a version read by its hash it is not: each
    version would evict today's view of the same path, the next reader would
    build today's again, and a corpus pass would pin a fresh view of today's
    schema for every version it met (#926). This view is never shared. It
    is built with its method caches on the instance (`_ReleasableView`) and
    released when the block exits. A caller keeps what it read from the
    view, as `run_schema` keeps a version's identifier rules, and not the
    view. So a corpus pass holds at most one version view at a time. Kept,
    each one was 24-49 MB resident: 14 versions took a form and grounding
    pass from about 0.29 GB to 0.80 GB peak (#4082).

    A version read by its hash is only those bytes, so a document that
    imports anything but the LinkML metamodel (`linkml:`) is refused rather
    than completed from today's tree; a merged schema imports nothing."""
    local = [str(i) for i in (document.get("imports") or []) if not str(i).startswith("linkml:")]
    if local:
        raise ValueError(f"the bytes import {', '.join(local)}, which their recorded hash does not cover")
    schema = SchemaDefinition(**document)
    schema.source_file = str(path)
    view = _ReleasableView(schema)
    try:
        yield view
    finally:
        view.release()


def views_held() -> int:
    """How many views this module currently shares (for tests)."""
    return len(_VIEWS)
