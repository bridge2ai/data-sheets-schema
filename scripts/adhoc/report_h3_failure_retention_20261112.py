#!/usr/bin/env python3
"""2026-11-12 #5967: local commits, test receipts and retained files -> handoff.
Inputs: own branches/scratch outputs; outputs: lead Markdown/JSON, scratch receipt.
No network, native execution or changes to source evidence.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

E = Path('/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions')
W = E / 'codex-native-failure-record-20261112'
S = E / 'scratch-h3-failure-record-20261112'
H = E / 'codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs/codex-h3-failure-record-and-retention-20261112'
BASE = 'c1ad9baa19a5b938d7976541bed27a73eee32d8c'
MAIN = '7ad8c9e7295f1575ae9108ea62c12c83b1dd4db1'
parser = argparse.ArgumentParser()
parser.add_argument('--final', action='store_true')
args = parser.parse_args()

def git(*parts):
    return subprocess.check_output(['/usr/bin/git', '-C', str(W), *parts])

def pin(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}

cohorts, scans = [], []
for root in sorted((S / 'tests').iterdir()):
    if (root / 'scanner.json').exists() and (root / 'outcome.json').exists():
        scan = json.loads((root / 'scanner.json').read_bytes())
        source = Path(json.loads((root / 'plan.json').read_bytes())['source_root'])
        violations = []
        for row in scan['violations']:
            raw = (source / row['path']).read_bytes()
            violations.append({'path': row['path'], 'line': row['line'],
                'sha256': hashlib.sha256(raw).hexdigest(),
                'byte_identical_to_base': raw == git('show', BASE + ':' + row['path'])})
        scans.append({'name': root.name, 'exit': scan['exit'], 'violations': violations,
                      'report': pin(root / 'scanner.json')})
    if not (root / 'outcome.json').exists() or not (root / 'pytest.xml').exists():
        continue
    xml = ET.parse(root / 'pytest.xml')
    outcome = json.loads((root / 'outcome.json').read_bytes())
    artifacts = []
    for name in ('final.json', 'published.json', 'actual-result.json', 'actual-failed-result.json'):
        for path in sorted((root / 'cases').rglob(name)):
            row = pin(path)
            if name != 'published.json':
                value = json.loads(path.read_bytes())
                row['result'] = {key: value.get(key) for key in (
                    'state', 'runtime_gates_passed', 'first_stop', 'publication_validation_failure', 'retained_artifacts')}
            artifacts.append(row)
    cohorts.append({'name': root.name, 'tests': len(xml.findall('.//testcase')),
        'failures': len(xml.findall('.//failure')), 'errors': len(xml.findall('.//error')),
        'returncode': outcome['returncode'], 'cleanup_verified': outcome['cleanup_verified'],
        'junit': pin(root / 'pytest.xml'), 'log': pin(root / 'pytest.log'),
        'outcome': pin(root / 'outcome.json'), 'artifacts': artifacts,
        'artifact_search': 'Path.rglob, including hidden and ignored files'})
part1 = git('rev-parse', 'codex/native-failure-record-20261112').decode().strip()
part2 = git('rev-parse', 'codex/native-incomplete-capture-retention-20261112').decode().strip() if args.final else None
protected = ['src/data_sheets_schema/shared_generation.py', 'src/data_sheets_schema/api_runner.py',
             'src/download/prompts/canonical_hashes.yaml', 'tests/utils/run_spec_boundary_contracts.json']
checks = []
for head in filter(None, (part1, part2)):
    for path in protected + ['src/data_sheets_schema/native_subscription_guard.py']:
        reference = BASE if path.endswith('native_subscription_guard.py') else MAIN
        raw, expected = git('show', head + ':' + path), git('show', reference + ':' + path)
        assert raw == expected, (head, path)
        checks.append({'commit': head, 'path': path, 'sha256': hashlib.sha256(raw).hexdigest(), 'equal_reference': reference})
details_path = S / ('final-details.json' if args.final else 'part1-details.json')
details = json.loads(details_path.read_bytes()) if details_path.exists() else {}
receipts = [pin(path) for path in sorted(S.glob('*/config-restoration.json'))]
if (S / 'failure-audit.json').exists():
    receipts.append(pin(S / 'failure-audit.json'))
value = {'part1': part1, 'part2': part2, 'base': BASE, 'cohorts': cohorts, 'scans': scans,
    'receipts': receipts, 'protected_and_guard': checks,
    'details': details, 'scope': 'Offline synthetic engineering tests. Ordinary Python fixture peers only. No native binary, provider/model call, real capture or reservation, push or GitHub write.'}
lines = ['# Helper 3: failure publication and incomplete capture retention', '',
    'Part 1: `' + part1 + '`. Part 2: ' + ('`' + part2 + '`.' if part2 else 'pending on a separate branch.'), '',
    'A publication validation failure records the validator stage, exception type and reason; forces failed state and the sticky failure gate; and pins available consumed evidence by size and SHA-256. Exact diagnostic readback cannot assert completion or acceptance. Ordinary successful results still use fresh registration, authority, subscription and gate verification.', '',
    'Design recorded before implementation: relaxing admission validation was rejected. The selected separate failure-only diagnostic route leaves successful semantic verification intact. Failure readback verifies historical bytes, not current runtime validity or authenticated authority. No registered document kind or version changes.', '',
    '| Cohort | Tests | Failures | Errors | Exit | Cleanup |', '|---|---:|---:|---:|---:|---|']
for row in cohorts:
    lines.append(f"| {row['name']} | {row['tests']} | {row['failures']} | {row['errors']} | {row['returncode']} | {row['cleanup_verified']} |")
for row in scans:
    lines += ['', f"Generation-specificity audit `{row['name']}`: exit {row['exit']}; {len(row['violations'])} violations. All flagged source files byte-identical to the accepted base: {all(v['byte_identical_to_base'] for v in row['violations'])}. This was the runner's scanner option, not the RunSpec boundary inventory. Raw report is pinned in JSON; no scanner failure is treated as passing."]
lines += ['', details.get('markdown', 'Integration verification is still in progress.'), '', value['scope']]
text = '\n'.join(lines) + '\n'
raw = json.dumps(value, indent=2) + '\n'
assert chr(64) not in raw + text
H.with_suffix('.md').write_text(text)
H.with_suffix('.json').write_text(raw)
for path in (H.with_suffix('.md'), H.with_suffix('.json')):
    print(json.dumps(pin(path)))
