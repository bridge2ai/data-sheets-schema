#!/usr/bin/env python3
"""2026-11-12 retention: audit actual saved failed outputs and source invariants.
Inputs: own branches and synthetic regression artifacts; outputs: JSON audit and final handoff details.
No runtime imports, execution, publication or changes to saved test evidence.
"""
import ast
import hashlib
import json
from pathlib import Path
import subprocess

W = Path(__file__).resolve().parents[2]
S = W.parent / 'scratch-h3-failure-record-20261112'
BASE = 'c1ad9baa19a5b938d7976541bed27a73eee32d8c'
def git(*args):
    return subprocess.check_output(['/usr/bin/git', '-C', str(W), *args])
def sha(raw):
    return hashlib.sha256(raw).hexdigest()
def pin(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': sha(raw)}
source = {}
tested = S / 'retention-c/tree'
for name in ('native_execution_orchestration.py', 'native_shared_results_orchestration.py'):
    relative = Path('src/data_sheets_schema') / name
    assert (W / relative).read_bytes() == (tested / relative).read_bytes()
def normalize_inventory(raw):
    tree = ast.parse(raw)
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                    and node.name == 'list_retained_records')
    found = False
    for node in function.body:
        if isinstance(node, ast.If) and ast.unparse(node.test) == "'retained_artifacts' not in final":
            node.body = [ast.Pass()]
            found = True
    assert found
    return ast.dump(tree, include_attributes=False)
relative = Path('src/data_sheets_schema/native_shared_results.py')
assert normalize_inventory((W / relative).read_bytes()) == normalize_inventory((tested / relative).read_bytes())
for name, needles in {
    'native_shared_results_orchestration.py': ["'provenance'", 'def incomplete_capture'],
    'native_shared_phase.py': ['def _final_checks', "if kind == 'final_receipts'", "elif kind == 'recorder'"],
    'native_shared_controller_orchestration.py': ["'phase_history': self.phase.report"],
}.items():
    path = 'src/data_sheets_schema/' + name
    raw = git('show', BASE + ':' + path)
    source[path] = {'base_sha256': sha(raw), 'lines': [
        {'line': number, 'text': line.strip()}
        for number, line in enumerate(raw.decode().splitlines(), 1) if any(needle in line for needle in needles)]}
for path in ('src/data_sheets_schema/native_shared_phase.py', 'src/data_sheets_schema/native_subscription_guard.py'):
    assert (W / path).read_bytes() == git('show', BASE + ':' + path)
actual = []
for path in sorted((S / 'tests/retention-regression/cases').rglob('actual-failed-result.json')):
    value = json.loads(path.read_bytes())
    assert value['state'] == 'failed' and value['runtime_gates_passed'] is False
    assert value['scientific_acceptance'] == 'not_assessed'
    retained = value['retained_artifacts']
    copies = []
    for name, row in retained.items():
        if row['kept']:
            saved = pin(Path(row['retained_path']))
            assert (saved['bytes'], saved['sha256']) == (row['bytes'], row['sha256'])
            copies.append({'role': name, **saved})
        else:
            assert row['reason']
    assert all(retained[name]['kept'] for name in ('full', 'core', 'phase_report'))
    actual.append({'result': pin(path), 'copies': copies, 'retained_artifacts': retained})
assert actual, 'actual synthetic retention regression artifact required'
ordinary_paths = list((S / 'tests/existing-regression/cases').rglob('actual-failed-result.json'))
assert len(ordinary_paths) == 1
ordinary = json.loads(ordinary_paths[0].read_bytes())
assert ordinary['state'] == 'failed' and ordinary['runtime_gates_passed'] is False
assert 'publication_validation_failure' not in ordinary, 'ordinary failure unexpectedly used diagnostic readback'
compositions = []
for path in sorted(S.glob('*/composition.json')):
    value = json.loads(path.read_bytes())
    restoration = path.parent / 'config-restoration.json'
    backup = path.parent / 'tree/.git/config.bak-h3-failure-20261112'
    if backup.exists():
        assert restoration.exists(), 'own private CI config has not been restored: ' + str(path.parent)
        assert (backup.parent / 'config').read_bytes() == backup.read_bytes()
    compositions.append({'receipt': pin(path), 'status': value['status'],
        'restoration': pin(restoration) if restoration.exists() else None})
plan_ref = '7ad8c9e7295f1575ae9108ea62c12c83b1dd4db1'
plan_raw = git('show', plan_ref + ':notes/generic_v10_analysis_plan.md')
plan_lines = plan_raw.decode().splitlines()
out = {'source_reading': source, 'phase_rules_and_guard_v1_unchanged': True,
       'analysis_plan': {'commit': plan_ref, 'sha256': sha(plan_raw), 'lines': [
           {'line': number, 'text': plan_lines[number - 1]} for number in (799, 800, 1163)]},
       'integration_source_unchanged_except_unit_tested_complete_capture_inventory_branch': True,
       'actual_failed_retention': actual, 'compositions': compositions,
       'ordinary_failure_used_original_semantic_readback': pin(ordinary_paths[0]),
       'scope': 'Synthetic file/phase evidence only; no native/model/provider execution or acceptance.'}
target = S / 'retention-audit.json'; target.write_text(json.dumps(out, indent=2) + '\n')
print(json.dumps(pin(target)))
cohorts = {}
for name in ('part1-runtime-retry', 'retention-regression', 'retention-final-unit', 'existing-regression', 'runspec-boundary'):
    receipt = S / 'tests' / name / 'outcome.json'
    outcome = json.loads(receipt.read_bytes())
    assert outcome['returncode'] == 0 and outcome['cleanup_verified'] is True, name
    cohorts[name] = pin(receipt)
details_path = S / 'final-details.json'
details = json.loads(details_path.read_bytes())
details['verification_status'] = 'Required final cohorts passed; earlier failures retained and explained.'
details['verified_final_cohorts'] = cohorts
details['retention_audit'] = pin(target)
details['markdown'] += ('\n\nThe inventory reader also covers final_full/final_core projections from an existing complete capture when a later failure stopped the attempt. That final fallback and its tamper refusal were tested in the final unit cohort. The audit verifies the public-finalizer source is unchanged from the passing integration composition except for that separately unit-tested inventory branch. All private CI configuration edits have been restored byte-for-byte, with saved restoration receipts. The ordinary failed readback, existing saved-capture regressions and RunSpec inventory passed. Full CI and a successful native generation were not run or claimed.')
details_path.write_text(json.dumps(details, indent=2) + '\n')
print(json.dumps(pin(details_path)))
