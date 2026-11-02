#!/usr/bin/env python3
"""#5212 round 8, 2026-11-02: collect both real CI layouts without running tests.

Inputs: pinned --tree, --baseline collection and scratch --prefix. Outputs:
full/ten shard collection logs and ledgers, plus a multiset/ownership proof.
Uses the existing offline runner and the pinned plugin's own partition.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--tree', type=Path, required=True)
    p.add_argument('--baseline', type=Path, required=True)
    p.add_argument('--prefix', type=Path, required=True)
    a = p.parse_args()
    tree = a.tree.resolve()
    sys.path[:0] = [str(tree), str(Path(sys.executable).parent.parent / 'lib' /
        f'python{sys.version_info.major}.{sys.version_info.minor}' / 'site-packages')]
    from utils import pytest_shard as plugin
    assert Path(plugin.__file__).resolve() == tree/'utils/pytest_shard.py'
    baseline = json.loads(a.baseline.read_text())
    assert baseline['exit_code'] == 0 and not baseline['collection_errors']
    runner = tree/'scripts/adhoc/run_d68_round4_20261101.py'
    timing = tree/'utils/ci_test_durations.json'
    metadata = dict(head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=tree, text=True).strip(),
        baseline_sha256=sha(a.baseline), timing_sha256=sha(timing),
        plugin_sha256=sha(Path(plugin.__file__)), runner_sha256=sha(runner), checks=[])

    def collect(label, *flags):
        base = Path(str(a.prefix) + '-' + label)
        assert not base.with_suffix('.json').exists(), 'retain previous runs'
        command = [sys.executable, '-S', '-P', '-B', str(runner), '--tree', str(tree),
                   '--basetemp', str(base), 'tests', '--collect-only', '-q', *flags]
        with base.with_suffix('.log').open('w') as stream:
            status = subprocess.run(command, cwd=tree, stdout=stream, stderr=subprocess.STDOUT)
        data = json.loads(base.with_suffix('.json').read_text())
        assert status.returncode == data['exit_code'] == 0 and not data['collection_errors'], str(base)
        assert sha(timing) == metadata['timing_sha256']
        metadata['checks'].append(dict(label=label, command=command, cases=len(data['selected']),
            seconds=data['wall_seconds'], ledger=str(base.with_suffix('.json')),
            ledger_sha256=sha(base.with_suffix('.json')), log_sha256=sha(base.with_suffix('.log'))))
        print(f'{label}: {len(data["selected"])} collected, {data["wall_seconds"]:.3f}s', flush=True)
        return data['selected']

    whole = collect('full')
    assert Counter(whole) == Counter(baseline['selected'])
    lanes = plugin.partition_lanes(whole)
    ordinary = lanes['ordinary']
    weights = plugin.read_weights(timing)
    layouts = []
    for total in (6, 4):
        assignment = plugin.balanced_files((n.split('::', 1)[0] for n in ordinary), total, weights)
        union, seen = Counter(), set()
        sizes = []
        for index in range(1, total+1):
            selected = collect(f'{total}-shard-{index}', '-p', 'utils.pytest_shard',
                f'--ci-shard={index}/{total}', '--ci-lane=ordinary',
                '--ci-shard-timings=utils/ci_test_durations.json')
            expected = Counter(n for n in ordinary if assignment[n.split('::', 1)[0]] == index)
            assert Counter(selected) == expected
            assert not (seen & set(selected)), 'a node label has more than one owning shard'
            seen.update(selected)
            union.update(selected)
            sizes.append(len(selected))
        assert union == Counter(ordinary)
        for lane, nodes in lanes.items():
            if lane != 'ordinary':
                assert len(nodes) == 1 and not (seen & set(nodes))
                union.update(nodes)
        assert union == Counter(whole)
        layouts.append(dict(shards=total, shard_cases=sizes, ordinary_occurrences=len(ordinary),
            full_with_four_dedicated_cases=sum(union.values()), missing=0, extra=0,
            multiple_owners=0, matches_plugin=True))
    metadata.update(full_cases=len(whole), ordinary_cases=len(ordinary),
        full_multiset_unchanged=True, repeated_ordinary_labels=sum(c > 1 for c in Counter(ordinary).values()),
        layouts=layouts, full_shard_execution=False)
    output = Path(str(a.prefix) + '-proof.json')
    output.write_text(json.dumps(metadata, indent=2) + '\n')
    assert output.stat().st_size
    print(json.dumps(layouts, indent=2), flush=True)


if __name__ == '__main__':
    main()
