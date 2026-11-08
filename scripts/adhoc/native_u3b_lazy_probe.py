"""U3-B isolated initialization/refusal probe, 2026-11-07.

Input: installed dependencies and this checkout. Output: JSON assertions on
stdout. Imports Python rawloader only when explicitly testing its transition;
never executes a native agent or performs a provider/network operation.
"""
import json
from pathlib import Path
import sys

assert 'linkml.utils.rawloader' not in sys.modules
from data_sheets_schema import native_catalog_initialization as initialization
from data_sheets_schema import native_catalog_reuse as catalog
from data_sheets_schema import audit_omissions as omissions
from data_sheets_schema.schema_snapshot import SchemaSnapshot
assert 'linkml.utils.rawloader' not in sys.modules
assert initialization.phase() == 0
assert catalog.runtime_token() is not None
raw = b'id: https://example.test/missing\nclasses:\n  Dataset: {}\n'
path = Path('/synthetic/not-read/schema.yaml')
snapshot = SchemaSnapshot((('missing', path, raw),), ('synthetic', 'synthetic'))

def outcome():
    try:
        return ('value', omissions._schema_with_root_bases(path, schema_snapshot=snapshot))
    except Exception as exc:
        return ('error', type(exc).__name__, str(exc), str(exc.__cause__))

original = outcome()
assert original[0] == 'error'
assert outcome() == original
before = catalog.runtime_token()
import linkml.utils.rawloader
assert initialization.phase() == 1
assert catalog.runtime_token() is not None and catalog.runtime_token() is not before
initialized = outcome()
assert initialized[0] == 'value'
assert outcome() == initialized
print(json.dumps({'lazy_import_preserved': True, 'original': original[0],
                  'initialized': initialized[0], 'within_state_parity': True}))
