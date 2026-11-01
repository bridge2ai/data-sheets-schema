#!/usr/bin/env python3
# Purpose: summarize retained D76 runs with exact node outcomes and artifact hashes.
# Inputs: completed runs, explicit accepted head, optional historical107/CI targets;
# output: fresh JSON summary. Serves PR #5213/D76; 2026-10-31. No tests or mutations.
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def complete_passing(reports):
    """A success is exactly three passing phases, never a partial/duplicate observation."""
    return len(reports) == 3 and Counter((r['when'], r['outcome'], r.get('xfail')) for r in reports) == Counter({
        ('setup', 'passed', None): 1, ('call', 'passed', None): 1, ('teardown', 'passed', None): 1})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', type=Path, action='append', required=True)
    parser.add_argument('--accepted-head', help='Full final commit SHA eligible for acceptance; baseline heads never count.')
    parser.add_argument('--historical-targets', type=Path)
    parser.add_argument('--ci-expected', type=Path, help='Exact expected-node list from the full collection CI planner.')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if (args.historical_targets or args.ci_expected) and not args.accepted_head:
        parser.error('historical/CI acceptance requires --accepted-head')
    if args.accepted_head and (len(args.accepted_head) != 40 or any(c not in '0123456789abcdef' for c in args.accepted_head)):
        parser.error('--accepted-head must be a full lowercase Git SHA')
    rows = []
    observations = defaultdict(list)
    ci_rows = []
    for directory in args.run:
        plan = json.loads((directory / 'plan.json').read_text())
        outcome = json.loads((directory / 'outcome.json').read_text())
        nodes = json.loads((directory / 'nodes.json').read_text())
        by_node = defaultdict(list)
        for report in nodes['reports']:
            by_node[report['nodeid']].append(report)
        failing = []
        for node, reports in by_node.items():
            observations[node].append({'run': str(directory), 'head': plan['head'],
                'reports': reports, 'complete_pass': complete_passing(reports)})
            if not complete_passing(reports):
                failing.append({'nodeid': node, 'reports': reports})
        messages = []
        xml = directory / 'pytest.xml'
        if xml.is_file():
            for case in ET.parse(xml).getroot().iter('testcase'):
                for tag in ('failure', 'error', 'skipped'):
                    for finding in case.findall(tag):
                        messages.append({'classname': case.get('classname'), 'name': case.get('name'),
                            'kind': tag, 'message': finding.get('message'), 'text': finding.text})
        artifacts = {str(path.relative_to(directory)): digest(path) for path in sorted(directory.glob('*.json')) if path.is_file()}
        for name in ('pytest.xml', 'pytest.log'):
            path = directory / name
            if path.is_file():
                artifacts[name] = digest(path)
        denials = {str(path.relative_to(directory)): {'sha256': digest(path), 'lines': path.read_text().splitlines()}
                   for path in directory.glob('guard-denials-*.jsonl')}
        row = {'run': str(directory), 'head': plan['head'], 'outcome': outcome,
               'nonpassing_nodes': failing, 'xml_findings': messages, 'artifacts': artifacts,
               'guard_denials': denials}
        rows.append(row)
        if plan.get('ci_ordinary_shard_of_4') is not None and plan['head'] == args.accepted_head:
            ci_rows.append((row, nodes))
    accepted_rows = [row for row in rows if row['head'] == args.accepted_head] if args.accepted_head else []
    accepted_runs_pass = bool(accepted_rows) and all(
        (row['outcome'].get('passed') or row['outcome'].get('collection_passed')) and not row['guard_denials']
        for row in accepted_rows)
    result = {'runs': rows, 'accepted_head': args.accepted_head,
        'accepted_runs_pass': accepted_runs_pass if args.accepted_head else None,
        'reported_counts_sum_includes_repeats': dict(sum((Counter(row['outcome']['counts']) for row in rows), Counter()))}
    gates = []
    if args.accepted_head:
        gates.append(accepted_runs_pass)
    if args.historical_targets:
        targets = json.loads(args.historical_targets.read_text())
        if len(targets) != 107 or len(set(targets)) != 107:
            raise ValueError('historical cohort requires exactly107 unique nodes')
        historical = []
        for node in targets:
            eligible = [item for item in observations[node] if item['head'] == args.accepted_head]
            passed = bool(eligible) and all(item['complete_pass'] for item in eligible)
            historical.append({'nodeid': node, 'eligible_observations': eligible,
                'other_head_observations': [item for item in observations[node] if item['head'] != args.accepted_head],
                'passed': passed})
        result['historical'] = {'targets_sha256': digest(args.historical_targets), 'rows': historical,
            'total': len(targets), 'missing': [r['nodeid'] for r in historical if not r['eligible_observations']],
            'nonpassing': [r['nodeid'] for r in historical if not r['passed']],
            'passed': all(r['passed'] for r in historical)}
        gates.append(result['historical']['passed'])
    if args.ci_expected:
        expected = Counter(json.loads(args.ci_expected.read_text()))
        module = 'tests/test_source_heading_runtime_api.py'
        if len(ci_rows) != 1:
            result['ci_partition'] = {'passed': False, 'reason': 'exactly one eligible ordinary-shard run required', 'runs': len(ci_rows)}
        else:
            row, nodes = ci_rows[0]
            actual = Counter(nodes['selected'])
            held = [node for node in actual if node.split('::', 1)[0] == module]
            result['ci_partition'] = {'run': row['run'], 'expected_sha256': digest(args.ci_expected),
                'expected_occurrences': sum(expected.values()), 'actual_occurrences': sum(actual.values()),
                'missing': dict(expected - actual), 'extra': dict(actual - expected), 'held_module': module,
                'held_module_nodes': held, 'passed': bool(expected) and expected == actual and bool(held)
                    and row['outcome']['node_accounting_complete']}
        gates.append(result['ci_partition']['passed'])
    result['acceptance_passed'] = all(gates) if gates else None
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps({'output': str(args.output), 'sha256': digest(args.output), 'runs': len(rows),
        'counts_including_repeats': result['reported_counts_sum_includes_repeats'],
        'acceptance_passed': result['acceptance_passed']}, sort_keys=True))
    return 1 if result['acceptance_passed'] is False else 0


if __name__ == '__main__':
    raise SystemExit(main())
