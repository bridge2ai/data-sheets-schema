"""Selected normative/data/provenance resources, resolved at each boundary.

This is not a host or installed-code sandbox. Mutable run state and the digest
inventory belong to the write footprint; software/Git attestation stays with
its existing readers. No successful filesystem discovery is cached here.
"""
from __future__ import annotations

import os
from pathlib import Path
import stat

MAX_SCHEMA_FILES = 64
MAX_SCHEMA_FILE_BYTES = 4 * 1024 * 1024
MAX_SCHEMA_TOTAL_BYTES = 16 * 1024 * 1024
MAX_SCHEMA_ENTRIES = 100_000
MAX_SCHEMA_DEPTH = 64


class _SchemaReads:
    """One boundary's bounded captured bytes, shared by actual schema readers."""

    def __init__(self):
        self.captured = {}
        self.total = 0

    def read(self, selected):
        selected = Path(selected)
        if selected in self.captured:
            return self.captured[selected]
        if len(self.captured) >= MAX_SCHEMA_FILES:
            raise ValueError('shared schema closure exceeds file count bound')
        limit = min(MAX_SCHEMA_FILE_BYTES, MAX_SCHEMA_TOTAL_BYTES - self.total)
        fd = os.open(selected, os.O_RDONLY | getattr(os, 'O_NONBLOCK', 0))
        with os.fdopen(fd, 'rb') as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode):
                raise ValueError(f'shared schema dependency is not a regular file: {selected}')
            if info.st_size > limit:
                raise ValueError('shared schema closure exceeds byte bound')
            raw = stream.read(limit + 1)
        if len(raw) > limit:
            raise ValueError('shared schema closure exceeds byte bound')
        self.total += len(raw)
        self.captured[selected] = raw
        return raw


def record_schema_paths(path: Path, *, _reader=None) -> tuple[Path, ...]:
    """Discover both record readers' imports with one shared bounded budget."""
    from .resources import physical, resource_path
    from .schema_snapshot import capture_schema
    reader = _reader if _reader is not None else _SchemaReads()
    # Validator(str(schema)) preserves the logical source_file. The custom
    # JsonSchemaGenerator compiler resolves it for source_file and base_dir.
    # Both begin with fresh namespaces, but a root symlink can give them
    # different imports. Count their union, never two independent budgets.
    logical = physical(resource_path(path))
    paths = []
    for root in dict.fromkeys((logical, logical.resolve())):
        snapshot = capture_schema(root, read_bytes=reader.read,
                                  namespace_orders=(False,), strict=True)
        paths.extend(source for _name, source, _raw in snapshot.sources)
    return tuple(dict.fromkeys(paths))


def schema_sync_paths(*, _reader=None) -> tuple[Path, ...]:
    """Protect schema-sync's eager YAML bytes and its actual logical imports.

    Unreferenced YAML is captured without parsing. A nonmatching directory
    symlink is skipped, just as Path.rglob does; matching nonregular points
    fail the bounded read. No external import's parent tree is crawled.
    """
    from . import schema_sync
    from .resources import physical, resource_path
    from .schema_digest import INVENTORY_LEDGER
    from .schema_snapshot import capture_schema
    reader = _reader if _reader is not None else _SchemaReads()
    merged_names = {merged.name for merged, _source, _class, _marker in schema_sync.MERGED_SCHEMAS}
    inventory = physical(resource_path(INVENTORY_LEDGER))
    eager, imported, points = set(), set(), []
    scanned = {}
    entries = 0

    def yaml_paths(directory, depth=0):
        nonlocal entries
        if depth > MAX_SCHEMA_DEPTH:
            raise ValueError('shared schema closure exceeds directory depth bound')
        if directory in scanned:
            return scanned[directory]
        paths = []
        with os.scandir(directory) as children:
            for child in children:
                entries += 1
                if entries > MAX_SCHEMA_ENTRIES:
                    raise ValueError('shared schema closure exceeds entry bound')
                path = Path(child.path)
                if child.name.endswith('.yaml'):
                    paths.append(path)
                if child.is_dir(follow_symlinks=False):
                    paths.extend(yaml_paths(path, depth + 1))
        scanned[directory] = tuple(paths)
        return scanned[directory]

    for merged, source, _class, _marker in schema_sync.MERGED_SCHEMAS:
        merged, source = resource_path(merged), resource_path(source)
        if merged.exists():
            points.append(physical(merged))
        # The owner returns UNCHECKED/STALE before its snapshot on these paths.
        if not source.exists() or not merged.exists():
            continue
        source = physical(source)
        for path in yaml_paths(source.parent):
            path = physical(path)
            if path.name not in merged_names or path == source:
                reader.read(path)
                eager.add(path)
        snapshot = capture_schema(source, content=reader.read(source),
                                  read_bytes=reader.read, namespace_orders=(False,), strict=True)
        imported.update(path for _name, path, _raw in snapshot.sources)
    # This specific path is intentionally mutable when merely swept up by
    # the eager snapshot. An alias, root or actual import is not exempt.
    return tuple(dict.fromkeys((*points, *sorted(eager - {inventory}), *sorted(imported))))


def resource_paths(specs) -> tuple[Path, ...]:
    """Paths actually read by the selected API contract, not new input pins.

    Optional current observations remain optional. Discovery protects their
    existing bytes; content validation and request identities remain unchanged.
    """
    from . import audit_omissions, provenance, prompt_registry, shared_generation
    from .evidence_assertions import protocol_for_renderer
    from .resources import resource_path
    from .schema_digest import resolve_schema
    from .profiles import PROFILES

    paths = [resource_path(name) for name in shared_generation.ASSET_HASHES]
    if any(spec.shared_generation_version == 2 for spec in specs):
        paths.extend(resource_path(name) for name in (*shared_generation.ROUTING_ASSET_HASHES,
                                                     *shared_generation.ROUTING_CODE))
    # Omission assets are module-adjacent, unlike the resource_path assets.
    paths.extend(audit_omissions.ASSETS / name for name in audit_omissions.ASSET_SHA256)
    paths.extend(resource_path(Path(
        f'src/download/prompts/evidence_protocol_v{protocol_for_renderer(spec.render_version)}.md'))
        for spec in specs)
    reader = _SchemaReads()
    paths.extend(record_schema_paths(provenance.record_schema_path(), _reader=reader))
    paths.extend(schema_sync_paths(_reader=reader))
    # Record conformance compares every registered profile's current digest,
    # even for a neutral run. Resolve their actual (possibly overridden) pins.
    # An absent pin still belongs to the existing MissingVocabulary finding.
    for profile in PROFILES.values():
        pin = profile.pin_path
        if pin is not None and pin.exists():
            paths.append(pin)
    optional = [resource_path(prompt_registry.REGISTRY),
                resolve_schema(provenance.SOURCE_SCHEMA),
                resolve_schema(provenance.CORE_SOURCE_SCHEMA),
                resource_path(provenance.DETERMINISTIC_CONFIG),
                # grounding.form_facts calls declared_naming() with this cwd
                # default, independently of the explicitly selected manifest.
                Path('data/preprocessed/source_manifest.yaml'),
                *(resource_path(path) for path in provenance.AGENT_PLAYBOOKS)]
    paths.extend(path for path in optional if path.exists())
    return tuple(dict.fromkeys(paths))
