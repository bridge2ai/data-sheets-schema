"""Same-tool U5 before/after scanner evidence, including incomplete derivation."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

from tests.test_native_u5_external_schema import BASE_COMMIT, ROOT, checked_input


def test_scanner_before_after_retains_complete_arrays_or_explicit_blocker(tmp_path):
    baseline, _ = checked_input('baseline-' + BASE_COMMIT[:9], BASE_COMMIT)
    tool = ROOT / '.claude/skills/d4d-generation-specificity-audit/scan.py'
    tokens, exceptions = tool.with_name('tokens.yaml'), tool.with_name('exceptions.yaml')
    identity = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (tool, tokens, exceptions)}
    env = {k: os.environ[k] for k in ('PATH', 'HOME', 'TMPDIR', 'VIRTUAL_ENV') if k in os.environ}
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    evidence = {}
    arrays = {}
    for label, source in (('before', baseline), ('after', ROOT)):
        output = tmp_path / label
        output.mkdir()
        command = [sys.executable, '-P', '-B', str(tool), '--root', str(source),
                   '--report', str(output / 'scan.md'), '--json', str(output / 'scan.json'),
                   '--tokens', str(tokens), '--exceptions', str(exceptions), '--full-json']
        completed = subprocess.run(command, cwd=source, env=env, capture_output=True, timeout=600)
        (output / 'stdout.txt').write_bytes(completed.stdout)
        (output / 'stderr.txt').write_bytes(completed.stderr)
        value = None
        if completed.returncode in (0, 1):
            value = json.loads((output / 'scan.json').read_bytes())
            assert isinstance(value['hits'], list) and isinstance(value['violations'], list)
            arrays[label] = {k: value[k] for k in ('hits', 'violations', 'test_dependencies')}
        evidence[label] = {'root': str(source), 'returncode': completed.returncode,
                           'derivation_complete': value is not None,
                           'finding_arrays_available': value is not None,
                           'tool_identities': identity,
                           'stderr': completed.stderr.decode(errors='replace')}
    complete = len(arrays) == 2
    result = {'before_base': BASE_COMMIT, 'runs': evidence,
              'status': 'complete' if complete else 'blocked_incomplete_derivation',
              # Null is deliberate: absent derivation is not zero findings.
              'exact_arrays_equal': arrays['before'] == arrays['after'] if complete else None,
              'finding_arrays': arrays if complete else None,
              'scope': 'source-only scanner measurement; no native acceptance'}
    (tmp_path / 'scanner-comparison.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    assert {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (tool, tokens, exceptions)} == identity
    checked_input('baseline-' + BASE_COMMIT[:9], BASE_COMMIT)
    assert complete, json.dumps(evidence, indent=2)
    assert result['exact_arrays_equal'], 'full finding arrays differ; explicit disposition required'
