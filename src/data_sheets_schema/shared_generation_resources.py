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


def record_schema_paths(path: Path) -> tuple[Path, ...]:
    """Discover both record readers' imports with one shared bounded budget."""
    from .resources import physical, resource_path
    from .schema_snapshot import capture_schema
    captured = {}
    total = 0

    def read(selected):
        nonlocal total
        selected = Path(selected)
        if selected in captured:
            return captured[selected]
        if len(captured) >= MAX_SCHEMA_FILES:
            raise ValueError('shared record-schema closure exceeds file count bound')
        limit = min(MAX_SCHEMA_FILE_BYTES, MAX_SCHEMA_TOTAL_BYTES - total)
        fd = os.open(selected, os.O_RDONLY | getattr(os, 'O_NONBLOCK', 0))
        with os.fdopen(fd, 'rb') as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode):
                raise ValueError(f'shared record-schema dependency is not a regular file: {selected}')
            if info.st_size > limit:
                raise ValueError('shared record-schema closure exceeds byte bound')
            raw = stream.read(limit + 1)
        if len(raw) > limit:
            raise ValueError('shared record-schema closure exceeds byte bound')
        total += len(raw)
        captured[selected] = raw
        return raw

    # Validator(str(schema)) preserves the logical source_file. The custom
    # JsonSchemaGenerator compiler resolves it for source_file and base_dir.
    # Both begin with fresh namespaces, but a root symlink can give them
    # different imports. Count their union, never two independent budgets.
    logical = physical(resource_path(path))
    paths = []
    for root in dict.fromkeys((logical, logical.resolve())):
        snapshot = capture_schema(root, read_bytes=read,
                                  namespace_orders=(False,), strict=True)
        paths.extend(source for _name, source, _raw in snapshot.sources)
    return tuple(dict.fromkeys(paths))


def resource_paths(specs) -> tuple[Path, ...]:
    """Paths actually read by the selected API contract, not new input pins.

    Optional current observations remain optional. Discovery protects their
    existing bytes; content validation and request identities remain unchanged.
    """
    from . import audit_omissions, provenance, prompt_registry, shared_generation
    from .evidence_assertions import protocol_for_renderer
    from .resources import resource_path
    from .schema_digest import resolve_schema

    paths = [resource_path(name) for name in shared_generation.ASSET_HASHES]
    # Omission assets are module-adjacent, unlike the resource_path assets.
    paths.extend(audit_omissions.ASSETS / name for name in audit_omissions.ASSET_SHA256)
    paths.extend(resource_path(Path(
        f'src/download/prompts/evidence_protocol_v{protocol_for_renderer(spec.render_version)}.md'))
        for spec in specs)
    paths.extend(record_schema_paths(provenance.record_schema_path()))
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
