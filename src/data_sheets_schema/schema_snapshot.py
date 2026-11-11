"""Capture a local LinkML schema and its transitive imports without a view.

Keeping logical paths preserves relative imports through symlink aliases.
LinkML package imports are read from the installed package. Remote imports are
refused: an uncaptured dependency cannot establish a reusable cache identity.
"""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass
import functools
import hashlib
import json
import os
from pathlib import Path
from threading import Lock

import yaml
from linkml_runtime import SCHEMA_DIRECTORY, URI_TO_LOCAL
from linkml_runtime.linkml_model.meta import SchemaDefinition
from linkml_runtime.utils.context_utils import map_import
from linkml_runtime.utils.namespaces import Namespaces

_METADATA_FIELDS = ("id", "name", "imports", "prefixes", "default_curi_maps")
_METADATA_CACHE_ENTRIES = 2
_METADATA_CACHE_BYTES = 40_000_000


class _MetadataDerivationCache:
    """Bound only immutable import-metadata field bytes, never normalized tuples."""

    def __init__(self):
        self._entries = OrderedDict()
        self._bytes = 0
        self._lock = Lock()

    @staticmethod
    def _key(key):
        if (type(key) is not tuple or len(key) != 2 or type(key[0]) is not bytes
                or type(key[1]) is not tuple or any(type(raw) is not bytes for raw in key[1])):
            raise ValueError("schema metadata cache requires immutable complete byte keys")

    def get(self, key):
        self._key(key)
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            self._entries.move_to_end(key)
            return entry[0]

    def put(self, key, value):
        self._key(key)
        if type(value) is not bytes:
            raise ValueError("schema metadata cache retains only immutable field bytes")
        size = len(key[0]) + sum(len(raw) for raw in key[1]) + len(value)
        if size > _METADATA_CACHE_BYTES:
            return
        with self._lock:
            prior = self._entries.get(key)
            if prior is not None:
                if prior[0] != value:
                    raise ValueError("one schema document produced different metadata field bytes")
                self._entries.move_to_end(key)
                return
            while self._entries and (len(self._entries) >= _METADATA_CACHE_ENTRIES
                                     or self._bytes + size > _METADATA_CACHE_BYTES):
                _, (_, old_size) = self._entries.popitem(last=False)
                self._bytes -= old_size
            self._entries[key] = (value, size)
            self._bytes += size

    def snapshot(self):
        with self._lock:
            return tuple((key, value) for key, (value, _size) in self._entries.items())

    def clear(self):
        with self._lock:
            self._entries.clear()
            self._bytes = 0


_METADATA_DERIVATIONS = _MetadataDerivationCache()
_SCHEMA_LAUNCH_CONTEXT = None
_schema_dependencies = None


@dataclass(frozen=True)
class SchemaSnapshot:
    # (LinkML import key, logical source path, captured bytes), root first.
    sources: tuple[tuple[str, Path, bytes | OSError], ...]
    key: tuple[str, str]


def _lossless_json_tree(value, seen: set[int]) -> bool:
    if value is None or type(value) in (bool, int, str):
        return True
    if type(value) is float:
        try:
            encoded = json.dumps(value, allow_nan=False)
            decoded = json.loads(encoded)
        except (TypeError, ValueError):
            return False
        return type(decoded) is float and repr(decoded) == repr(value)
    if type(value) is list:
        if id(value) in seen:
            return False
        seen.add(id(value))
        return all(_lossless_json_tree(item, seen) for item in value)
    if type(value) is dict:
        if id(value) in seen:
            return False
        seen.add(id(value))
        return all(type(key) is str and _lossless_json_tree(item, seen)
                   for key, item in value.items())
    return False


def _ordered_json_equal(left, right) -> bool:
    if type(left) is not type(right):
        return False
    if type(left) is float:
        return repr(left) == repr(right)
    if type(left) is list:
        return (len(left) == len(right)
                and all(_ordered_json_equal(a, b) for a, b in zip(left, right)))
    if type(left) is dict:
        return (tuple(left.keys()) == tuple(right.keys())
                and all(_ordered_json_equal(left[k], right[k]) for k in left))
    return left == right


def _encode_metadata_fields(doc) -> bytes | None:
    if type(doc) is not dict:
        return None
    fields = {key: doc[key] for key in _METADATA_FIELDS if key in doc}
    if not _lossless_json_tree(fields, set()):
        return None
    try:
        raw = json.dumps(
            fields, ensure_ascii=False, allow_nan=False, separators=(",", ":")
        ).encode("utf-8")
        decoded = json.loads(raw.decode("utf-8"))
    except (TypeError, ValueError):
        return None
    if not _ordered_json_equal(decoded, fields):
        return None
    return raw


def _decode_metadata_fields(raw: bytes) -> dict:
    if type(raw) is not bytes:
        raise ValueError("cached schema metadata fields must be bytes")
    decoded = json.loads(raw.decode("utf-8"))
    if (type(decoded) is not dict
            or any(key not in _METADATA_FIELDS for key in decoded)
            or not _lossless_json_tree(decoded, set())):
        raise ValueError("cached schema metadata fields are not a valid 5-field mapping")
    return decoded


def _cold_metadata(content: bytes) -> tuple:
    doc = yaml.safe_load(content) or {}
    return _metadata_document(doc)


def _launch_cached_metadata(content: bytes) -> tuple:
    context = _SCHEMA_LAUNCH_CONTEXT
    guard = _schema_dependencies
    if (type(content) is not bytes
            or type(context) is not tuple or len(context) != 2
            or type(context[0]) is not bytes or not context[0]
            or type(context[1]) is not bool or not context[1]
            or guard is None):
        return _cold_metadata(content)
    domain, _enabled = context
    for _attempt in range(2):
        before = guard.schema_metadata_state(
            metadata=_metadata,
            metadata_document=_metadata_document,
            schema_definition=SchemaDefinition,
            yaml_alias=yaml,
            json_alias=json,
        )
        if before is None:
            return _cold_metadata(content)
        key = (
            domain + b"\nproducer:schema_snapshot._metadata_v1\nphase:"
            + str(before[0]).encode("ascii") + b"\n",
            (content,),
        )
        cached = _METADATA_DERIVATIONS.get(key)
        if cached is not None:
            doc = _decode_metadata_fields(cached)
            result = _metadata_document(doc)
            after = guard.schema_metadata_state(
                metadata=_metadata,
                metadata_document=_metadata_document,
                schema_definition=SchemaDefinition,
                yaml_alias=yaml,
                json_alias=json,
            )
            if after != before:
                continue
            return result
        raw_doc = yaml.safe_load(content)
        if raw_doc is not None and type(raw_doc) is not dict:
            return _metadata_document(raw_doc or {})
        doc = {} if raw_doc is None else raw_doc
        encoded = _encode_metadata_fields(doc)
        if encoded is None:
            return _metadata_document(doc)
        result = _metadata_document(doc)
        if _metadata_document(_decode_metadata_fields(encoded)) != result:
            return result
        after = guard.schema_metadata_state(
            metadata=_metadata,
            metadata_document=_metadata_document,
            schema_definition=SchemaDefinition,
            yaml_alias=yaml,
            json_alias=json,
        )
        if after != before:
            continue
        _METADATA_DERIVATIONS.put(key, encoded)
        return result
    return _cold_metadata(content)


@functools.lru_cache(maxsize=128)
def _metadata(content: bytes) -> tuple:
    if _SCHEMA_LAUNCH_CONTEXT is not None:
        return _launch_cached_metadata(content)
    return _cold_metadata(content)


def _metadata_document(doc) -> tuple:
    # Let the installed metamodel normalize its supported mapping/list forms.
    fields = {k: doc[k] for k in
        ("id", "name", "imports", "prefixes", "default_curi_maps") if k in doc}
    # gen-linkml's raw loader derives an omitted name from the schema ID.
    # Metadata discovery must admit the same source documents. The actual
    # view parser still applies its installed SchemaDefinition contract.
    if not fields.get("name") and fields.get("id"):
        fields["name"] = str(fields["id"]).replace("#", "/").rsplit("/", 1)[-1]
    schema = SchemaDefinition(**fields)
    prefixes = tuple((str(p.prefix_prefix), str(p.prefix_reference)) for p in schema.prefixes.values())
    return str(schema.name), tuple(schema.imports), prefixes, tuple(schema.default_curi_maps)


def resolve_import_path(name, source: Path, namespaces) -> Path:
    """LinkML's import mapping, including installed URL aliases (#1274)."""
    mapped = map_import({"linkml:": str(SCHEMA_DIRECTORY)}, namespaces, name) + ".yaml"
    mapped = str(URI_TO_LOCAL.get(mapped, mapped))
    if "://" in mapped:
        raise ValueError(f"cannot capture remote schema import {name!r}")
    imported = Path(mapped)
    return Path(os.path.abspath(imported if imported.is_absolute() else source.parent / imported))


def capture_schema(path: str | Path, *, content: bytes | None = None,
                   read_bytes: Callable[[Path], bytes] | None = None,
                   namespace_orders: tuple[bool, ...] | None = None,
                   strict: bool = False, logical_paths: bool = False) -> SchemaSnapshot:
    """Capture both supported namespace-initialization orders (#1273).

    Callers can initialize namespaces before loading imports, or allow the first
    prefixed import to do it. Capture the union without reading any file twice;
    the view later selects bytes using its actual namespace state. An unavailable
    alternative is recorded and fails only if that alternative is selected.
    The source preflight supplies its existing byte capture and requests the
    generator's default traversal alone, with errors raised before generation.
    """
    if type(logical_paths) is not bool:
        raise ValueError("logical_paths must be an explicit boolean")
    if logical_paths:
        return _capture_schema(path, read_bytes, content=content, namespace_orders=namespace_orders,
                               strict=strict, logical_paths=True)
    from data_sheets_schema.resources import resource_path
    read = read_bytes or Path.read_bytes
    from data_sheets_schema.resources import physical
    root = physical(resource_path(path))              # from any directory; `..` through the filesystem (#1301, #1570)
    return _capture_schema(root, read, content=content, namespace_orders=namespace_orders,
                           strict=strict, physical_identity=True)


def _capture_native_schema(path: Path, members: tuple[tuple[Path, bytes], ...],
                           *, member_bytes: int) -> SchemaSnapshot:
    """Strict-check every native member, then reuse only its private metadata.

    All occurrences are checked before traversal, including replaced paths.
    Normalization remains lazy in traversal order. No caller supplies parsed
    data, a validator or a cached validation result.
    """
    from .audit_omissions import _mapping
    fields, frozen = {}, {}
    for source, raw in members:
        doc = _mapping(raw, 'native schema', limit=member_bytes, _native_events=True)
        fields[raw] = {key: doc[key] for key in
                       ('id', 'name', 'imports', 'prefixes', 'default_curi_maps') if key in doc}
        frozen[source] = raw

    def read(source):
        if source not in frozen:
            raise ValueError('selected schema import is outside the complete captured closure')
        return frozen[source]

    normalized = {}

    def metadata(raw):
        if raw not in normalized:
            # The metamodel may normalize mutable inlined values. Its input
            # belongs to this call and cannot mutate another source's fields.
            normalized[raw] = _metadata_document(deepcopy(fields[raw]))
        return normalized[raw]

    return _capture_schema(path, read, strict=True, logical_paths=True,
                           metadata_reader=metadata)


def _capture_schema(root, read, *, content=None, namespace_orders=None,
                    strict=False, physical_identity=False, logical_paths=False,
                    metadata_reader=None):
    """Shared traversal with unchanged positional saved-reader identities.

    The live wrapper alone resolves filesystem aliases. Ordinary saved replay
    retains its existing nonphysical identity; explicitly selected native
    logical replay has its own domain and strict canonical-path validation.
    """
    if type(logical_paths) is not bool:
        raise ValueError("logical_paths must be an explicit boolean")
    if logical_paths:
        # An already captured closure has canonical lexical identities. Never
        # consult today's aliases, resource installation or filesystem metadata.
        path, root = root, Path(root)
        if (read is None or not strict or physical_identity or not root.is_absolute()
                or str(root) != str(path) or '..' in root.parts
                or os.path.normpath(str(root)) != str(root)):
            raise ValueError("logical schema replay requires a strict captured reader and canonical absolute root")
    if metadata_reader is None:
        metadata_reader = _metadata
    files = {root: read(root) if content is None else content}
    root_meta = metadata_reader(files[root])
    names = {root: root_meta[0]}
    orders = namespace_orders if namespace_orders is not None else ((False, True) if root_meta[1] else (False,))
    for early in orders:
        metadata = {root_meta[0]: root_meta}

        @functools.lru_cache(maxsize=1)
        def namespaces():
            ns = Namespaces()
            for meta in metadata.values():
                for cmap in root_meta[3]:
                    ns.add_prefixmap(cmap, include_defaults=False)
                for prefix, value in meta[2]:
                    ns[prefix] = value
            return ns

        try:
            if early:
                namespaces()
            pending, visited = [root_meta[0]], set()
            while pending:
                name = pending.pop()
                if name in visited:
                    continue
                visited.add(name)
                source = root if name == root_meta[0] else resolve_import_path(name, root, namespaces)
                if source not in files:
                    try:
                        files[source] = read(source)
                    except OSError as exc:
                        files[source] = exc
                    names[source] = name
                data = files[source]
                if isinstance(data, OSError):
                    raise data
                meta = metadata[name] = metadata_reader(data)
                for imp in meta[1]:
                    if imp == name:
                        continue
                    if "/" in name and ":" not in imp:
                        imp = os.path.normpath(str(Path(name).parent / imp))
                    pending.append(imp)
        except (OSError, ValueError, TypeError, yaml.YAMLError):
            if strict:
                raise
            # A failed alternate traversal must not reject a valid one. The
            # selected loader below still raises on those captured bytes/errors.
            pass

    identity = []
    for p, data in sorted(files.items()):
        try:
            target = str(p.resolve()) if physical_identity else str(p)
        except (OSError, RuntimeError):
            target = str(p)
        stamp = (f"{type(data).__name__}:{data.errno}" if isinstance(data, OSError)
                 else hashlib.sha256(data).hexdigest())
        identity.append((str(p), target, stamp))
    # Distinct logical aliases may resolve imports differently. Keep each
    # stable alias cached rather than evicting views by their shared target.
    key = (str(root), hashlib.blake2b(
        json.dumps({'domain': 'captured_logical_schema_v1', 'sources': identity}
                   if logical_paths else identity, ensure_ascii=False).encode("utf-8"), digest_size=16).hexdigest())
    return SchemaSnapshot(tuple((names[p], p, data) for p, data in files.items()), key)
