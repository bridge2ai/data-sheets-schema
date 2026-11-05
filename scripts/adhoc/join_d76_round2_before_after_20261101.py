#!/usr/bin/env python3
"""Join exact new D76 round-2 test blobs across baseline/final, 2026-11-01.

Inputs: literal0460 baseline, final-head new-regression evidence, tests-only commit.
Output: fresh JSON with each failure-to-pass or control transition and input hashes.
No tests, mutations of input evidence, provider calls or remote Git operations.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import subprocess

BASE = '0460a69d8982b8acea8e0c370439cfe65495586e'
PROOFS = ('node_accounting_complete', 'source_unchanged', 'hygiene_passed',
          'origins_verified', 'helpers_unchanged', 'targets_unchanged',
          'sandbox_loaded', 'all_worker_collections_identical', 'zero_guard_denials')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def require(value, message):
    if not value:
        raise ValueError(message)


def read(directory, head):
    paths = {name: directory / (name + '.json') for name in
             ('plan', 'outcome', 'nodes', 'source-before', 'source-after', 'phase-accounting')}
    raw = {name: path.read_bytes() for name, path in paths.items()}
    values = {name: json.loads(blob) for name, blob in raw.items()}
    require(values['plan']['head'] == head, 'unexpected source head')
    require(values['source-before'] == values['source-after'], 'source changed')
    require(values['source-before']['head'] == head and values['source-before']['tracked_exact'], 'inexact source snapshot')
    require(values['plan']['detached'] is True and values['plan']['git_tree'] == values['source-before']['tree'],
            'detached source tree mismatch')
    outcome = values['outcome']
    require(all(outcome.get(key) is True for key in PROOFS), 'incomplete source/phase/import/offline proofs')
    require(outcome['guard_denial_count'] == 0 and not list(directory.glob('guard-denials-*.jsonl')), 'guard denial')
    require(not outcome['collection_errors'], 'collection failure')
    require(not values['plan']['collect_only'], 'collection alone is not a regression result')
    records = defaultdict(list)
    for row in values['phase-accounting']['occurrences']:
        require(row['complete'], 'incomplete test occurrence')
        suffix = row['nodeid'].split('::', 1)[1]
        records[suffix].append(row)
    require(Counter({key: len(rows) for key, rows in records.items()}) ==
            Counter(node.split('::', 1)[1] for node in values['nodes']['selected']), 'selected/phase mismatch')
    values['records'] = records
    values['artifacts'] = {str(paths[name]): sha(blob) for name, blob in raw.items()}
    return values


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--final', type=Path, required=True)
    parser.add_argument('--final-head', required=True)
    parser.add_argument('--tests-commit', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    require(all(re.fullmatch(r'[0-9a-f]{40}', value) for value in (args.final_head, args.tests_commit)),
            'full lowercase final/test commit hashes required')
    before = read(args.baseline, BASE)
    after = read(args.final, args.final_head)
    root = Path(after['plan']['worktree'])
    hashes = []
    for name in ('test_wave7_5213_d76_round2_binding.py', 'test_wave7_5213_d76_round2_recorder.py'):
        baseline_paths = [path for path in before['plan']['target_sha256'] if Path(path).name == name]
        final_paths = [path for path in after['plan']['target_sha256'] if Path(path).name == name]
        require(len(baseline_paths) == len(final_paths) == 1, 'exactly two expected target files required')
        baseline_path, final_path = baseline_paths[0], final_paths[0]
        expected = sha(subprocess.check_output(['git', '--no-replace-objects', '-C', str(root),
            'show', args.tests_commit + ':tests/' + name]))
        require(before['plan']['target_sha256'][baseline_path] ==
                after['plan']['target_sha256'][final_path] == expected, 'test blobs differ between baseline/final/commit')
        require(sha(Path(baseline_path).read_bytes()) == sha(Path(final_path).read_bytes()) == expected,
                'test file bytes changed after execution')
        hashes.append({'name': name, 'sha256': expected, 'tests_commit': args.tests_commit,
                       'baseline_path': baseline_path, 'final_path': final_path})
    require(len(before['plan']['target_sha256']) == len(after['plan']['target_sha256']) == 2, 'extra targets')
    require(set(before['records']) == set(after['records']), 'baseline/final test suffix set differs')
    rows = []
    for suffix, baseline_rows in sorted(before['records'].items()):
        final_rows = after['records'][suffix]
        require(len(baseline_rows) == len(final_rows) == 1, 'ambiguous repeated new-regression suffix')
        old, new = baseline_rows[0], final_rows[0]
        rows.append({'test_suffix': suffix, 'before': old, 'after': new,
                     'transition': old['status'] + '_to_' + new['status'],
                     'failure_to_pass': old['status'] == 'failed' and new['status'] == 'passed'})
    result = {'baseline_head': BASE, 'final_head': args.final_head, 'test_blobs': hashes,
              'exact_test_suffix_join': True, 'occurrences': len(rows), 'rows': rows,
              'transitions': dict(Counter(row['transition'] for row in rows)),
              'final_passed': after['outcome']['passed'] and all(row['after']['status'] == 'passed' for row in rows),
              'artifact_sha256': {**before['artifacts'], **after['artifacts']},
              'limits': 'Passing-before cases are controls, not reproduced defects. Failure traces still require classification.'}
    require(not args.output.exists() and args.output.parent.is_dir(), 'fresh output in existing directory required')
    for tree in (root, Path(before['plan']['worktree']), Path(__file__).resolve().parents[2]):
        require(not args.output.resolve().is_relative_to(tree.resolve()), 'output must be outside source worktrees')
    require(all(sha(Path(path).read_bytes()) == digest for path, digest in result['artifact_sha256'].items()),
            'evidence changed during join')
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps({'output': str(args.output), 'sha256': sha(args.output.read_bytes()),
                      'transitions': result['transitions'], 'final_passed': result['final_passed']}))
    return 0 if result['final_passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
