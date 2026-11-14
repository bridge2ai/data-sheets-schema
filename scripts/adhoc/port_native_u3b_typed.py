"""U3-B selective typed catalog/captured-assets port, 2026-11-07.

Inputs: local donor 1d792d525 and base typed_audit.py. Output: typed_audit.py.
Keep M8 wire formatting and ordinary behavior; omit donor serializer and
opened-packet caches. This script runs once after port_native_u3b.py.
"""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
path = ROOT / 'src/data_sheets_schema/typed_audit.py'
base = path.read_text()
d = subprocess.check_output(['git', 'show', '1d792d525:src/data_sheets_schema/typed_audit.py'], cwd=ROOT, text=True)
new = d[d.index('class _SchemaReuse:'):d.index('\ndef _omission_findings')]
# Do not retain a packet-open verdict. Reconstruct and compare each time.
start = new.index('    if type(derivations) is DerivationCache:', new.index('def _open('))
end = new.index('    _schema_reuse = None', start)
new = new[:start] + new[end:]
start = new.index('    if type(derivations) is DerivationCache:', new.index('def _open('))
end = new.index('    return raw, prepared', start)
new = new[:start] + new[end:]
# Carry M8's wire identity and refusal semantics verbatim.
new = new.replace('schema_snapshot=None, derivations=None, captured_assets=None):', 'schema_snapshot=None, derivations=None, captured_assets=None, omission_wire=None):')
new = new.replace('schema_snapshot=None, derivations=None, captured_assets=None, _catalog_lookup=None):', 'schema_snapshot=None, derivations=None, captured_assets=None, _catalog_lookup=None, omission_wire=None):')
new = new.replace('schema_snapshot=schema_snapshot, derivations=derivations, captured_assets=captured_assets)', 'schema_snapshot=schema_snapshot, derivations=derivations, captured_assets=captured_assets, omission_wire=omission_wire)')
needle = '    inputs = {key: _blob(value)'
new = new.replace(needle, '    if omission_wire is not None and (type(omission_wire) is not str or omission_wire != SHARED_OMISSION_WIRE):\n        raise ValueError("unsupported omission wire selection")\n' + needle)
new = new.replace('**derived, limitations=list(LIMITATIONS)))', '**derived, limitations=list(LIMITATIONS),\n        **({"omission_wire": omission_wire} if omission_wire is not None else {})))')
new = new.replace('def _open(packet, *, derivations=None, captured_assets=None, _catalog_lookup=None):\n', 'def _open(packet, *, derivations=None, captured_assets=None, _catalog_lookup=None):\n    selected = {"omission_wire"} if type(packet) is dict and "omission_wire" in packet else set()\n')
new = new.replace('"limitations", "sha256"}, "packet")', '"limitations", "sha256"} | selected, "packet")\n    if selected and (type(packet["omission_wire"]) is not str or packet["omission_wire"] != SHARED_OMISSION_WIRE):\n        raise ValueError("unsupported omission wire selection")')
new = new.replace('**derived, "limitations": list(LIMITATIONS)})', '**derived, "limitations": list(LIMITATIONS),\n                      **({"omission_wire": packet["omission_wire"]} if selected else {})})')
# Every native open gets a currently validated/associated catalog, even on a
# derivation hit; unsupported runtime state always takes fresh construction.
needle = '    derived, raw, prepared = _derive(packet["inputs"]'
new = new.replace(needle, '''    if captured_assets is not None and _schema_reuse is None:
        snapshot = _snapshot(packet["schema_sources"])
        catalog = omissions._schema(snapshot.sources[0][1], schema_snapshot=snapshot, logical_paths=True)
        _schema_reuse = _SchemaReuse(snapshot.sources, catalog)
''' + needle)
# Native derivation keys are state-specific; unsupported state bypasses storage.
needle = "        encoded = self._rows.get(key)"
new = new.replace(needle, '''        marker = None
        if captured_assets is not None:
            from .native_catalog_reuse import runtime_token
            marker = runtime_token()
            if marker is None:
                return _derive_uncached(inputs, schema_rows, project, limits,
                    captured_assets=captured_assets, _schema_reuse=_schema_reuse)
            key = (*key, marker)
''' + needle)
new = new.replace('            self._store(key, encoded)', '            if captured_assets is None or runtime_token() is marker:\n                self._store(key, encoded)')
# The API's ordinary omissions.prepare remains the public producer.
new = new.replace('    prepared = omissions._prepare(', '    producer = omissions.prepare if captured_assets is None else omissions._prepare\n    native_options = {} if captured_assets is None else dict(captured_assets=captured_assets,\n        _catalog=(_schema_reuse.for_snapshot(snapshot) if type(_schema_reuse) is _SchemaReuse else None))\n    prepared = producer(')
new = new.replace('captured_assets=captured_assets,\n        _catalog=(_schema_reuse.for_snapshot(snapshot)\n                  if captured_assets is not None and type(_schema_reuse) is _SchemaReuse else None)', '**native_options')
# Ordinary calls preserve their kwargs so existing wrappers see the same API.
new = new.replace('catalog = omissions._schema(Path(schema_path), schema_snapshot=schema_snapshot,\n                                        logical_paths=captured_assets is not None)', 'catalog = omissions._schema(Path(schema_path), schema_snapshot=schema_snapshot,\n                                        **({"logical_paths": True} if captured_assets is not None else {}))')
new = new.replace('worker_request(packet, worker["id"], derivations=derivations, captured_assets=captured_assets)', 'worker_request(packet, worker["id"], derivations=derivations,\n                       **({"captured_assets": captured_assets} if captured_assets is not None else {}))')
tail = base[base.index('\ndef _omission_wire_prepared'):]
# Thread opt-ins through existing formatters and checks without replacing them.
tail = tail.replace('derivations=None)', 'derivations=None, captured_assets=None, _catalog_lookup=None)')
tail = tail.replace('derivations=derivations)', 'derivations=derivations, **_native_options(captured_assets, _catalog_lookup))')
helper = '''
def _native_options(captured_assets, lookup):
    return ({} if captured_assets is None else
            {"captured_assets": captured_assets, "_catalog_lookup": lookup})

'''
path.write_text(base[:base.index('class DerivationCache:')] + new + helper + tail)
