"""Verify parse-cache handoff artifacts, protected files and authored text.

Inputs: handoff and assigned scratch. Output: verification facts and hashes.
Lead parse-cache assignment, 2026-11-15.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

handoff, scratch = Path(sys.argv[1]), Path(sys.argv[2])
base = 'e2d0ebb95'
protected = ['src/data_sheets_schema/shared_generation.py', 'src/data_sheets_schema/api_runner.py',
             'src/download/prompts/canonical_hashes.yaml', 'tests/utils/run_spec_boundary_contracts.json',
             '.claude/skills/d4d-generation-specificity-audit']
assert not subprocess.check_output(['git', 'diff', base, '--', *protected])
subprocess.run(['git', 'diff', '--check'], check=True)
diff = subprocess.check_output(['git', 'diff', base, '--unified=0'], text=True)
assert not any(chr(64) in line for line in diff.splitlines() if line.startswith('+') and not line.startswith('+++'))
for path in [*Path('scripts/adhoc').glob('*parse_cache*20261115.py'), Path('tests/test_typed_json_parse_cache.py')]:
    assert path.is_file() and path.stat().st_size and chr(64) not in path.read_text(), path
for mode in ('response', 'publication'):
    for suffix in ('', '-profile'):
        out = scratch / ('cache-after-v3-' + mode + suffix)
        value = json.loads((out / 'metrics.json').read_text())
        assert value['parse_cache']['hits'] > 0
        if mode == 'publication':
            assert value['state'] == 'assembly_complete' and value['published_files'] == 6
            assert (out / 'published-stage').is_dir()
        if suffix:
            assert (out / 'costs.prof').stat().st_size
for name in ('cache-unit-v3-run', 'cache-final-v3-measurements-run', 'cache-regression-v3-run',
             'cache-collection-run', 'cache-pins-final-run'):
    for member in ('command.json', 'output.log', 'result.json'):
        assert (scratch / name / member).is_file() and (scratch / name / member).stat().st_size
for name in ('parse-cache-summary-v3.json', 'cache-regression-v3.xml', 'cache-pins-final/hashes.json'):
    assert (scratch / name).stat().st_size
for row in json.loads((scratch / 'cache-pins-final/hashes.json').read_text()):
    if row['new_sha256'] is not None:
        assert hashlib.sha256(Path(row['path']).read_bytes()).hexdigest() == row['new_sha256']
command = json.loads((scratch / 'cache-regression-v3-run/command.json').read_text())
requested = {arg[:-3].replace('/', '.') for arg in command if arg.startswith('tests/') and arg.endswith('.py')}
tree = ET.parse(scratch / 'cache-regression-v3.xml')
classes = {case.get('classname', '') for case in tree.iter('testcase')}
assert all(any(name == module or name.startswith(module + '.') for name in classes) for module in requested)
print(json.dumps({'test_suites': [suite.attrib for suite in tree.iter('testsuite')],
                  'requested_modules_verified': sorted(requested)}, indent=2))
raw = handoff.read_bytes()
assert raw and bytes([64]) not in raw
print('Protected files and scanner unchanged; whitespace and authored-character checks passed.')
print('Required measurement, publication, test, collection and pin-search evidence exists and is nonempty.')
print(str(handoff))
print(hashlib.sha256(raw).hexdigest())
