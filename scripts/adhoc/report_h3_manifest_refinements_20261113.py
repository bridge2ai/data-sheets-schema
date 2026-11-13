"""Save independent manifest refinements and the unowned-root design hold.

2026-11-13. Inputs: current N source/Git, saved offline cohorts and the lead's
two assignment files. Output: adjacent JSON only; no R write, tests, package
imports, primary-environment change or native/provider execution.
"""
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
EXECUTIONS = ROOT.parent
SCRATCH = EXECUTIONS / 'scratch-h3-environment-manifest-20261113'
ASSIGNMENTS = EXECUTIONS / 'codex-development-efficiency-20261111/notes/development_efficiency_20261111/assignments'
OUTPUT = Path(__file__).with_name('h3_manifest_refinements_20261113.json')
SOURCE = ROOT / 'src/data_sheets_schema/native_environment_manifest.py'
INTERMEDIATE = '89aec8288'
BASE = '7b851213f3492144cfd5b83d6bbd9a8a040e9132'
PROTECTED = ('src/data_sheets_schema/shared_generation.py', 'src/data_sheets_schema/api_runner.py',
             'src/download/prompts/canonical_hashes.yaml', 'tests/utils/run_spec_boundary_contracts.json',
             'src/data_sheets_schema/native_subscription_guard.py')


def pin(path):
    raw = Path(path).read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def document(path):
    return json.loads(Path(path).read_bytes())


def git(*args):
    return subprocess.check_output(['/usr/bin/git', '--no-replace-objects', '-C', str(ROOT), *args])


def version(raw):
    return next(ast.literal_eval(node.value) for node in ast.parse(raw).body
                if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == 'VERSION'
                                                       for target in node.targets))


def main():
    cohorts = {}
    for directory in sorted((SCRATCH / 'tests').glob('refinements-manifest-*')):
        outcome_path = directory / 'outcome.json'
        if not outcome_path.is_file():
            raise ValueError('a manifest cohort has no final outcome: ' + str(directory))
        outcome = document(outcome_path)
        xml = directory / 'pytest.xml'
        cases = []
        if xml.is_file():
            for case in ET.parse(xml).getroot().iter('testcase'):
                failed = case.find('failure')
                error = case.find('error')
                skipped = case.find('skipped')
                status = 'failed' if failed is not None else 'error' if error is not None else 'skipped' if skipped is not None else 'passed'
                cases.append({'name': case.get('name'), 'status': status})
        counts = {name: sum(row['status'] == name for row in cases) for name in ('passed', 'failed', 'error', 'skipped')}
        accepted = (bool(cases) and outcome.get('returncode') == 0 and outcome.get('cleanup_verified') is True
                    and not outcome.get('interrupted') and not outcome.get('forced_cleanup')
                    and counts['failed'] == counts['error'] == 0)
        cohorts[directory.name] = {'outcome': pin(outcome_path), 'saved_outcome': outcome,
            'xml': pin(xml) if xml.is_file() else None, 'counts': counts, 'cases': cases,
            'status': 'passed_selected_checks' if accepted else 'nonacceptance'}
    real = SCRATCH / 'tests/refinements-manifest-real-canary-01/cases/test_one_real_installed_distri0/installed-distribution-canary.json'
    prefix = SCRATCH / 'tests/refinements-manifest-primary-prefix-01/cases/test_primary_dependency_root_p0/primary-dependency-payload-inventory.json'
    canary, primary = document(real), document(prefix)
    for value in (canary, primary):
        totals = value['totals']
        rows = [value['distribution']] if 'distribution' in value else value['distributions_checked_before_hold']
        expected = {'distributions': len(rows), 'files_verified': sum(row['verified_files']['count'] for row in rows),
            'bytes_verified': sum(row['verified_files']['bytes'] for row in rows),
            'files_unverified_by_kind': {kind: sum(group['count'] for row in rows for group in row['unverified_files'] if group['kind'] == kind)
                                       for kind in ('bytecode', 'other', 'record')}}
        if totals != expected:
            raise ValueError('saved installed-payload counts do not follow from their rows')
    old_commit = git('rev-parse', INTERMEDIATE).decode().strip()
    old_source = git('show', old_commit + ':src/data_sheets_schema/native_environment_manifest.py')
    current_version = version(SOURCE.read_bytes())
    if version(old_source) != 2 or current_version != 1:
        raise ValueError('expected branch-only v2 checkpoint followed by the lead-ruled v1 restoration')
    protected = {}
    for relative in PROTECTED:
        if (ROOT / relative).read_bytes() != git('show', BASE + ':' + relative):
            raise ValueError('protected file or guard v1 differs from the base: ' + relative)
        protected[relative] = pin(ROOT / relative)
    result = {'kind': 'h3_manifest_payload_refinements_and_design_hold', 'version': 1,
        'status': 'payload_refinements_complete_unowned_root_policy_pending',
        'source_head': git('rev-parse', 'HEAD').decode().strip(), 'manifest_source': pin(SOURCE),
        'source_package_tree': git('rev-parse', 'HEAD:src/data_sheets_schema').decode().strip(),
        'source_commits': git('log', '--reverse', '--format=%H %s', '1a466d6f6..HEAD').decode().splitlines(),
        'manifest_commits': git('log', '--reverse', '--format=%H %s', '1a466d6f6..HEAD', '--',
                               'src/data_sheets_schema/native_environment_manifest.py', 'tests/test_native_environment_manifest.py').decode().splitlines(),
        'protected_and_guard_v1': {'base': BASE, 'pins': protected},
        'manifest_format': {'current_version': current_version, 'rule': 'Lead addendum changes version 1 in place; no production registration exists.',
            'intermediate_branch_only_checkpoint': {'commit': old_commit, 'version': version(old_source),
                'source_sha256': hashlib.sha256(old_source).hexdigest()},
            'historical_evidence_locations': [str(SCRATCH), str(EXECUTIONS / 'scratch-h3-pin-gate-20261113'),
                str(EXECUTIONS / 'codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs/codex-h3-recorder-env-and-pin-comparison-20261113.json')],
            'historical_scope': 'Saved synthetic manifests and registrations exist in owned scratch outside the checkouts, and the earlier R handoff references them. The lead directed that these remain historical only. They are not production registrations; this helper performs no publication.'},
        'real_distribution_canary': {'evidence': pin(real), 'value': canary},
        'primary_dependency_payload_prefix': {'evidence': pin(prefix), 'value': primary,
            'acceptance': False, 'limitation': 'Verified entry counts are the completed payload prefix before the old unowned-file hold. No post-census recapture or final manifest was completed. Counts are RECORD entries, not a claim of unique physical files.'},
        'diagnostic_provenance': {'source': pin(ROOT / 'scripts/adhoc/check_h3_environment_payload_inventory_20261113.py'),
            'historical_execution_path': 'tests/test_native_environment_payload_inventory.py',
            'scope': 'The read-only diagnostic functions were relocated out of normal pytest discovery before commit, preserving the saved historical outcomes and node names. The census is expensive and may intentionally hold; it is not a routine CI acceptance test. Future explicit execution must retain the isolated import-root setup.'},
        'cohorts': cohorts, 'cohort_scope': 'Saved selections listed independently; overlapping counts are not summed.',
        'remaining_design_hold': {
            'question': 'Does every file under import roots retain the existing exact checkout/source and standard-library exclusions, or include those roots with explicitly defined source/output exceptions?',
            'reason': 'Including a checkout also includes generated outputs and may recursively make those outputs manifest inputs. The addendum does not specify the boundary.',
            'status': 'awaiting_explicit_user_reply_no_default_chosen',
            'tentative_closed_unowned_entry': {'root': 'physical absolute import-root identity', 'path': 'normalized relative POSIX path', 'bytes': 'integer size', 'sha256': 'content digest'},
            'not_implemented': 'No final unowned_files census or unowned-root policy is claimed. The final gate schema, packets and demonstrations remain dependent on that decision.'},
        'assignments': [pin(ASSIGNMENTS / name) for name in ('claude-lead-helper3-gate-refinements-20261113.md', 'claude-lead-helper3-gate-addendum-20261113.md')],
        'limitations': ['Primary environment unchanged.', 'No native binary, probe, capture, reservation, model call, network, push or GitHub write by this manifest task.',
            'Manifest lstat portability was fixed; protected guards still prevent a global Python 3.9 support claim.'],
        'generator': pin(Path(__file__))}
    raw = (json.dumps(result, indent=2, sort_keys=True) + '\n').encode()
    OUTPUT.write_bytes(raw)
    if OUTPUT.read_bytes() != raw:
        raise ValueError('manifest refinement status did not persist')
    print(json.dumps(pin(OUTPUT), sort_keys=True))


if __name__ == '__main__':
    main()
