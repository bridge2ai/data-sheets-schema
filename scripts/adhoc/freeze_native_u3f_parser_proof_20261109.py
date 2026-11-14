"""U3-F parser transport proof setup, 2026-11-09.

Inputs: original committed native event parser, experimental scanner/refactors.
Outputs: retained experimental source under assigned scratch and a source-bound
parser contract in scan.py. Restore only this task's two unsuccessful refactors.
This does not add a filename-only exemption: every source byte must match.
"""
import hashlib
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT.parent / 'scratch-native-u1u3/u3f/parser-refactor-experiment'
OUT.mkdir()
paths = ['.claude/skills/d4d-generation-specificity-audit/scan.py',
         'src/data_sheets_schema/native_schema_event_reuse.py',
         'src/data_sheets_schema/audit_omissions.py',
         'tests/test_native_u1_scanner_contracts.py']
for relative in paths:
    target = OUT / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes((ROOT / relative).read_bytes())
for relative in paths[1:3]:
    raw = subprocess.check_output(['git', 'show', '49a5f2b74:'+relative], cwd=ROOT)
    (ROOT / relative).write_bytes(raw)
raw = (ROOT / paths[1]).read_bytes()
digest = hashlib.sha256(raw).hexdigest()
scanner = ROOT / paths[0]
text = scanner.read_text()
start = text.index('def _immutable_builtin_observation(')
end = text.index('def _without_docstring(', start)
text = text[:start]+text[end:]
text = text.replace('                if q in parsed and _immutable_builtin_observation(parsed[q][1], fn, node):\n                    continue\n', '')
marker = 'def _without_docstring(body):'
proof = '''def _native_event_parser_contract(source):
    """Closed transport summary for the reviewed immutable YAML-event cache.

    The entire source, including imports/constants, is fixed, not just the
    receiving call. load_native keys by exact input bytes plus the runtime
    fingerprint; cached records contain immutable parser fields, while every
    result is freshly composed. mapping repeats JSON/shape validation before
    retention. Bounds, fallback and runtime-token drift checks remain exact.

    This permits the existing parser/evidence transfer rules for this one
    fixed implementation. It does not prove admission, omit source literals,
    trust a cache verdict or permit any future implementation by filename.
    A changed byte refuses discovery and requires a new instrument review.
    """
    import hashlib
    if hashlib.sha256(source.encode('utf-8')).hexdigest() != DIGEST:
        raise ConfigError('native event parser transport source changed; fixed summary requires review')
    return True


'''.replace('DIGEST', repr(digest))
text = text.replace(marker, proof+marker)
old = '        res = str(q).endswith(_audit_evidence_modules)\n'
new = '''        if _rel(root, q) == 'src/data_sheets_schema/native_schema_event_reuse.py':
            # A closed parser implementation, not a basename waiver. Its
            # imported authority bindings are included in the source contract.
            res = q in parsed and _native_event_parser_contract(parsed[q][0])
        else:
            res = str(q).endswith(_audit_evidence_modules)
'''
assert text.count(old) == 1
scanner.write_text(text.replace(old, new))
tests = ROOT / paths[3]
text = tests.read_text()
start = text.index('def _immutable_observation(')
end = text.index('\ndef test_native_route_cannot_omit_bc1_exclusion', start)
tests.write_text(text[:start]+'''@pytest.mark.parametrize('before,after', [
    ('key = raw, token', 'key = token'),
    ('return value, candidate', 'return {"project": "CHORUS"}, candidate'),
    ('retain_native(candidate, limit=limit)', 'pass'),
    ('events.clear()', "events.append('CHORUS')"),
    ('if not reusable or _token(limit) != token:', 'if not reusable:'),
    ('from . import audit_omissions as _omissions', 'from . import unknown as _omissions'),
])
def test_native_event_parser_summary_is_bound_to_complete_source(before, after):
    source = (ROOT / 'src/data_sheets_schema/native_schema_event_reuse.py').read_text()
    assert scan._native_event_parser_contract(source)
    assert before in source
    with pytest.raises(scan.ConfigError, match='parser transport source changed'):
        scan._native_event_parser_contract(source.replace(before, after, 1))

''' + text[end:])
print(digest)
