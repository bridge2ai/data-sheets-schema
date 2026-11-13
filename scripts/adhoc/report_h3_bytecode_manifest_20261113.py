"""Report the lead's .pyc ruling from saved offline proofs, 2026-11-13.

Inputs: final N source, lead addendum, named canary/unit/primary census cohorts.
Output: a new adjacent JSON; historical reports are read and never overwritten.
No production import, test launch, primary environment mutation or R write.
"""
import argparse
import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HELPER = Path(__file__).with_name('report_h3_unowned_manifest_20261113.py')
helper_raw = HELPER.read_bytes()
helper = {'__name__': 'fixed_bytecode_report_helpers', '__file__': str(HELPER)}
exec(compile(helper_raw, str(HELPER), 'exec'), helper)
pin, read, git, cohort = (helper[name] for name in ('pin', 'read', 'git', 'cohort'))
SCRATCH, ASSIGNMENT, SOURCE = (helper[name] for name in ('SCRATCH', 'ASSIGNMENT', 'SOURCE'))
HISTORICAL = Path(__file__).with_name('h3_unowned_manifest_20261113.json')
OUTPUT = Path(__file__).with_name('h3_bytecode_manifest_20261113.json')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--primary-cohort', default='refinements-bytecode-primary-01')
    args = parser.parse_args()
    if Path(args.primary_cohort).name != args.primary_cohort or not args.primary_cohort.startswith('refinements-bytecode-primary-'):
        raise ValueError('primary cohort must be a named owned bytecode census')
    ruling = ASSIGNMENT.read_text()
    start = ruling.index('1. **Bytecode.**')
    bytecode_ruling = ruling[start:ruling.index('2. **Paths', start)].strip()
    if 'neither listed nor counted' not in bytecode_ruling:
        raise ValueError('the explicit lead bytecode ruling is absent')
    prior = pin(HISTORICAL)
    if prior['sha256'] != 'a4e07d0d6a53d0c5502598eb73bdf7f7d02146a47d2435c227e59fc92dbdfd0e':
        raise ValueError('historical unowned census evidence was overwritten')
    version = next(ast.literal_eval(node.value) for node in ast.parse(SOURCE.read_bytes()).body
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == 'VERSION'
                                               for target in node.targets))
    if version != 1:
        raise ValueError('manifest version must remain 1 in place')
    cohorts = {path.name: cohort(path) for path in sorted(SCRATCH.glob('refinements-bytecode-*'))}
    primary_path = SCRATCH / args.primary_cohort / 'cases/test_primary_dependency_root_p0/primary-dependency-payload-inventory.json'
    primary = read(primary_path)
    if primary['manifest_source'] != pin(SOURCE):
        raise ValueError('primary census used different manifest source bytes')
    if primary.get('complete') is not True or cohorts[args.primary_cohort]['status'] != 'passed_selected_checks':
        raise ValueError('primary bytecode census did not complete cleanly')
    manifest_pin = primary['manifest']
    if pin(manifest_pin['path']) != manifest_pin:
        raise ValueError('final saved manifest bytes differ from their pin')
    manifest = read(manifest_pin['path'])
    if manifest['version'] != 1 or manifest['distributions'] != primary['distributions']:
        raise ValueError('primary report differs from the saved final manifest')
    if any(path.endswith('.pyc') for row in manifest['distributions']
           for group in row['unverified_files'] for path in group['paths']):
        raise ValueError('excluded pyc entry leaked into an unverified inventory')
    if any(row['path'].endswith('.pyc') for row in manifest['unowned_files']):
        raise ValueError('excluded pyc entry leaked into the unowned inventory')
    totals = {'distributions': len(manifest['distributions']),
        'files_verified': sum(row['verified_files']['count'] for row in manifest['distributions']),
        'bytes_verified': sum(row['verified_files']['bytes'] for row in manifest['distributions']),
        'files_unverified_by_kind': {kind: sum(group['count'] for row in manifest['distributions']
            for group in row['unverified_files'] if group['kind'] == kind)
            for kind in ('bytecode', 'other', 'record')}}
    unowned_totals = {'count': len(manifest['unowned_files']),
                     'bytes': sum(row['bytes'] for row in manifest['unowned_files'])}
    if primary['totals'] != totals or primary['unowned_totals'] != unowned_totals:
        raise ValueError('saved primary totals do not follow from manifest rows')
    required = ('refinements-bytecode-canary-01', 'refinements-bytecode-unit-01', args.primary_cohort)
    if any(cohorts[name]['status'] != 'passed_selected_checks' for name in required):
        raise ValueError('required bytecode check lacks an accepted saved outcome')
    diagnostic = SCRATCH / required[0] / 'cases/test_pyc_creation_change_and_r0/bytecode-diagnostics.json'
    if read(diagnostic) != [
            {'state': 'created', 'pyc_files': 4, 'manifest_unchanged': True},
            {'state': 'changed', 'pyc_files': 4, 'manifest_unchanged': True},
            {'state': 'removed', 'pyc_files': 0, 'manifest_unchanged': True}]:
        raise ValueError('bytecode canary lacks its persisted lifecycle observations')
    protected = {}
    for name in helper['PROTECTED']:
        if (ROOT / name).read_bytes() != git('show', helper['BASE'] + ':' + name):
            raise ValueError('protected file changed: ' + name)
        protected[name] = pin(ROOT / name)
    result = {'kind': 'h3_bytecode_environment_manifest_ruling', 'version': 1,
        'status': 'pyc_exclusion_implemented_primary_dependency_census_complete',
        'source_head': git('rev-parse', 'HEAD').decode().strip(), 'manifest_source': pin(SOURCE),
        'manifest_tests': pin(ROOT / 'tests/test_native_environment_manifest.py'),
        'source_commits': git('log', '--reverse', '--format=%H %s', '971df6404a97585b6c513760d827ffd5f71bc73a..HEAD').decode().splitlines(),
        'lead_ruling': {'assignment': pin(ASSIGNMENT), 'text': bytecode_ruling,
            'authority': 'Claude lead assignment, added 2026-11-13T08:26:25Z'},
        'historical_census': {'pin': prior, 'disposition': 'Retained unchanged; its cache counts predate this ruling.'},
        'manifest_version': version, 'shape_changed': False,
        'bytecode_policy': {'excluded_suffix': '.pyc', 'case_sensitive': True,
            'hashed_record_payloads_verified': False, 'pinned_counts_include_pyc': False,
            'record_metadata': 'Exact installed RECORD bytes remain pinned; changing a RECORD row changes its metadata pin.',
            'legacy_pyo': 'Existing verification/inventory treatment is unchanged.',
            'concurrent_mutation': 'Directory, metadata and non-bytecode payload race checks remain fail-closed.'},
        'bytecode_diagnostics_outside_manifest': {'evidence': pin(diagnostic), 'observations': read(diagnostic)},
        'primary_dependency_census': {'evidence': pin(primary_path), 'value': primary,
            'manifest': manifest_pin, 'totals': totals, 'unowned_totals': unowned_totals,
            'bootstrap_unowned_files': [row for row in manifest['unowned_files']
                                       if row['path'] in ('_virtualenv.py', '_virtualenv.pth')]},
        'cohorts': cohorts, 'cohort_scope': 'Independent saved selections; overlapping counts are not summed.',
        'protected_and_guard_v1': {'base': helper['BASE'], 'pins': protected},
        'limitations': ['Census reads borrowed primary dependency roots in an isolated CPython process; no primary startup or production-registration claim.',
            'No primary environment modification, native binary, probe, capture, reservation, model, network, push or GitHub write.',
            'The bytecode exclusion does not exempt source, metadata, pth or other unowned files.',
            'Old synthetic packets remain historical; G must carry this implementation before fresh rehearsal.'],
        'generator': pin(Path(__file__)), 'report_helper': pin(HELPER)}
    raw = (json.dumps(result, indent=2, sort_keys=True) + '\n').encode()
    with OUTPUT.open('xb') as stream:
        stream.write(raw)
    if OUTPUT.read_bytes() != raw:
        raise ValueError('bytecode report did not persist')
    print(json.dumps({'report': pin(OUTPUT), 'manifest': manifest_pin, 'totals': totals,
                      'unowned_totals': unowned_totals}, sort_keys=True))


if __name__ == '__main__':
    main()
