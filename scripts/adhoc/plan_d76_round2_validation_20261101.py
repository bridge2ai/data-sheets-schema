#!/usr/bin/env python3
"""Freeze bounded PR #5213 D76 round-2 selections, 2026-11-01.

Inputs: frozen checkout, two retained reviewer probe directories, historical cohort,
optional full-collection nodes. Outputs: fresh external JSON lists and input hashes.
No test launches, source edits, GitHub or provider activity.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess


OLD_D76 = ['tests/test_wave7_5213_d76_' + name + '.py' for name in (
    'arm_paths', 'binding_records', 'legacy_registration', 'recorder', 'registration', 'relative_registration')]
NEW = ['tests/test_wave7_5213_d76_round2_binding.py', 'tests/test_wave7_5213_d76_round2_recorder.py']
CODEX = ['test_prior_adversarial.py', 'test_recheck_edges.py']
DEFECT_OBSERVATIONS = ['test_postconstruction_binding.py', 'test_postconstruction_admission.py']
CLAUDE = ['test_codex_prior_adversarial_copy.py', 'test_probe_arm_paths_more.py',
          'test_probe_sg2_corpus_root.py', 'test_probe_record_condition_cross_cwd.py',
          'test_probe_sg2_conventional_manifest.py', 'test_probe_native_source_spelling.py',
          'test_probe_sg1_instruction_cwd.py', 'test_probe_sg2_display_fast.py',
          'test_probe_recorder_residuals.py']
MATCHED = 'notes/matched_cborg_2026-09-13/'
CANARY = [MATCHED + 'native_controls/test_native_command_policy.py',
          MATCHED + 'native_controls/test_native_launch.py', 'notes/claudecode_direct/test_direct_arm.py']
AUDIT = [MATCHED + 'audit_controls/' + name for name in (
    'test_source_metadata_upgrade.py', 'test_response_buffer_selection.py',
    'test_budget_amendment_registration.py', 'test_upstream_timeout.py')]
F5_TESTS = ['tests/' + name for name in ('test_audit_recall_leak_rendered.py',
    'test_audit_recall_leak.py', 'test_audit_record_contract.py', 'test_native_phase_scope_rendering.py',
    'test_anonymous_removal_renderer.py', 'test_claim_clarification_renderer.py')]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tree', type=Path, required=True)
    parser.add_argument('--probes', type=Path, required=True, help='scratch-5213recheck/scripts/adhoc')
    parser.add_argument('--historical-targets', type=Path, required=True, help='retained exact107-node JSON list')
    parser.add_argument('--collection', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = args.tree.resolve(strict=True)
    probes = args.probes.resolve(strict=True)
    cohort = json.loads(args.historical_targets.read_text())
    if len(cohort) != 107 or len(set(cohort)) != 107:
        raise ValueError('exact107 unique historical IDs required')
    lists = {'new-regressions': NEW, 'old-d76': OLD_D76, 'historical107': cohort,
             'reviewer-codex': [str(probes / 'codex-20261101' / name) for name in CODEX],
             'reviewer-codex-defect-observations': [str(probes / 'codex-20261101' / name) for name in DEFECT_OBSERVATIONS],
             'reviewer-claude': [str(probes / 'claude-recheck-20261101' / name) for name in CLAUDE],
             'f5-notes-canary': CANARY, 'f5-notes-audit': AUDIT, 'f5-tests': F5_TESTS}
    hashes = {}
    for values in lists.values():
        for value in values:
            path = Path(value.split('::', 1)[0])
            path = path if path.is_absolute() else root / path
            if not path.is_file() or path.is_symlink():
                raise ValueError('missing or symlink target: ' + value)
            hashes[str(path)] = sha(path)
    if args.output.exists() or args.output.resolve().is_relative_to(root):
        raise ValueError('fresh external output directory required')
    args.output.mkdir(parents=True)
    for name, targets in lists.items():
        save(args.output / (name + '.json'), targets)
    data = {'head': subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip(),
            'target_counts': {name: len(values) for name, values in lists.items()},
            'target_sha256': hashes, 'historical_targets_sha256': sha(args.historical_targets),
            'notes_sessions': 'separate fresh detached trees; each uses its explicit notes-ci-job mode',
            'defect_observations': 'Original Codex probes assert the defect; retained observations are not acceptance passes.',
            'claude_print_only_limit': 'F2(a)/(b) probe prints alone are insufficient; new committed F2 regressions assert match.',
            'limits': 'No broad/heavy rerun; retain duplicate IDs and all original probe bytes.'}
    if args.collection:
        spec = importlib.util.spec_from_file_location('d76_round2_ci', root / 'utils/pytest_shard.py')
        selector = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(selector)
        nodes = json.loads(args.collection.read_text())['collected']
        ordinary = selector.partition_lanes(nodes)['ordinary']
        weights = selector.read_weights(root / 'utils/ci_test_durations.json')
        assignment = selector.balanced_files((node.split('::', 1)[0] for node in ordinary), 4, weights)
        module = 'tests/test_source_heading_runtime_api.py'
        shard = assignment[module]
        selected = [node for node in ordinary if assignment[node.split('::', 1)[0]] == shard]
        save(args.output / 'ci-ordinary-expected-nodes.json', selected)
        data['ci'] = {'shard': shard, 'total': 4, 'collection_sha256': sha(args.collection),
            'selector_sha256': sha(root / 'utils/pytest_shard.py'),
            'timings_sha256': sha(root / 'utils/ci_test_durations.json'),
            'expected_occurrences': len(selected), 'holds_module': module,
            'held_module_nodes': [node for node in selected if node.split('::', 1)[0] == module]}
    save(args.output / 'plan.json', data)
    print(json.dumps(data, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
