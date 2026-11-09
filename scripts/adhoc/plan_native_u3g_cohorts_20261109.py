#!/usr/bin/env python3
"""Plan U3-G's sequential offline validation cohorts, 2026-11-09 (#5653).

Inputs: retained U4b/A5 and final U3-F2 pytest-command.json files, this committed
checkout or an explicit private composition, and a dependency-venv interpreter.
Output: JSON on stdout (or a fresh explicitly named U3-G scratch JSON file).
This helper never imports project code, launches a process, or executes tests.
Historical counts/durations describe old runs, not acceptance of the new tree.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
import os
from pathlib import Path
import re
import shlex

ROOT = Path(__file__).resolve().parents[2]
EXECUTIONS = next(parent for parent in ROOT.parents if parent.name == 'd4d-executions')
RUNNER = 'scripts/adhoc/run_native_u3g_20261109.py'
EXCLUDED = (
    'tests/test_native_shared_execution.py::test_actual_public_correction_three_workers_and_saved_completion',
    'tests/test_native_shared_execution_variant.py::test_actual_public_merged_omissions_and_all_chunk_statuses',
)
CANARY = 'tests/test_native_generation_frontdoor.py::test_validate_probe_uses_saved_bytes_and_never_runs_a_producer'
U4B_EXTRA = (
    'tests/test_native_subscription_guard_v2.py',
    'tests/test_native_subscription_capture.py',
    'tests/test_native_launch_review.py',
    'tests/test_native_model_aliases.py',
    'tests/test_native_receipt_unopened.py',
    'tests/test_native_shared_permissions.py',
)
# A5's driver explicitly used these retained A4 commands without changing nodes.
U4B_COMMANDS = {
    'u4': ('a4-u4-final', 734.686),
    'u5-core': ('a4-u5-core', 85.641),
    'u5-typed': ('a4-u5-typed', 8.147),
    'u5-receipts': ('a4-u5-receipts', 53.778),
    'u5-specificity': ('a4-u5-specificity', 722.248),
    'u5-delegated': ('a4-u5-delegated', 58.454),
    'u5-registration': ('a4-u5-registration-control', 205.791),
    'u5-readback': ('a4-u5-readback-control', 74.216),
    'u5-scanner': ('a4-u5-scanner-final', 66.550),
}
F2_COMMANDS = {
    'f2-core': ('render-contracts-scoped', 108.720),
    'f2-delegated': ('delegated-scoped', 83.669),
    'f2-specificity': ('specificity-scoped', 297.035),
    'parity-canary': ('parity-composed-canary', None),
    'parity': ('parity-composed', 26.325),
}
ORDER = ('canary', 'u4', 'u4b', 'neutral', 'u5-core', 'u5-typed',
         'u5-receipts', 'u5-specificity', 'u5-delegated', 'u5-registration',
         'u5-readback', 'u5-scanner', 'd114', 'f2-core', 'f2-delegated',
         'f2-specificity', 'parity-canary', 'parity')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def file_identity(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': digest(raw)}


def historical_nodes(path):
    raw = path.read_bytes()
    value = json.loads(raw)
    args = value.get('args')
    if not isinstance(args, list) or not all(isinstance(arg, str) for arg in args):
        raise ValueError('historical command has no string args array: ' + str(path))
    nodes = [arg for arg in args if arg.startswith('tests/')]
    if not nodes or len(nodes) != len(set(nodes)):
        raise ValueError('historical command has missing/duplicate test selectors: ' + str(path))
    return nodes, {'path': str(path), 'bytes': len(raw), 'sha256': digest(raw),
                   'original_args': args, 'historical_selectors': nodes}


def roster(name, source):
    historical = None
    seconds = None
    additions = []
    if name in U4B_COMMANDS:
        run, seconds = U4B_COMMANDS[name]
        nodes, historical = historical_nodes(
            EXECUTIONS / 'scratch-native-u4b' / run / 'pytest-command.json')
        if name == 'u4':
            additions = ['tests/test_native_shared_callback_preloading.py']
    elif name in F2_COMMANDS:
        run, seconds = F2_COMMANDS[name]
        nodes, historical = historical_nodes(EXECUTIONS / 'scratch-native-u1u3' /
            'u3f2' / run / 'pytest-command.json')
    elif name == 'canary':
        nodes = [CANARY]
    elif name == 'u4b':
        old_nodes, historical = historical_nodes(EXECUTIONS /
            'scratch-native-u4b/a5-u4b/pytest-command.json')
        nodes = sorted(str(path.relative_to(source))
            for path in (source / 'tests').glob('test_native_u4b_*.py'))
        if not nodes:
            raise ValueError('current U4b file roster is empty')
        nodes += list(U4B_EXTRA)
        historical['current_roster_additions'] = sorted(set(nodes) - set(old_nodes))
        historical['current_roster_removals'] = sorted(set(old_nodes) - set(nodes))
        if historical['current_roster_removals']:
            raise ValueError('current U4b roster drops historical selectors')
        seconds = 539.922
    elif name == 'neutral':
        nodes, historical = historical_nodes(EXECUTIONS /
            'scratch-native-u4b/a5r2-neutral/pytest-command.json')
        seconds = 94.403
    elif name == 'd114':
        nodes = ['tests/test_native_u4b_a5_producer_integration.py']
    else:
        raise ValueError('unknown cohort: ' + name)
    nodes = list(nodes) + additions
    if len(nodes) != len(set(nodes)):
        raise ValueError('duplicate selectors inside cohort: ' + name)
    for node in nodes:
        relative = node.split('::', 1)[0]
        if '..' in Path(relative).parts or not relative.startswith('tests/'):
            raise ValueError('unsafe test selector: ' + node)
        if not (source / relative).is_file():
            raise ValueError('selected test file is absent: ' + str(source / relative))
        # The inherited runner accepts test selectors only, not arbitrary pytest
        # flags. Keep the exact excluded nodes out even under file-wide selection.
        if any(node == item or relative == item.split('::', 1)[0] for item in EXCLUDED):
            raise ValueError('cohort would include an out-of-scope completion case: ' + node)
    return {'nodes': nodes, 'historical_command': historical,
            'additional_selectors': additions,
            'historical_supervisor_seconds': seconds,
            'duration_scope': 'Historical comparison only; not a new timing or acceptance result.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, default=ROOT,
        help='Worktree or explicit private composition containing the U3-G runner.')
    parser.add_argument('--python', type=Path,
        default=EXECUTIONS.parent / 'data-sheets-schema/.venv/bin/python',
        help='Dependency venv interpreter; retain its venv spelling, not resolved binary.')
    parser.add_argument('--label', default='worktree', help='Fresh output prefix for this source.')
    parser.add_argument('--cohorts', nargs='+', choices=ORDER, default=list(ORDER))
    parser.add_argument('--output', type=Path, help='Optional fresh JSON under assigned u3g scratch.')
    args = parser.parse_args()
    source = args.source_root
    if (not source.is_absolute() or source.resolve(strict=True) != source
            or not source.is_relative_to(EXECUTIONS)):
        parser.error('--source-root must be a physical absolute directory inside d4d-executions')
    if not args.python.is_absolute() or not args.python.is_file():
        parser.error('--python must name an existing absolute dependency-venv interpreter')
    if not (args.python.parent.parent / 'pyvenv.cfg').is_file():
        parser.error('--python must retain its dependency-venv path')
    if re.fullmatch(r'[a-z0-9][a-z0-9-]*', args.label) is None:
        parser.error('--label must be a lowercase literal path component')
    if len(args.cohorts) != len(set(args.cohorts)):
        parser.error('duplicate cohort names are not allowed')
    selected = set(args.cohorts)
    names = [name for name in ORDER if name in selected]
    evidence = EXECUTIONS / 'scratch-native-u1u3/u3g'
    runner = source / RUNNER
    runner_identity = file_identity(runner)
    groups = []
    exact_coverage = defaultdict(list)
    file_coverage = defaultdict(list)
    test_identities = {}
    for name in names:
        group = roster(name, source)
        destination = evidence / (args.label + '-' + name)
        environment = {'U3F_PARITY': '1'} if name.startswith('parity') else {}
        argv = [str(args.python), '-S', '-P', '-B', str(runner), '--out',
                str(destination), '--workers', '2', *group['nodes']]
        command = (['/usr/bin/env', 'U3F_PARITY=1'] if environment else []) + argv
        prerequisites = [] if name == 'canary' else ['Verify same-source canary persisted output before this cohort.']
        if name == 'parity':
            prerequisites.append('Verify same-source parity-canary raw bytes before full parity.')
        for node in group['nodes']:
            exact_coverage[node].append(name)
            relative = node.split('::', 1)[0]
            if name not in file_coverage[relative]:
                file_coverage[relative].append(name)
            if relative not in test_identities:
                test_identities[relative] = file_identity(source / relative)
        groups.append({'name': name, **group, 'cwd': str(source), 'out': str(destination),
            'output_exists': os.path.lexists(destination), 'argv': argv, 'environment': environment,
            'shell_command': shlex.join(command), 'prerequisites': prerequisites})
    value = {'kind': 'native_u3g_offline_cohort_plan', 'version': 1,
        'status': 'plan_only_not_executed', 'source_root': str(source),
        'runner': runner_identity, 'planner': file_identity(Path(__file__).resolve()),
        'execution': 'Sequential only; one active test invocation; quiet-window lock checked by runner.',
        'workers': 2, 'test_deadline_seconds': 3200, 'independent_cutoff_seconds': 3250,
        'excluded_public_completion_nodes': list(EXCLUDED),
        'pytest_exclusion_flags': ['--deselect=' + node for node in EXCLUDED],
        'exclusion_enforcement': 'No selected file/node can contain either excluded test. Flags are '
            'explicit metadata only: inherited runner rejects non-tests/ arguments. Do not append '
            'them to its argv without a narrow runner interface change.',
        'historical_nonpasses': 'All 118 retained nonpasses require fresh trace classification; '
            'none is waived, converted to an expected failure, or omitted by this plan.',
        'packet_requirements': 'Run packet-dependent core, D114 and failed protected-selector '
            'checks again against the explicit private four-packet composition. Run raw parity '
            'and its canary on both source trees. Worktree failures remain recorded.',
        'canary_artifacts': ['cases/popen-*/test_validate_probe_uses_saved*/verified-output.json',
            'cases/popen-*/test_validate_probe_uses_saved*/expectation.json',
            'cases/popen-*/test_validate_probe_uses_saved*/probe.json',
            'cases/popen-*/test_validate_probe_uses_saved*/account-choice.json',
            'pytest.xml', 'outcome.json', 'source-stability.json'],
        'cohorts': groups, 'selected_test_file_identities': test_identities,
        'duplicate_exact_selectors': {node: cohorts for node, cohorts in exact_coverage.items()
                                      if len(cohorts) > 1},
        'overlapping_test_files': {name: cohorts for name, cohorts in file_coverage.items()
                                   if len(cohorts) > 1},
        'overlap_policy': 'Duplicate coverage is intentional and explicit. File-wide and specific '
            'node selections overlap; never sum cohort pass counts as unique tested nodes.'}
    raw = (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()
    if args.output:
        output = args.output
        if (not output.is_absolute() or output.resolve() != output
                or not output.is_relative_to(evidence) or output.suffix != '.json'):
            parser.error('--output must be a fresh physical JSON path under assigned u3g scratch')
        if not output.parent.is_dir():
            parser.error('--output parent must already exist')
        with output.open('xb') as stream:
            stream.write(raw)
    print(raw.decode(), end='')


if __name__ == '__main__':
    main()
