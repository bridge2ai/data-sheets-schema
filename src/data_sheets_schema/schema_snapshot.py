"""Capture a local LinkML schema and its transitive imports without a view.

Keeping logical paths preserves relative imports through symlink aliases.
LinkML package imports are read from the installed package. Remote imports are
refused: an uncaptured dependency cannot establish a reusable cache identity.
"""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Callable
import functools
import hashlib
import json
import os
from pathlib import Path

import yaml
from linkml_runtime import SCHEMA_DIRECTORY, URI_TO_LOCAL
from linkml_runtime.linkml_model.meta import SchemaDefinition
from linkml_runtime.utils.context_utils import map_import
from linkml_runtime.utils.namespaces import Namespaces


@dataclass(frozen=True)
class SchemaSnapshot:
    # (LinkML import key, logical source path, captured bytes), root first.
    sources: tuple[tuple[str, Path, bytes | OSError], ...]
    key: tuple[str, str]


@functools.lru_cache(maxsize=128)
def _metadata(content: bytes) -> tuple:
    doc = yaml.safe_load(content) or {}
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
                   strict: bool = False) -> SchemaSnapshot:
    """Capture both supported namespace-initialization orders (#1273).

    Callers can initialize namespaces before loading imports, or allow the first
    prefixed import to do it. Capture the union without reading any file twice;
    the view later selects bytes using its actual namespace state. An unavailable
    alternative is recorded and fails only if that alternative is selected.
    The source preflight supplies its existing byte capture and requests the
    generator's default traversal alone, with errors raised before generation.
    """
    from data_sheets_schema.resources import resource_path
    read = read_bytes or Path.read_bytes
    root = Path(os.path.abspath(resource_path(path)))   # from any directory (#1301)
    files = {root: read(root) if content is None else content}
    root_meta = _metadata(files[root])
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
                meta = metadata[name] = _metadata(data)
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
            target = str(p.resolve())
        except (OSError, RuntimeError):
            target = str(p)
        stamp = (f"{type(data).__name__}:{data.errno}" if isinstance(data, OSError)
                 else hashlib.sha256(data).hexdigest())
        identity.append((str(p), target, stamp))
    # Distinct logical aliases may resolve imports differently. Keep each
    # stable alias cached rather than evicting views by their shared target.
    key = (str(root), hashlib.blake2b(
        json.dumps(identity, ensure_ascii=False).encode("utf-8"), digest_size=16).hexdigest())
    return SchemaSnapshot(tuple((names[p], p, data) for p, data in files.items()), key)
