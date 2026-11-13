"""Export N's environment-ruling evidence locally, 2026-11-13.

Inputs: N Git/source and saved sibling test cohorts. Output: adjacent
h3_environment_ruling_20261113.json. Never write R, import production code,
run tests or publish. Run after all cohorts finish.
"""
import ast
import hashlib
import json
import subprocess
from pathlib import Path
import xml.etree.ElementTree as ET

N = Path(__file__).resolve().parents[2]
S = N.parent / 'scratch-h3-environment-manifest-20261113/tests'
BASE = '7b851213f3492144cfd5b83d6bbd9a8a040e9132'
OUTPUT = Path(__file__).with_name('h3_environment_ruling_20261113.json')
PROTECTED = ('src/data_sheets_schema/shared_generation.py', 'src/data_sheets_schema/api_runner.py',
             'src/download/prompts/canonical_hashes.yaml', 'tests/utils/run_spec_boundary_contracts.json',
             'src/data_sheets_schema/native_subscription_guard.py')


def pin(path):
    raw = path.read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def git(*args, raw=False):
    value = subprocess.check_output(['git', '--no-replace-objects', '-C', str(N), *args])
    return value if raw else value.decode().strip()


def constant(path, name):
    for node in ast.parse(path.read_text()).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise ValueError('missing literal constant: ' + str(path) + ':' + name)


def cohort(directory, current_tree):
    plan_path, outcome_path, xml_path = (directory / name for name in ('plan.json', 'outcome.json', 'pytest.xml'))
    if plan_path.exists() and not outcome_path.exists():
        raise RuntimeError('wait for final process outcome before exporting: ' + directory.name)
    plan = json.loads(plan_path.read_text()) if plan_path.exists() else {}
    outcome = json.loads(outcome_path.read_text()) if outcome_path.exists() else None
    cases = []
    if xml_path.exists():
        for case in ET.parse(xml_path).getroot().iter('testcase'):
            failure, error, skipped = case.find('failure'), case.find('error'), case.find('skipped')
            status = 'failed' if failure is not None else 'error' if error is not None else 'skipped' if skipped is not None else 'passed'
            row = dict(name=case.get('name'), classname=case.get('classname'), status=status)
            evidence = failure if failure is not None else error
            if evidence is not None:
                row.update(message=evidence.get('message'), traceback=evidence.text)
            cases.append(row)
    counts = ({'tests': len(cases), **{key: sum(case['status'] == value for case in cases)
               for key, value in [('passed', 'passed'), ('failures', 'failed'), ('errors', 'error'), ('skipped', 'skipped')]}}
              if xml_path.exists() else None)
    interrupted = bool(outcome and (outcome.get('interrupted') or outcome.get('forced_cleanup')))
    completed = bool(outcome and outcome.get('returncode') == 0 and outcome.get('cleanup_verified') is True and not interrupted
                     and counts is not None and counts['failures'] == counts['errors'] == 0)
    status = ('interrupted_nonacceptance' if interrupted else
              'incomplete_nonacceptance' if counts is None or outcome is None else
              'passed_selected_checks' if completed else 'failed_nonacceptance')
    commit = plan.get('source_commit')
    tree = git('rev-parse', commit + ':src/data_sheets_schema') if commit else None
    names = {'plan.json', 'outcome.json', 'worker-outcome.json', 'pytest.log', 'pytest.xml',
             'bootstrap.json', 'interruption-request.json', 'origins-before.json', 'origins-after.json', 'network.json'}
    return dict(status=status, acceptance_for_selected_checks=completed,
                source_commit=commit, source_package_tree=tree,
                matches_current_package_tree=tree == current_tree if tree else None,
                counts=counts, cases=cases, outcome=outcome,
                evidence=[pin(p) for p in sorted(directory.iterdir()) if p.is_file() and p.name in names])


def builder_functions(path):
    if path.suffix != '.py':
        return []
    result = []
    for node in ast.parse(path.read_text()).body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        decorators = [ast.unparse(item) for item in node.decorator_list]
        calls = [item.func.attr if isinstance(item.func, ast.Attribute) else item.func.id
                 for item in ast.walk(node) if isinstance(item, ast.Call)
                 and isinstance(item.func, (ast.Attribute, ast.Name))]
        if (any('fixture' in item for item in decorators)
                or node.name in {'build_native_fixture', 'make_case', 'runtime_for'}
                or set(calls) & {'prepare_synthetic', 'synthetic_registration'}):
            result.append(dict(name=node.name, line=node.lineno))
    return result


def main():
    if N.name != 'codex-native-environment-manifest-20261113':
        raise RuntimeError('exporter belongs to N only')
    head = git('rev-parse', 'HEAD')
    current_tree = git('rev-parse', head + ':src/data_sheets_schema')
    tests = {p.name: cohort(p, current_tree) for p in sorted(S.iterdir()) if p.is_dir()
             and any((p / name).exists() for name in ('plan.json', 'outcome.json', 'pytest.xml'))}
    protected = {}
    for relative in PROTECTED:
        current = (N / relative).read_bytes()
        if current != git('show', BASE + ':' + relative, raw=True):
            raise ValueError('protected file differs from base: ' + relative)
        protected[relative] = hashlib.sha256(current).hexdigest()
    fixtures = [name for name in git('diff', '--name-only', BASE, 'HEAD', '--', 'tests').splitlines() if name]
    package = N / 'src/data_sheets_schema'
    kinds = []
    for filename, key in [('native_execution_registration_v2.py', 'PREPARATION_KIND'),
                          ('native_execution_registration_v2.py', 'EXECUTION_KIND'),
                          ('native_environment_manifest.py', 'KIND')]:
        path = package / filename
        kinds.append(dict(kind=constant(path, key), version=constant(path, 'VERSION'), source=pin(path)))
    manifests = []
    for path in sorted(S.glob('*/cases/test_prepare_rederives_real_na*/environment-manifest.json')):
        document = json.loads(path.read_text())
        if document.get('kind') != 'd4d_native_environment_manifest':
            raise ValueError('unexpected persisted environment control artifact')
        manifests.append({**pin(path), 'cohort': path.relative_to(S).parts[0],
                          'distribution_count': len(document['distributions']),
                          'scope': 'Persisted isolated test-environment artifact; cohort outcome is separate.'})
    passed = [case['name'] for result in tests.values()
              if result['acceptance_for_selected_checks'] and result['matches_current_package_tree']
              for case in result['cases'] if case['status'] == 'passed']
    helper = 'test_loaded_dependency_scope_preserves_manifest_and_pinned_imports'
    dispatch = 'test_dispatch_recheck_rejects_changed_environment'
    helper_status = ('fixed_targeted_verification_passed' if helper in passed and dispatch in passed
                     else 'fix_committed_targeted_verification_pending')
    findings = [
        dict(id='H3-EM1', status='fixed', finding='Discovery missed missing entire dist-info; strict import ownership census added.'),
        dict(id='H3-EM2', status='fixed', finding='Pytest rewrite bytecode was misclassified; only importable cache spellings count.'),
        dict(id='H3-EM3', status='fixed', finding='Synthetic, retention, neutral and omission fixtures needed explicit manifest migration.'),
        dict(id='H3-EM4', status='design_approved_implementation_elsewhere', finding='Reference source origin and candidate host identity needed separation.', owner_reply='Approve reference-only validation context'),
        dict(id='H3-EM5', status='production_environment_hold', finding='Primary virtualenv bootstrap lacks RECORD ownership; isolated tests add synthetic bootstrap metadata and leave primary untouched.'),
        dict(id='H3-EM6', status='fixed', finding='Metadata could change during census; captured RECORD ownership, rediscovery and directory checks close that race.'),
        dict(id='H3-EM7', status='fixed', finding='Dispatch fixture continued into unrelated synthetic authority setup; dedicated regression now omits it.'),
        dict(id='H3-EM8', status='passed_current_control' if dispatch in passed else 'verification_pending', finding='Dispatch must regenerate installed metadata even when manifest bytes are unchanged.'),
        dict(id='H3-EM9', status='corrected_selection', finding='Earlier retention selection included public launch tests; interrupted cohorts remain nonacceptance and final selectors name read-only nodes.'),
        dict(id='H3-EM10', status=helper_status, fix_commit=git('rev-parse', 'ecb628c68'),
             finding='Frozen helper imports expanded sys.path with unpinned historical code; strict census correctly refused dispatch-live-01.',
             repair='Restore caller sys.path before loaded_dependencies yields while retaining exact byte finder. No census exemption.',
             original_failure_cohort='dispatch-live-01', required_controls=[helper, dispatch]),
    ]
    record = dict(kind='h3_environment_manifest_ruling_evidence', version=1,
        status='local_environment_evidence_export_not_gate_proof', branch=git('branch', '--show-current'),
        head=head, base=BASE, source_package_tree=current_tree,
        commits=git('log', '--reverse', '--format=%H %s', BASE + '..HEAD').splitlines(),
        registered_kinds=kinds, controller_authority_version=constant(package / 'native_execution_registration_v2.py', 'AUTHORITY_VERSION'),
        changed_test_paths=fixtures,
        fixture_files=[{**pin(N / name), 'registration_builders_or_fixtures': builder_functions(N / name)} for name in fixtures if (N / name).exists()],
        tests=tests, protected_and_guard_sha256=protected, persisted_environment_manifests=manifests, findings=findings,
        bounds=pin(Path(__file__).with_name('h3_gate_bounds_20261113.json')),
        validation_context_design=pin(Path(__file__).with_name('h3_gate_validation_context_20261113.json')),
        generator=pin(Path(__file__)), limits=[
            'No aggregate total across overlapping cohorts is an acceptance claim.',
            'Interrupted, incomplete and failed cohorts remain nonacceptance.',
            'Passing cohorts establish only selected controls at their recorded source commit.',
            'RECORD hashes bind installation metadata, not newly computed hashes of every installed payload.',
            'This N exporter claims neither a gate schema nor a two-project demonstration; G supplies that evidence.',
            'No provider, model, native binary, probe, capture, reservation or publication is performed by this exporter.'])
    OUTPUT.write_text(json.dumps(record, indent=2, sort_keys=True) + '\n')
    print(json.dumps(pin(OUTPUT), sort_keys=True))


if __name__ == '__main__':
    main()
