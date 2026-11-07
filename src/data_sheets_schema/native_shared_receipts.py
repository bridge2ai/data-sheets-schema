"""Pure captured receipt accounting for native_shared_generation_v1.

The native selection is distinct from both API receipt registrations. These
functions perform no file, runtime, provider or environment operations.
"""
from __future__ import annotations

import json
from pathlib import Path
from threading import Lock

from . import audit_omissions as omissions
from . import native_shared_contract as contract
from . import native_catalog_reuse as catalog_reuse
from .schema_snapshot import SchemaSnapshot


def schema_snapshot(selection, kind='full'):
    """Reconstruct the exact captured logical closure without a live resolver."""
    rows = [schema for schema in selection.schemas if schema.kind == kind]
    if len(rows) != 1:
        raise ValueError('native stage requires exactly one selected schema closure')
    schema = rows[0]
    names = {role: name for name, role in schema.import_roles}
    sources = tuple((names[item.pin.role], Path(item.pin.path), item.raw) for item in schema.sources)
    return SchemaSnapshot(sources, (str(sources[0][1]), schema.closure_sha256))



_CATALOG_PAYLOAD_BYTES = 40_000_000
_CATALOG_DOMAIN = 'native_shared_receipt_catalog_v1'


def _catalog_key(selection, snapshot):
    """Validate immutable carrier identity before considering a pure hit."""
    rows = [item for item in selection.schemas if item.kind == 'full']
    if len(rows) != 1 or type(rows[0]) is not contract.SchemaClosureCapture:
        raise ValueError('receipt catalog requires one captured full schema')
    schema = rows[0]
    # Recheck pin integrity even if a caller has bypassed frozen dataclasses.
    sources = tuple(contract.CapturedArtifact(
        contract.ArtifactPin(item.pin.role, item.pin.path, item.pin.bytes, item.pin.sha256), item.raw)
        for item in schema.sources)
    checked = contract.SchemaClosureCapture(schema.closure_sha256, schema.import_roles,
        schema.kind, schema.root_class, schema.root_name, sources)
    names = {role: name for name, role in checked.import_roles}
    expected = tuple((names[item.pin.role], Path(item.pin.path), item.raw) for item in sources)
    if snapshot.sources != expected:
        raise ValueError('receipt catalog snapshot differs from its captured schema')
    if sum(len(item.raw) for item in sources) > omissions.MAX_SCHEMA_BYTES:
        raise ValueError('schema closure exceeds byte bound')
    metadata = contract.canonical({'domain': _CATALOG_DOMAIN, 'kind': checked.kind,
        'root_class': checked.root_class, 'root_name': checked.root_name,
        'root_path': sources[0].pin.path, 'closure_sha256': checked.closure_sha256,
        'import_roles': [list(row) for row in checked.import_roles],
        'sources': [{'name': names[item.pin.role], 'pin': contract.pin_dict(item.pin)} for item in sources],
        'declaration': selection.document()['inputs']['full_schema'],
        'mode': {'logical_paths': True, 'strict': True, 'namespace_orders': None},
        'limits': {'max_input_bytes': omissions.MAX_INPUT_BYTES,
            'max_schema_bytes': omissions.MAX_SCHEMA_BYTES, 'max_nodes': omissions.MAX_NODES,
            'max_depth': omissions.MAX_DEPTH, 'native': dict(contract.HARD_LIMITS),
            'supplied': selection.bounds()}})
    return metadata, tuple(item.raw for item in sources)


class _ReceiptCatalogContext:
    """One bounded immutable derivation, owned by one capture or live attempt."""
    def __init__(self):
        self._entry = None
        self._entry_marker = None
        self._typed_marker = None
        self._derivations = None
        self._derivations_marker = None
        self._bytes = 0
        self._lock = Lock()

    def derivations(self):
        from . import audit_omissions as omissions, typed_audit as typed
        token = (typed._derive, typed._derive_uncached, typed._seal, omissions._prepare)
        with self._lock:
            if self._derivations is None or self._derivations_marker != token:
                self._derivations = typed.DerivationCache()
                self._derivations_marker = token
            return self._derivations

    def catalog(self, selection, snapshot):
        return self.schema_data(selection, snapshot)[1]

    def schema_data(self, selection, snapshot):
        key = _catalog_key(selection, snapshot)
        current_marker = catalog_reuse.runtime_token()
        with self._lock:
            if current_marker is None or self._entry_marker is not current_marker:
                self._discard()
            entry = (self._entry if current_marker is not None
                     and self._entry_marker is current_marker
                     and self._bytes <= _CATALOG_PAYLOAD_BYTES
                     and self._entry is not None and self._entry[0] == key else None)
        if entry is None:
            return self._fresh_schema_data(selection, snapshot, key)
        result = contract.strict_json(entry[1], 'captured schema catalog', omissions.MAX_SCHEMA_BYTES)
        if catalog_reuse.runtime_token() is not current_marker:
            # A changing dependency cannot authorize a prior successful catalog.
            return self._fresh_schema_data(selection, snapshot, key)
        return entry[2], result

    def _discard(self):
        """Caller holds the lock; a transition cannot revive an old entry."""
        self._entry = self._entry_marker = self._typed_marker = None
        self._bytes = 0

    def _fresh_schema_data(self, selection, snapshot, key):
        # Root-only prefixes are intentional: an explicit empty tuple must
        # never inherit imported or current-installation identifier bases.
        before = catalog_reuse.runtime_token()
        with self._lock:
            if before is None or self._entry_marker is not before:
                self._discard()
        bases, catalog = omissions._schema_with_root_bases(snapshot.sources[0][1], schema_snapshot=snapshot)
        # LinkML URIorCURIE names have the same released JSON meaning.
        raw = omissions._json(catalog).encode('utf-8')
        result = contract.strict_json(raw, 'captured schema catalog', omissions.MAX_SCHEMA_BYTES)
        bases_bytes = json.dumps(bases, ensure_ascii=True, separators=(',', ':')).encode('ascii')
        after = catalog_reuse.runtime_token()
        marker = (before if before is not None and before is after
                  and catalog_reuse.supported_snapshot(snapshot) else None)
        size = len(key[0]) + sum(len(item) for item in key[1]) + len(raw) + len(bases_bytes)
        if size <= _CATALOG_PAYLOAD_BYTES:
            with self._lock:
                self._entry, self._bytes = (key, raw, bases), size
                self._typed_marker = marker
                self._entry_marker = marker
        else:
            with self._lock:
                self._discard()
        return bases, result

    def _typed_catalog(self, selection, path, snapshot):
        """Only an existing, exactly associated catalog may skip construction."""
        try:
            if (type(snapshot) is not SchemaSnapshot or type(snapshot.sources) is not tuple
                    or not snapshot.sources or type(path) is not type(Path())
                    or not path.is_absolute()):
                return None
            for row in snapshot.sources:
                if (type(row) is not tuple or len(row) != 3 or type(row[0]) is not str
                        or type(row[1]) is not type(Path()) or not row[1].is_absolute()
                        or type(row[2]) is not bytes):
                    return None
            if path != snapshot.sources[0][1]:
                return None
            key = _catalog_key(selection, snapshot)
            token = catalog_reuse.runtime_token()
            with self._lock:
                if token is None or self._typed_marker is not token:
                    self._discard()
                entry = self._entry
                if (token is None or self._typed_marker is not token or entry is None
                        or entry[0] != key or self._bytes > _CATALOG_PAYLOAD_BYTES):
                    return None
            catalog = contract.strict_json(entry[1], 'captured schema catalog', omissions.MAX_SCHEMA_BYTES)
            if catalog['sources'] != [
                    {'name': name, 'sha256': omissions._sha(raw)} for name, _path, raw in snapshot.sources]:
                return None
            if catalog_reuse.runtime_token() is not token:
                with self._lock:
                    self._discard()
                return None
            return catalog
        except Exception:
            # A failed eligibility lookup must not replace the original typed
            # constructor's error or move it ahead of protocol/input checks.
            return None


def _catalog_context(value=None):
    if value is None:
        return _ReceiptCatalogContext()
    if type(value) is not _ReceiptCatalogContext:
        raise ValueError('receipt catalog context must be private derivation storage')
    return value
