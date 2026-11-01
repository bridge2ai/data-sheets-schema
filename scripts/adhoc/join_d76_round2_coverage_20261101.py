#!/usr/bin/env python3
"""Join bounded PR #5213 D76 round-2 coverage; 2026-11-01.

Inputs: final full collection, frozen selections and seven completed cohort runs.
Output: fresh external JSON with exact module/probe coverage and artifact hashes.
No tests, source mutations, providers or GitHub. Historical107/CI use the existing
final summary; defect-asserting observations deliberately are not acceptance runs.
"""
import argparse
import ast
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent


def load(name):
    spec = importlib.util.spec_from_file_location(name, HERE / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PHASE = load('d76_phase_accounting_20261031')
SELECTION = load('plan_d76_round2_validation_20261101')
NOTES = load('d76_round2_hygiene_20261101')
GROUPS = {
    'new-regressions': SELECTION.NEW, 'old-d76': SELECTION.OLD_D76,
    'f5-tests': SELECTION.F5_TESTS, 'f5-notes-canary': SELECTION.CANARY,
    'f5-notes-audit': SELECTION.AUDIT,
    'reviewer-codex': SELECTION.CODEX, 'reviewer-claude': SELECTION.CLAUDE,
}
NOTES_JOBS = {'f5-notes-canary': 'offline-canary', 'f5-notes-audit': 'offline-audit'}
PROOFS = ('source_unchanged', 'hygiene_passed', 'origins_verified', 'helpers_unchanged',
          'targets_unchanged', 'sandbox_loaded', 'all_worker_collections_identical', 'zero_guard_denials')


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def strict_object(pairs):
    value = {}
    for key, item in pairs:
        require(key not in value, 'duplicate JSON key: ' + key)
        value[key] = item
    return value


class Evidence:
    def __init__(self):
        self.raw = {}

    def read(self, path):
        path = Path(path).resolve(strict=True)
        if path not in self.raw:
            require(path.is_file() and path.stat().st_size <= 256 * 1024 * 1024, 'invalid evidence file')
            self.raw[path] = path.read_bytes()
        return self.raw[path]

    def json(self, path):
        return json.loads(self.read(path), object_pairs_hook=strict_object)

    def stable(self):
        require(all(path.read_bytes() == raw for path, raw in self.raw.items()), 'evidence changed during join')

    def digests(self):
        return {str(path): sha(raw) for path, raw in sorted(self.raw.items())}


def check_scope(name, requested):
    require(name in GROUPS, 'unknown round2 cohort')
    require(requested and len(set(requested)) == len(requested), 'empty/duplicate target list')
    if name.startswith('reviewer-'):
        require(all(Path(path).is_absolute() for path in requested), 'reviewer paths must be absolute')
        require([Path(path).name for path in requested] == GROUPS[name], 'reviewer file roster differs')
    else:
        require(requested == GROUPS[name], 'requested module roster differs')


def check_notes_job(name, plan, hygiene):
    expected = NOTES_JOBS.get(name)
    require(plan.get('notes_ci_job') == expected, 'wrong notes CI job')
    require(hygiene.get('passed') is True, 'hygiene evidence refused')
    if expected:
        require(plan.get('notes_ci_pythonpath') == list(NOTES.CI_PATHS), 'wrong notes CI PYTHONPATH')
        require(plan.get('hygiene_mode') == hygiene.get('hygiene_mode') ==
                'notes_ci_new_tracked_source_bytecode', 'wrong notes hygiene policy')
        require(hygiene.get('before') == '' and not hygiene.get('removed_paths') and
                not hygiene.get('refusals'), 'notes hygiene contains unexplained changes')
        require(all(row.get('header_and_compiled_payload_verified') is True
                    for row in hygiene.get('allowed_new_bytecode', [])), 'unverified notes bytecode')
    else:
        require(plan.get('notes_ci_pythonpath') is None and
                hygiene.get('before') == hygiene.get('after'), 'ordinary source hygiene changed')


def read_run(ev, directory, head):
    directory = Path(directory).resolve(strict=True)
    plan, outcome, nodes, source, after, hygiene, command = [ev.json(directory / (name + '.json'))
        for name in ('plan', 'outcome', 'nodes', 'source-before', 'source-after', 'hygiene', 'pytest-command')]
    require(plan.get('head') == source.get('head') == head and source == after, 'wrong or changed source head')
    require(source.get('tracked_exact') is True and plan.get('detached') is True and
            plan.get('git_tree') == source.get('tree'), 'source tree is not exact/detached')
    require(all(outcome.get(key) is True for key in PROOFS), 'missing source/import/offline proof')
    require(outcome.get('guard_denial_count') == 0 and not list(directory.glob('guard-denials-*.jsonl')),
            'offline guard denial')
    require(not nodes.get('collection_errors') and not outcome.get('collection_errors'), 'collection errors')
    require(command.get('cwd') == plan['worktree'] and command.get('argv') == plan['pytest_argv'] and
            command['argv'][:len(plan['targets'])] == plan['targets'], 'command differs from targets/plan')
    require(outcome.get('collected_occurrences') == len(nodes['collected']) and
            outcome.get('selected_occurrences') == len(nodes['selected']), 'node-count claim differs')
    return {'directory': str(directory), 'plan': plan, 'outcome': outcome,
            'nodes': nodes, 'source': source, 'hygiene': hygiene}


def helper_roles(ev, run):
    result = {}
    for path, digest in run['plan']['helpers'].items():
        role = 'scripts/adhoc/' + Path(path).name
        require(role not in result, 'ambiguous helper role')
        require(sha(ev.read(path)) == digest == run['source']['entries'].get(role, {}).get('sha256'),
                'helper differs from tracked source')
        result[role] = digest
    return result


def verify_targets(ev, name, requested, run, reference, frozen):
    check_scope(name, requested)
    require(requested == run['plan']['targets'], 'selection differs from requested invocation')
    root, main_root = Path(run['plan']['worktree']), Path(reference['plan']['worktree'])
    expected_keys = set()
    probe_functions = {}
    for value in requested:
        path = Path(value) if Path(value).is_absolute() else root / value
        frozen_path = Path(value) if Path(value).is_absolute() else main_root / value
        expected_keys.add(str(path))
        digest = frozen['target_sha256'].get(str(frozen_path))
        raw = ev.read(path)
        require(digest is not None and run['plan']['target_sha256'].get(str(path)) == sha(raw) == digest,
                'target/reviewer hash differs from frozen selection')
        if not Path(value).is_absolute():
            require(run['source']['entries'].get(value, {}).get('sha256') == digest, 'target differs from source')
        else:
            functions = {node.name for node in ast.parse(raw).body
                         if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith('test_')}
            require(functions, 'reviewer file has no declared test functions')
            probe_functions[value] = functions
    require(set(run['plan']['target_sha256']) == expected_keys, 'unexpected/missing target hash')
    return probe_functions


def check_selection(name, requested, nodes, reference_nodes, probe_functions=None, reviewer_root=None):
    collected, selected = Counter(nodes['collected']), Counter(nodes['selected'])
    require(collected and collected == selected, 'cohort was empty or deselected')
    rows = []
    if name.startswith('reviewer-'):
        # Preserve the entire node ID for accounting, including blank prefixes.
        # Frozen known probes declare top-level functions; require every one.
        functions = Counter(node.rsplit('::', 1)[-1].split('[', 1)[0] for node in collected)
        owners = {}
        for path, names in (probe_functions or {}).items():
            for function in names:
                require(function not in owners, 'ambiguous reviewer function across files')
                owners[function] = path
        declared = set(owners)
        require(set(functions) == declared, 'missing/unexpected reviewer test function')
        for node in collected:
            prefix, _, suffix = node.rpartition('::')
            if prefix:
                path = Path(prefix)
                require(path.is_absolute() or reviewer_root is not None, 'reviewer node origin cannot be resolved')
                actual = path if path.is_absolute() else Path(reviewer_root) / path
                require(actual.resolve() == Path(owners[suffix.split('[', 1)[0]]).resolve(),
                        'reviewer node names a different source file')
        for path, names in probe_functions.items():
            rows.append({'module': path, 'declared_functions': sorted(names), 'present': names <= set(functions)})
        basis = ('exact own collected/selected literal multiset; frozen file hashes; '
                 'available file prefixes checked, blank prefixes mapped by unique declared function names')
    else:
        require(all(node.split('::', 1)[0] in requested for node in collected), 'unexpected module in cohort')
        for module in requested:
            actual = Counter({node: count for node, count in collected.items() if node.split('::', 1)[0] == module})
            require(actual, 'requested module has no collected nodes: ' + module)
            expected = Counter(node for node in reference_nodes if node.split('::', 1)[0] == module)
            if module.startswith('tests/'):
                require(expected and expected == actual, 'module differs from full collection: ' + module)
            rows.append({'module': module, 'occurrences': sum(actual.values()),
                         'full_collection_occurrences': sum(expected.values()) if module.startswith('tests/') else None})
        basis = ('exact module multisets from full tests collection' if name not in NOTES_JOBS else
                 'each notes module present; exact own collection/selection only')
    accounting = PHASE.phase_accounting(nodes['selected'], nodes['reports'])
    completed = Counter(row['nodeid'] for row in accounting['occurrences'] if row['complete'])
    require(accounting['all_selected_completed'] and selected == completed, 'incomplete selected phases')
    return {'reference_basis': basis, 'modules': rows, 'selected_occurrences': sum(selected.values()),
            'coverage_complete': True, 'counts': accounting['counts'],
            'all_occurrences_passed': accounting['counts']['passed'] == sum(selected.values()),
            'nonpassing_occurrences': [row for row in accounting['occurrences'] if row['status'] != 'passed']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expected-head', required=True)
    parser.add_argument('--full-collection', type=Path, required=True)
    parser.add_argument('--selection-dir', type=Path, required=True)
    parser.add_argument('--run', action='append', required=True, metavar='NAME=DIRECTORY')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    require(re.fullmatch(r'[0-9a-f]{40}', args.expected_head), 'full lowercase final head required')
    paths = {}
    for item in args.run:
        name, sep, directory = item.partition('=')
        require(sep and name in GROUPS and name not in paths and directory, 'invalid/duplicate cohort')
        paths[name] = Path(directory)
    require(set(paths) == set(GROUPS), 'all seven bounded cohorts required')
    ev = Evidence()
    reference = read_run(ev, args.full_collection, args.expected_head)
    rp, rn = reference['plan'], reference['nodes']
    require(rp.get('collect_only') is True and rp['targets'] == ['tests'] and
            reference['outcome'].get('collection_passed') is True and reference['outcome'].get('returncode') == 0,
            'successful full tests collection required')
    require(not rn['reports'] and Counter(rn['collected']) == Counter(rn['selected']), 'filtered/noncollection reference')
    check_notes_job('full-collection', rp, reference['hygiene'])
    roles = helper_roles(ev, reference)
    for name in (Path(__file__).name, 'plan_d76_round2_validation_20261101.py',
                 'd76_phase_accounting_20261031.py', 'd76_round2_hygiene_20261101.py'):
        require(sha(ev.read(HERE / name)) == reference['source']['entries'].get('scripts/adhoc/' + name, {}).get('sha256'),
                'join helper differs from final tracked source')
    frozen = ev.json(args.selection_dir / 'plan.json')
    require(frozen['head'] == args.expected_head, 'selection head differs')
    rows, notes_roots = [], []
    for name, directory in paths.items():
        run = read_run(ev, directory, args.expected_head)
        require(run['source'] == reference['source'], 'cohort differs from final collected source')
        require(run['plan'].get('collect_only') is False, 'cohort is collection only')
        require(helper_roles(ev, run) == roles, 'cohort helper roles differ')
        for field in ('runtime', 'workflow_sha256', 'selector_sha256'):
            require(run['plan'].get(field) == rp.get(field), 'cohort differs: ' + field)
        check_notes_job(name, run['plan'], run['hygiene'])
        if name in NOTES_JOBS:
            require(run['plan']['worktree'] != rp['worktree'], 'notes needs its fresh separate tree')
            notes_roots.append(run['plan']['worktree'])
        else:
            require(run['plan']['worktree'] == rp['worktree'], 'core/probe tree differs from collection')
        requested = ev.json(args.selection_dir / (name + '.json'))
        functions = verify_targets(ev, name, requested, run, reference, frozen)
        selection = check_selection(name, requested, run['nodes'], rn['collected'], functions,
                                    reviewer_root=run['plan']['worktree'])
        require(selection['counts'] == run['outcome']['counts'] and
                run['outcome'].get('node_accounting_complete') is True, 'phase-count claims differ')
        rows.append({'name': name, 'directory': str(directory), **selection,
                     'run_passed': run['outcome'].get('passed') is True,
                     'hygiene': run['hygiene'], 'notes_ci_job': run['plan'].get('notes_ci_job')})
    require(len(notes_roots) == len(set(notes_roots)) == 2, 'notes jobs must use distinct fresh trees')
    output = args.output.resolve()
    source_roots = [Path(rp['worktree']), Path(__file__).resolve().parents[2], *map(Path, notes_roots)]
    require(not output.exists() and output.parent.is_dir() and not any(output.is_relative_to(root) for root in source_roots),
            'fresh output outside source trees required')
    ev.stable()
    result = {'format': 'd76_round2_coverage_v1', 'expected_head': args.expected_head,
        'cohorts': rows, 'coverage_complete': True,
        'all_executed_occurrences_passed': all(row['all_occurrences_passed'] and row['run_passed'] for row in rows),
        'artifact_sha256': ev.digests(), 'tests_launched': 0,
        'limits': ['Historical107 and exact CI-shard acceptance remain in the separate final summary.',
                   'Defect-asserting observations and baseline runs are excluded; skips are coverage, not passes.',
                   'Claude residual F2 printed observations do not replace committed match assertions.',
                   'Notes/probes use their own collections, not membership in the full tests collection.',
                   'Blank reviewer prefixes have no independent file-origin proof; unique frozen function names supply the mapping.',
                   'Occurrence counts can overlap across cohorts; they are not unique-test totals.']}
    with output.open('x') as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps({'output': str(output), 'sha256': sha(output.read_bytes()),
                     'coverage_complete': True, 'all_executed_occurrences_passed': result['all_executed_occurrences_passed']}))


if __name__ == '__main__':
    main()
