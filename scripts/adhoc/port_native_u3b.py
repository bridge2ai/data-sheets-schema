"""Port U3-B donor sections onto the pinned base, 2026-11-07.

Inputs: local Git donor objects and the U3 base. Outputs: additive native
modules and selective shared-file changes for the offline U3-B review.
Run once on the untouched base; no network or executable-native operations.
"""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'src/data_sheets_schema'

def donor(name, revision='1d792d525'):
    return subprocess.check_output(['git', 'show', f'{revision}:src/data_sheets_schema/{name}.py'], cwd=ROOT, text=True)

def section(text, start, end):
    return text[text.index(start):text.index(end)]

def write(name, text):
    (SRC / (name + '.py')).write_text(text)

# Closed-binding opt-ins; preserve the zero-argument contract.
write('cache_dependencies', donor('cache_dependencies'))

a = (SRC / 'audit_omissions.py').read_text()
d = donor('audit_omissions')
a = a.replace('class _SchemaEventLoader', section(d, 'def captured_asset_bytes', 'class _EventReplayLoader') + 'class _SchemaEventLoader')
a = a.replace(section(a, 'def _schema(path', '\ndef _class'), section(d, 'def _schema(path', '\ndef _class'))
# Keep the existing prepare body; add the captured-asset and private catalog seams.
a = a.replace('max_request_bytes: int = 32_000_000) -> Prepared:', 'max_request_bytes: int = 32_000_000, captured_assets=None) -> Prepared:\n    return _prepare(record=record, bundle=bundle, manifest=manifest, receipt=receipt,\n        context=context, schema_path=schema_path, max_output_tokens=max_output_tokens,\n        schema_snapshot=schema_snapshot, max_request_bytes=max_request_bytes, captured_assets=captured_assets)\n\n\ndef _prepare(*, record, bundle, manifest, receipt, context, schema_path, max_output_tokens,\n             schema_snapshot=None, max_request_bytes=32_000_000, captured_assets=None, _catalog=None):')
a = a.replace('policy = _asset("policy.md").decode("utf-8")\n    response_schema = json.loads(_asset("response.schema.json"))\n    context_schema = json.loads(_asset("context.schema.json"))', 'assets = captured_asset_bytes(captured_assets)\n    policy = assets["policy.md"].decode("utf-8")\n    response_schema = json.loads(assets["response.schema.json"])\n    context_schema = json.loads(assets["context.schema.json"])')
a = a.replace('catalog = _schema(Path(schema_path), schema_snapshot=schema_snapshot)', 'catalog = (_catalog if _catalog is not None else\n                   _schema(Path(schema_path), schema_snapshot=schema_snapshot,\n                           logical_paths=captured_assets is not None))')
# Native only: retain events after mapping and node validation, never a verdict.
a = a.replace('def _mapping(raw, label, **kwargs):\n    value = _read(raw, label, **kwargs)', '''def _mapping(raw, label, *, _native_events=False, **kwargs):
    if _native_events:
        from .native_schema_event_reuse import mapping
        return mapping(raw, label, **kwargs)
    value = _read(raw, label, **kwargs)''')
a = a.replace("_mapping(schema_snapshot.sources[0][2], 'captured schema')", "_mapping(schema_snapshot.sources[0][2], 'captured schema', _native_events=True)")
a = a.replace('_mapping(raw, "schema", _schema_events=True)\n            frozen', '_mapping(raw, "schema", _schema_events=True, _native_events=logical_paths)\n            frozen')
write('audit_omissions', a)
s = (SRC / 'schema_snapshot.py').read_text().replace("_mapping(raw, 'native schema', limit=member_bytes)", "_mapping(raw, 'native schema', limit=member_bytes, _native_events=True)")
write('schema_snapshot', s)

e = donor('native_schema_event_reuse', 'b1b508870')
e = e[e.index('from __future__'):]
e = '"""Bounded native parser events; fresh M8 composition and validation per call."""\n' + e
e = e.replace('omissions._YAML_REPLAY_MAX_EVENTS', 'omissions.MAX_SCHEMA_EVENTS').replace('omissions._YAML_REPLAY_MAX_TEXT_BYTES', 'MAX_PAYLOAD_BYTES')
e = e.replace('return omissions._load_yaml(text), None', 'return omissions._schema_yaml(text), None')
e = e.replace('omissions._EventReplayLoader(text, events)', 'omissions._SchemaEventLoader(events)')
e = e.replace('chars > MAX_EVENT_CHARS', 'chars > min(MAX_EVENT_CHARS, omissions.MAX_SCHEMA_EVENT_CHARS)')
e = e.replace('return (limit, omissions.MAX_DEPTH', 'return (limit, omissions.MAX_SCHEMA_EVENT_CHARS, omissions.MAX_DEPTH')
# Reader creates the original Mark even after rawloader changes yaml.error.Mark.
e = e.replace('type(mark) is not yaml.error.Mark', 'type(mark) is not yaml.reader.Mark').replace('return yaml.error.Mark(name,', 'return yaml.reader.Mark(name,')
e += '''

def mapping(raw, label, *, limit=MAX_INPUT_BYTES, _schema_events=False, json_only=False):
    """Native-only strict mapping; unsuccessful construction is never retained."""
    from . import audit_omissions as omissions
    if json_only:
        return omissions._mapping(raw, label, limit=limit, json_only=True)
    if type(raw) is not bytes or not raw or len(raw) > limit:
        raise ValueError(f"{label} must be nonempty bytes within the {limit}-byte bound")
    try:
        value, candidate = load_native(raw.decode('utf-8'), limit=limit)
        omissions._validate_json(value, max_nodes=omissions.MAX_NODES, max_depth=omissions.MAX_DEPTH)
    except (ValueError, TypeError, KeyError, AttributeError, RecursionError, yaml.YAMLError) as exc:
        raise ValueError(f"{label} cannot be read safely ({type(exc).__name__})") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a mapping")
    retain_native(candidate, limit=limit)
    return value
'''
write('native_schema_event_reuse', e)
i = donor('native_catalog_initialization', 'b1b508870').replace('Diagnostic U0 T2:', 'Native catalog reuse:')
write('native_catalog_initialization', i)
c = donor('native_catalog_reuse', 'b1b508870')
c = c.replace('omissions._mapping, omissions._read, omissions._load_yaml, omissions._legacy_yaml,', 'omissions._mapping, omissions._read,')
c = c.replace('omissions._event_text_bytes, omissions._sha', 'omissions._sha')
c = c.replace("            '_YAML_REPLAY_MAX_EVENTS', '_YAML_REPLAY_MAX_TEXT_BYTES',\n", '')
c = c.replace('omissions._UniqueLoader, omissions._EventReplayLoader,', 'omissions._UniqueLoader,')
write('native_catalog_reuse', c)
r = donor('native_shared_receipts', 'b1b508870')
r = r[:r.index('\ndef omission_assets')]
r = r.replace('audit_omissions as omissions, receipts', 'audit_omissions as omissions')
r = r.replace('from .chunking import chunk_texts, validate_manifest_mapping\n', '').replace('from .receipt_completion_policy import coverage_counts\n', '')
# U3-C owns receipt reconstruction and the later observation/completion caches.
start = r.index('        self._prefixes = {}')
end = r.index('        self._bytes = 0', start)
r = r[:start] + r[end:]
write('native_shared_receipts', r)
