"""Report final manifest scope and saved offline evidence, 2026-11-13.

Inputs: N Git/source, lead addendum, previous immutable status, named census
cohorts. Output: adjacent JSON; no test, import of production code or R write.
"""
import ast
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-h3-environment-manifest-20261113/tests'
ASSIGNMENT = ROOT.parent / 'codex-development-efficiency-20261111/notes/development_efficiency_20261111/assignments/claude-lead-helper3-gate-addendum-20261113.md'
SOURCE = ROOT / 'src/data_sheets_schema/native_environment_manifest.py'
PRIOR = Path(__file__).with_name('h3_manifest_refinements_20261113.json')
OUTPUT = Path(__file__).with_name('h3_unowned_manifest_20261113.json')
BASE = '7b851213f3492144cfd5b83d6bbd9a8a040e9132'
PROTECTED = ('src/data_sheets_schema/shared_generation.py', 'src/data_sheets_schema/api_runner.py',
    'src/download/prompts/canonical_hashes.yaml', 'tests/utils/run_spec_boundary_contracts.json',
    'src/data_sheets_schema/native_subscription_guard.py')


def pin(path):
    path = Path(path)
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def read(path):
    return json.loads(Path(path).read_bytes())


def git(*args):
    return subprocess.check_output(['/usr/bin/git', '--no-replace-objects', '-C', str(ROOT), *args])


def cohort(directory):
    outcome_path = directory / 'outcome.json'
    outcome = read(outcome_path)
    xml = directory / 'pytest.xml'
    cases = []
    if xml.is_file():
        for case in ET.parse(xml).getroot().iter('testcase'):
            status = next((name for name, tag in (('failed', 'failure'), ('error', 'error'), ('skipped', 'skipped'))
                           if case.find(tag) is not None), 'passed')
            cases.append({'name': case.get('name'), 'status': status,
                          'failure_message': case.find('failure').get('message') if case.find('failure') is not None else None})
    counts = {name: sum(row['status'] == name for row in cases) for name in ('passed', 'failed', 'error', 'skipped')}
    accepted = (bool(cases) and outcome.get('returncode') == 0 and outcome.get('cleanup_verified') is True
                and not outcome.get('interrupted') and not outcome.get('forced_cleanup')
                and counts['failed'] == counts['error'] == 0)
    return {'outcome': pin(outcome_path), 'saved_outcome': outcome,
        'xml': pin(xml) if xml.is_file() else None, 'counts': counts, 'cases': cases,
        'log': pin(directory / 'pytest.log') if (directory / 'pytest.log').is_file() else None,
        'status': 'passed_selected_checks' if accepted else 'nonacceptance'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--primary-cohort', default='refinements-manifest-primary-complete-02')
    args = parser.parse_args()
    if (Path(args.primary_cohort).name != args.primary_cohort
            or not args.primary_cohort.startswith('refinements-manifest-primary-complete-')):
        raise ValueError('primary cohort must be a named owned census directory')
    text = ASSIGNMENT.read_text()
    heading = '**Scope of "import roots"**'
    scope = text[text.index(heading):text.index('Nothing has been registered on version 1')].strip()
    if 'Keep the explicit exclusions for the first-party checkout and the standard library.' not in scope:
        raise ValueError('the explicit lead scope ruling is absent')
    prior = read(PRIOR)
    if pin(PRIOR)['sha256'] != '4d2d5c8909f3f841d7be942f33f0e79e960e694908414481ff2a6a7143f16d89':
        raise ValueError('the previous policy-hold evidence was overwritten')
    version = next(ast.literal_eval(node.value) for node in ast.parse(SOURCE.read_bytes()).body
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == 'VERSION'
                                               for target in node.targets))
    if version != 1:
        raise ValueError('the lead directed manifest version 1 in place')
    cohorts = {path.name: cohort(path) for path in sorted(SCRATCH.glob('refinements-manifest-*'))}
    primary_directory = SCRATCH / args.primary_cohort
    primary_path = primary_directory / 'cases/test_primary_dependency_root_p0/primary-dependency-payload-inventory.json'
    primary = read(primary_path)
    if primary['manifest_source'] != pin(SOURCE):
        raise ValueError('the primary census used different production manifest bytes')
    rows = primary.get('distributions', primary.get('distributions_checked_before_hold', []))
    totals = {'distributions': len(rows), 'files_verified': sum(row['verified_files']['count'] for row in rows),
        'bytes_verified': sum(row['verified_files']['bytes'] for row in rows),
        'files_unverified_by_kind': {kind: sum(group['count'] for row in rows for group in row['unverified_files']
                                             if group['kind'] == kind) for kind in ('bytecode', 'other', 'record')}}
    if primary['totals'] != totals:
        raise ValueError('primary census counts do not follow from its saved rows')
    accepted = primary['complete'] and cohorts[primary_directory.name]['status'] == 'passed_selected_checks'
    manifest_pin = primary.get('manifest')
    if primary['complete']:
        if pin(manifest_pin['path']) != manifest_pin:
            raise ValueError('the saved completed manifest pin differs')
        manifest = read(manifest_pin['path'])
        if manifest['unowned_files'] != primary['unowned_files'] or manifest['excluded_roots'] != primary['excluded_roots']:
            raise ValueError('primary report does not describe the saved manifest scope')
        if primary['unowned_totals'] != {'count': len(manifest['unowned_files']),
                'bytes': sum(row['bytes'] for row in manifest['unowned_files'])}:
            raise ValueError('unowned totals do not follow from the saved manifest')
        if 'data-sheets-schema' in {row['name'] for row in manifest['distributions']}:
            raise ValueError('own project leaked into third-party inventory')
    protected = {}
    for relative in PROTECTED:
        if (ROOT / relative).read_bytes() != git('show', BASE + ':' + relative):
            raise ValueError('protected file changed: ' + relative)
        protected[relative] = pin(ROOT / relative)
    result = {'kind': 'h3_unowned_environment_manifest_ruling', 'version': 1,
        'status': 'final_scope_implemented_primary_dependency_census_complete' if accepted else 'final_scope_implemented_primary_census_nonacceptance',
        'source_head': git('rev-parse', 'HEAD').decode().strip(), 'manifest_source': pin(SOURCE),
        'source_commits': git('log', '--reverse', '--format=%H %s', 'b9527d552..HEAD').decode().splitlines(),
        'manifest_version': version, 'manifest_root_fields': ['kind', 'version', 'interpreter', 'distributions', 'unowned_files', 'excluded_roots'],
        'scope_ruling': {'assignment': pin(ASSIGNMENT), 'text': scope,
            'authority': 'Claude lead relay in the assignment; this report does not attribute it to an owner message.'},
        'historical_policy_hold': {'pin': pin(PRIOR), 'status': prior['status'],
            'disposition': 'Preserved unchanged. The later explicit Scope section resolves this earlier hold.'},
        'scope_followup': {'finding': 'The earlier bare every-file wording did not define checkout and stdlib exclusions. A provisional literal-all interpretation was superseded before code edits by the newly read explicit lead scope ruling.',
            'disposition': 'Implemented explicit exact-root exclusions with closed root/reason entries; separately listed third-party roots remain inventoried even below an excluded root.'},
        'diagnostic_followup': {'finding': 'The first final census included the helper directory pytest inserted for an adhoc test. A report-helper edit during that census changed an eligible unowned file, and the production final-identity check correctly held.',
            'preserved_cohort': 'refinements-manifest-primary-complete-01',
            'disposition': 'The diagnostic now omits and names only its own injected helper directory and isolated bootstrap prefix when describing primary dependency roots. The production collector was unchanged; the retry runs with N files frozen.'},
        'primary_dependency_census': {'evidence': pin(primary_path), 'value': primary, 'accepted': accepted,
            'bootstrap_unowned_files': [row for row in primary.get('unowned_files', [])
                                       if row['path'] in ('_virtualenv.py', '_virtualenv.pth')],
            'scope': 'Read-only borrowed primary dependency roots in an isolated CPython process with test-bootstrap metadata excluded; no claim of unchanged primary startup behavior or production registration.'},
        'cohorts': cohorts, 'cohort_scope': 'Independent saved selections; overlapping counts are not summed. Failed or interrupted cohorts retain nonacceptance.',
        'protected_and_guard_v1': {'base': BASE, 'pins': protected},
        'limitations': ['All fresh hashed RECORD entries are verified once per generate; unverified entries remain explicitly named by kind.',
            'Regular source-backed current-interpreter bytecode caches share the owned/listed-source treatment; nonstandard or sourceless caches remain explicit unowned files.',
            'Symlinked directories and non-directory import roots hold. Unowned file symlinks retain independent path and content identity.',
            'Primary environment unchanged. No native binary, probe, capture, reservation, model, network, push or GitHub write.',
            'Manifest lstat portability is fixed; no global Python 3.9 claim because protected guards remain outside this change.',
            'Old synthetic packets and earlier manifests remain historical; fresh G gate packets and demonstrations require the carried final implementation.'],
        'generator': pin(Path(__file__))}
    raw = (json.dumps(result, indent=2, sort_keys=True) + '\n').encode()
    OUTPUT.write_bytes(raw)
    if OUTPUT.read_bytes() != raw:
        raise ValueError('report did not persist')
    print(json.dumps({'report': pin(OUTPUT), 'status': result['status'], 'manifest': manifest_pin,
        'totals': primary['totals'], 'unowned_totals': primary.get('unowned_totals'),
        'bootstrap_unowned_files': result['primary_dependency_census']['bootstrap_unowned_files']}, sort_keys=True))


if __name__ == '__main__':
    main()
