"""Capture a local LinkML schema and its transitive imports without a view.

Keeping logical paths preserves relative imports through symlink aliases.
LinkML package imports are read from the installed package. Remote imports are
refused: an uncaptured dependency cannot establish a reusable cache identity.
"""

from __future__ import annotations

from dataclasses import dataclass
import functools
import hashlib
import json
import os
from pathlib import Path

import yaml
from linkml_runtime import SCHEMA_DIRECTORY
from linkml_runtime.utils.context_utils import map_import
from linkml_runtime.utils.namespaces import Namespaces


@dataclass(frozen=True)
class SchemaSnapshot:
    # (LinkML import key, logical source path, captured bytes), root first.
    sources: tuple[tuple[str, Path, bytes], ...]
    key: tuple[str, str]


@functools.lru_cache(maxsize=128)
def _metadata(content: bytes) -> tuple:
    doc = yaml.safe_load(content) or {}
    imports = doc.get("imports") or []
    if isinstance(imports, str):
        imports = [imports]
    prefixes = tuple((name, value.get("prefix_reference") if isinstance(value, dict) else value)
                     for name, value in (doc.get("prefixes") or {}).items())
    return str(doc.get("name")), tuple(imports), prefixes, tuple(doc.get("default_curi_maps") or [])


def capture_schema(path: str | Path, *, content: bytes | None = None) -> SchemaSnapshot:
    """Key and parse the same bytes, including every imported dependency."""
    root = Path(os.path.abspath(path))
    files = {root: root.read_bytes() if content is None else content}
    root_meta = _metadata(files[root])
    schemas: dict[str, tuple[Path, bytes]] = {}
    metadata: dict[str, tuple] = {}

    def namespaces():
        ns = Namespaces()
        for meta in metadata.values():
            for cmap in root_meta[3]:
                ns.add_prefixmap(cmap, include_defaults=False)
            for prefix, value in meta[2]:
                ns[prefix] = value
        return ns

    def imported_path(name):
        mapped = map_import({"linkml:": str(SCHEMA_DIRECTORY)}, namespaces, name)
        if "://" in mapped:
            raise ValueError(f"cannot capture remote schema import {name!r}")
        imported = Path(mapped + ".yaml")
        return Path(os.path.abspath(imported if imported.is_absolute() else root.parent / imported))

    # Match SchemaView.imports_closure's import keys and traversal order.
    # Preloading that map later prevents LinkML from reopening live files.
    pending = [root_meta[0]]
    while pending:
        name = pending.pop()
        if name in schemas:
            continue
        source = root if name == root_meta[0] else imported_path(name)
        if source not in files:
            files[source] = source.read_bytes()
        data = files[source]
        meta = metadata[name] = _metadata(data)
        schemas[name] = (source, data)
        for imp in meta[1]:
            if imp == name:
                continue
            if "/" in name and ":" not in imp:
                imp = os.path.normpath(str(Path(name).parent / imp))
            pending.append(imp)

    identity = [(str(p), str(p.resolve()), hashlib.sha256(data).hexdigest())
                for p, data in sorted(files.items())]
    key = (str(root.resolve()), hashlib.blake2b(
        json.dumps(identity, ensure_ascii=False).encode("utf-8"), digest_size=16).hexdigest())
    return SchemaSnapshot(tuple((name, path, data) for name, (path, data) in schemas.items()), key)
