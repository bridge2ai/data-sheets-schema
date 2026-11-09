#!/usr/bin/env python3
"""Summarize U4b offline validation and failure evidence, 2026-11-08.

Inputs: explicit retained run directories and this committed checkout. Output:
one new JSON manifest in assigned U4b scratch, with every nonpassing node,
original trace, artifact digest, source head and latest-node disposition.
No tests, native programs, providers or network operations are executed.
"""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-native-u4b'
BASE = '8ac918c603b2172c014b112affdce26a6c8899f6'
spec = importlib.util.spec_from_file_location('u4b_evidence_base',
    ROOT / 'scripts/adhoc/summarize_native_u5_prep_20261108.py')
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
base.SCRATCH = SCRATCH
UNCHANGED = (
    'src/data_sheets_schema/shared_generation.py',
    'src/data_sheets_schema/api_runner.py',
    'src/download/prompts/canonical_hashes.yaml',
    'tests/utils/run_spec_boundary_contracts.json',
    'src/data_sheets_schema/native_subscription_guard.py',
    'src/data_sheets_schema/native_execution.py',
    'src/data_sheets_schema/native_execution_registration.py',
)


def classify(run, node, message, trace):
    text = message + '\n' + trace
    if (run == 'a4-focused1'
            and node == 'tests.test_native_u4b_a4_cross_word::test_saved_word_a_guard_refuses_recorded_word_b_before_dispatch'
            and '_git_read' in text and 'cross-word refusal started another process' in text):
        return 'corrected_A4_capture_fixture_global_Popen_interception'
    if (run == 'a4-focused1'
            and node == 'tests.test_native_u4b_audit_counts::test_stated_severity_mismatch_refuses_without_a_stated_total'
            and "Findings: 2 high." in text and 'assert True is False' in text):
        return 'corrected_A4_test_uses_existing_explicit_global_summary_grammar'
    if (run == 'a4-u4-final' and node.startswith((
            'tests.test_native_subscription_capture::', 'tests.test_native_u4b_capture_retries::',
            'tests.test_native_u4b_addendum_authority::', 'tests.test_native_u4b_a3_captures::'))
            and ('_git_read' in text or 'registration_commit_for' in text)
            and ('Popen' in text or 'RecursionError' in text)):
        return 'corrected_A4_capture_fixture_global_Popen_interception'
    if (run == 'a3-u4-final' and node in {
            'tests.test_native_u4b_addendum_authority::test_saved_guard_readback_rechecks_context_even_after_hashes_are_rebound[runtime]',
            'tests.test_native_u4b_addendum_authority::test_saved_guard_readback_rechecks_context_even_after_hashes_are_rebound[both]'}
            and 'Regex pattern did not match' in text
            and 'subscription runtime differs from registered runtime bytes' in text):
        return 'corrected_A3_stronger_registered_runtime_refusal_diagnostic'
    if (run == 'a2-focused-c3088487c'
            and node == 'tests.test_native_u4b_admission::test_rehashed_guard_cannot_substitute_owner_or_capture[capture_manifest]'
            and 'FileNotFoundError' in text and '/one-capture/capture.json' in text):
        return 'corrected_A2_numbered_capture_manifest_test_path'
    if 'native renderer requires the sole captured runtime declaration before composition' in text:
        return 'inherited_R9_3_captured_runtime_class_identity'
    if 'shared selector call guards/order changed' in text:
        return 'protected_shared_selector_constructor_proof'
    if (node == 'tests.test_native_shared_render::test_native_construction_and_replay_use_validated_shared_admission'
            and 'assert [] == [1, 1]' in text):
        return 'protected_native_constructor_admission_hook'
    alias = 'typed_audit.py:311' in text and 'nested or copied receiver alias' in text
    if node.startswith('tests.test_native_u5_scanner_comparison::'):
        if alias and '"before":' in text and '"after":' in text and '"returncode": 2' in text:
            return 'complete_input_comparison_blocked_by_incomplete_derivation'
        return 'UNCLASSIFIED'
    if alias:
        return 'typed_audit_container_alias_proof'
    if run == 'u4b-components-1' and "KeyError: 'run_native_canary'" in text:
        return 'corrected_U4b_R8_receipt_fixture_capability_map'
    if run == 'u4-cohort' and "KeyError: 'runtime'" in text:
        return 'corrected_U4b_R9_legacy_parser_lookup'
    if (run == 'u5-core'
            and node == 'tests.test_native_u5_external_schema::test_same_external_320_api_instruction_before_after'
            and 'render source must be the assigned candidate or pinned baseline' in text):
        return 'corrected_U4b_R12_API_helper_scratch_root'
    return 'UNCLASSIFIED'


def file_identity(path):
    return {'path': str(path), 'bytes': path.stat().st_size, 'sha256': base.sha(path)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--compare', type=Path,
                        help='Prior retained manifest: compare exact nonpassing node/state/group identities')
    parser.add_argument('runs', nargs='+')
    args = parser.parse_args()
    output = args.output.absolute()
    if (output.parent != SCRATCH or output.resolve() != output or os.path.lexists(output)
            or len(set(args.runs)) != len(args.runs)):
        raise ValueError('require new literal output and unique explicit runs in assigned scratch')
    runs, latest, failures, groups = [], {}, [], Counter()
    for name in args.runs:
        run = base.summarize(name)
        junit = SCRATCH / name / 'pytest.xml'
        if not junit.is_file():
            raise ValueError('missing completed JUnit evidence: ' + name)
        for case in ET.parse(junit).getroot().iter('testcase'):
            node = case.get('classname', '') + '::' + case.get('name', '')
            state, detail = 'passed', None
            for tag, label in (('failure', 'failed'), ('error', 'errors'), ('skipped', 'skipped')):
                detail = case.find(tag)
                if detail is not None:
                    state = label
                    break
            row = {'node': node, 'state': state, 'run': name,
                   'head': run['source_stability']['before']['head']}
            if detail is not None:
                message, trace = detail.get('message', ''), detail.text or ''
                group = classify(name, node, message, trace)
                row.update(group=group, message=message, trace=trace)
                failures.append(row)
                groups[group] += 1
            latest[node] = row
        run['evidence_checks'] = {
            'source_unchanged_and_clean': run['source_stability']['unchanged'] is True
                and run['source_stability']['before']['status'] == ''
                and run['source_stability']['after']['status'] == '',
            'observed_cleanup': run['outcome']['cleanup_verified'] is True
                and not run['outcome']['forced_cleanup']
                and not run['outcome']['interrupted']
                and not run['outcome']['observation_errors']
                and not run['outcome']['observed_surviving_pids'],
            'bootstrap_origin_checks': json.loads((SCRATCH / name / 'worker-outcome.json').read_bytes())
                ['source_origin_checks_passed'] is True,
            'network_denied': json.loads((SCRATCH / name / 'network.json').read_bytes())
                ['network_bind_denied'] is True,
            'under_3600_seconds': run['outcome']['seconds'] < 3600,
        }
        runs.append(run)
    unchanged = {}
    for path in UNCHANGED:
        old = subprocess.check_output(['/usr/bin/git', '--no-replace-objects', 'show', BASE + ':' + path],
            cwd=ROOT, env=base.ENV, timeout=30)
        current = (ROOT / path).read_bytes()
        unchanged[path] = {'base_sha256': hashlib.sha256(old).hexdigest(),
            'current_sha256': hashlib.sha256(current).hexdigest(), 'equal': old == current}
    exports = {str(path.relative_to(SCRATCH)): file_identity(path)
               for path in sorted(SCRATCH.glob('*/manifest.json')) if path.is_file()}
    api = {str(path.relative_to(SCRATCH)): file_identity(path)
           for path in sorted((SCRATCH / 'api-comparison-canary/cases').glob('**/instruction.txt'))}
    fresh_comparisons = {}
    for name in args.runs:
        cases = SCRATCH / name / 'cases'
        # Exact test roles, numeric pytest instances only; do not follow the
        # sibling "current" aliases or confuse historical comparison inputs.
        paths = list(cases.glob('popen-*/test_scanner_before_after_reta[0-9]*/scanner-comparison.json'))
        for side in ('before', 'after'):
            paths.extend(cases.glob('popen-*/test_same_external_320_api_ins[0-9]*/'
                                    + side + '/instruction.txt'))
        fresh_comparisons[name] = [file_identity(path) for path in sorted(paths)]
    for row in failures:
        row['latest_state'] = latest[row['node']]['state']
        row['latest_run'] = latest[row['node']]['run']
    prior_comparison = None
    if args.compare is not None:
        prior_path = args.compare.absolute()
        if prior_path.parent != SCRATCH or prior_path.resolve() != prior_path:
            raise ValueError('comparison manifest must be a literal file in assigned scratch')
        with prior_path.open('rb') as stream:
            prior_raw = stream.read(16_000_001)
        if not 0 < len(prior_raw) <= 16_000_000:
            raise ValueError('comparison manifest exceeds its byte bound')
        prior = json.loads(prior_raw)
        old = {row['node']: {'state': row['state'], 'group': row['group']}
               for row in prior['latest_nonpassing']}
        current = {row['node']: {'state': row['state'], 'group': row['group']}
                   for row in latest.values() if row['state'] != 'passed'}
        prior_comparison = {
            'prior_manifest': {'path': str(prior_path), 'bytes': len(prior_raw),
                               'sha256': hashlib.sha256(prior_raw).hexdigest()},
            'same_nonpassing_node_state_group': old == current,
            'prior_count': len(old), 'current_count': len(current),
            'new_or_changed': [{'node': node, 'prior': old.get(node), 'current': row}
                               for node, row in sorted(current.items()) if old.get(node) != row],
            'no_longer_nonpassing': sorted(set(old) - set(current)),
            'scope': 'Exact node/state/classification identities, not byte-equal traces or native acceptance.'}
    result = {'kind': 'native_u4b_validation_evidence', 'version': 1,
        'base': BASE, 'head': base.git('rev-parse', 'HEAD'),
        'status': base.git('status', '--porcelain', '--untracked-files=all'),
        'generator': file_identity(Path(__file__)), 'runs': runs,
        'failure_occurrence_groups': dict(groups), 'nonpassing_history': failures,
        'latest_named_counts': dict(Counter(row['state'] for row in latest.values())),
        'latest_nonpassing': [row for row in latest.values() if row['state'] != 'passed'],
        'unchanged_files': unchanged, 'export_manifests': exports, 'api_instruction_parity_inputs': api,
        'fresh_comparison_artifacts': fresh_comparisons,
        'prior_nonpassing_comparison': prior_comparison,
        'scope': 'Offline preparation; overlapping cohorts, not native acceptance. '
                 'Bootstrap origin witnesses do not enumerate every xdist worker import. '
                 'Cleanup is limited to observed PID/creation-time descendants.'}
    encoded = (json.dumps(result, sort_keys=True, indent=2) + '\n').encode()
    with output.open('xb') as stream:
        stream.write(encoded)
    summary = {'path': str(output), 'sha256': hashlib.sha256(encoded).hexdigest(),
        'head': result['head'], 'latest_named_counts': result['latest_named_counts'],
        'failure_occurrence_groups': dict(groups),
        'prior_nonpassing_comparison': prior_comparison,
        'runs': [{'name': run['name'], 'counts': run['counts'], 'checks': run['evidence_checks']}
                 for run in runs]}
    print(json.dumps(summary, sort_keys=True))
    if ('UNCLASSIFIED' in groups or result['status'] or not all(x['equal'] for x in unchanged.values())
            or not all(all(run['evidence_checks'].values()) for run in runs)):
        raise SystemExit('evidence retained; unresolved classification/scope/witness check')


if __name__ == '__main__':
    main()
