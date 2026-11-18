"""Compact F3 scheduling scenarios from current CI evidence, 2026-11-18.

Inputs: exact collection, effective weights, measured/prior node durations,
explicit censoring floors, actual current packet setup timings.
Outputs: compact JSON and script-generated tables. No code/test mutations.
The four-case lane scenario is review-only and never edits production lanes.
"""
import argparse
from collections import Counter
from copy import deepcopy
import xml.etree.ElementTree as ET
import codex196_fix6289b_model_20261118 as m


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--collection', type=m.Path,
        default=m.OLD / 'simulation-final-inputs-001/final-nodeids.json')
    parser.add_argument('--outstem', default='capacity-simulation-initial')
    args = parser.parse_args()
    sim = m.module(m.R / 'scripts/adhoc/codex196_fix6289_simulate_20261118.py', 'ci_capacity_sim')
    sharder, sharder_path = sim.load_sharder(m.W)
    nodes = sim.collection(args.collection)
    ordinary = sharder.partition_lanes(nodes)['ordinary']
    original_weights = m.load(m.S / 'candidate-effective-weights.json')['file_seconds']
    observed = m.load(m.S / 'combined-node-seconds.json')
    floors = m.load(m.S / 'censored-node-floors.json')
    fixture = m.load(m.S / 'current-fixture-model.json')
    pending = m.load(m.S / 'pending-inventory.json')['shards']
    direct_long = [item['node'] for row in pending.values() for item in row['unfinished']
                   if item['elapsed_until_cancellation_seconds'] > 3000]
    if len(direct_long) != 4:
        raise ValueError('expected exactly four individually over-target censored cases')
    known_denials = [node for node in ordinary if node.startswith('tests/test_native_shared_denials')
                     and '::test_denial_live_and_saved[' in node]
    scenarios = []
    for label, removed in [('current_whole_file', []),
                           ('proposal_four_censored_case_lanes', direct_long),
                           ('sensitivity_all_denials_and_admission_lanes', sorted(set(direct_long + known_denials)))]:
        selected = [node for node in ordinary if node not in removed]
        counts = Counter(node.split('::', 1)[0] for node in selected)
        weights = dict(original_weights)
        # Once a case leaves the ordinary lane, its duration must not continue
        # to distort the residual file's ordinary scheduling weight.
        for node in removed:
            path = node.split('::', 1)[0]
            if path in counts:
                weights[path] = max(0.001, weights[path] - max(observed.get(node, 0), floors.get(node, 0)))
        estimates = sharder._estimates(counts, weights)
        seconds = {}
        for path, count in counts.items():
            members = [node for node in selected if node.split('::', 1)[0] == path]
            fixed = [node for node in members if node in observed or node in floors]
            unknown = [node for node in members if node not in observed and node not in floors]
            total = sum(max(observed.get(node, 0), floors.get(node, 0)) for node in fixed)
            share = max(0, estimates[path] - total) / len(unknown) if unknown else 0
            seconds.update({node: max(observed.get(node, 0), floors.get(node, 0)) for node in fixed})
            seconds.update({node: share for node in unknown})
        profiles = []
        for shard_count, limit in ((12, 3600), (8, 4800)):
            assignments = sharder.balanced_files(counts, shard_count, weights)
            rows = []
            for index in range(1, shard_count + 1):
                chosen = [node for node in selected if assignments[node.split('::', 1)[0]] == index]
                local_counts = Counter(node.split('::', 1)[0] for node in chosen)
                local_estimates = sharder._estimates(local_counts, weights)
                costs = {path: local_estimates[path] / count for path, count in local_counts.items()}
                chosen.sort(key=lambda node: -costs[node.split('::', 1)[0]])
                items = [sim.SimpleNamespace(nodeid=node) for node in chosen]
                config = sim.SimpleNamespace(workerinput={'workercount': 4},
                    getoption=lambda name, default=None: 1 if name == 'maxschedchunk' else default)
                ordered = [item.nodeid for item in sharder._pair_initial_load_items(config, items, costs, local_counts)]
                if Counter(ordered) != Counter(chosen):
                    raise ValueError('ordering changed exact occurrence coverage')
                result = sim.simulate_xdist(ordered, seconds, 4, fixture)
                predicted = result['makespan_seconds'] + 180
                rows.append({'shard': index, 'items': len(chosen),
                    'file_weight_seconds': round(sum(estimates[path] for path in local_counts), 3),
                    'predicted_job_seconds': round(predicted, 3),
                    'margin_seconds': round(limit - predicted, 3),
                    'meets_600_second_margin': predicted <= limit - 600,
                    'fixture_net_seconds': result['fixture_net_seconds'],
                    'workers': result['workers']})
            profiles.append({'shards': shard_count, 'limit_seconds': limit,
                'required_margin_seconds': 600, 'rows': rows,
                'worst_predicted_job_seconds': max(row['predicted_job_seconds'] for row in rows),
                'all_shards_meet_margin': all(row['meets_600_second_margin'] for row in rows)})
        scenarios.append({'label': label, 'removed_to_proposed_lanes': removed,
            'ordinary_occurrences': len(selected), 'profiles': profiles})
    jobs = m.load(m.S / 'jobs.json')['jobs']
    overhead = []
    for path in sorted((m.S / 'artifacts').glob('tests-py3.12-shard*/pytest.xml')):
        shard = int(path.parent.name.split('shard')[1])
        job = next(row for row in jobs if row['name'].endswith('/ shard ' + str(shard)))
        suite = next(ET.parse(path).iter('testsuite'))
        from datetime import datetime
        wall = (datetime.fromisoformat(job['completed_at'].replace('Z', '+00:00')) -
                datetime.fromisoformat(job['started_at'].replace('Z', '+00:00'))).total_seconds()
        overhead.append({'shard': shard, 'job_seconds': wall,
                         'pytest_suite_seconds': float(suite.get('time')),
                         'non_pytest_difference_seconds': round(wall - float(suite.get('time')), 3)})
    result = {'source_head': '7b9497fc17672e9ede94cebdd556085c8119f3cc',
        'inputs': {'collection': m.pin(args.collection), 'candidate_sharder': m.pin(sharder_path),
            'weights': m.pin(m.S / 'candidate-effective-weights.json'),
            'node_seconds': m.pin(m.S / 'combined-node-seconds.json'),
            'censoring_floors': m.pin(m.S / 'censored-node-floors.json'),
            'fixture_model': m.pin(m.S / 'current-fixture-model.json'), 'producer': m.pin(m.Path(__file__))},
        'collection': {'all': len(nodes), 'ordinary': len(ordinary), 'dedicated': len(nodes) - len(ordinary)},
        'model': {'workers': 4, 'scheduler': 'real installed xdist LoadScheduling, maxschedchunk=1',
            'ordering': 'actual candidate _pair_initial_load_items', 'job_overhead_seconds': 180,
            'current_ci_overhead_observations': overhead,
            'censoring': 'Current logged start-to-cancellation intervals are explicit minima for replay of this run, not successful completion measurements or future upper bounds. Delayed/batched log timestamps and hook/teardown time remain unresolved.',
            'failed_read': 'Read JUnit duration measures a failed path; successful corrected completion is unmeasured.',
            'unknown_nodes': 'Share the remaining positive file estimate; no upper bound is claimed.',
            'fixture': 'Current packet cold-setup maximum added per worker entry after removing available printed current setup.',
            'coverage': 'Exact occurrence counts are preserved in each ordinary plus proposed-lane partition.',
            'validity': 'Conditional forecast only; moving cases to new lanes is not implemented, and proposed dedicated-job durations are not certified.'},
        'single_case_obstruction': direct_long,
        'scenarios': scenarios}
    path = m.S / (args.outstem + '.json')
    m.save(path.name, result)
    lines = ['F3 conditional scheduling forecasts; no CI success is claimed.', '',
             'Four workers and 180 seconds of non-test allowance. Current censored minima and failed Read runtime remain non-completion evidence.', '',
             'Source JSON SHA-256: ' + m.pin(path)['sha256'], '']
    for scenario in scenarios:
        lines += [scenario['label'], '', '| Profile | Shard | Predicted seconds | Margin seconds | Meets 600-second margin |',
                  '|---|---:|---:|---:|---|']
        for profile in scenario['profiles']:
            for row in profile['rows']:
                lines.append('| ' + ' | '.join(map(str, (str(profile['shards']) + ' shards', row['shard'],
                    row['predicted_job_seconds'], row['margin_seconds'], row['meets_600_second_margin']))) + ' |')
        lines += ['']
    md = m.S / (args.outstem + '.md')
    md.write_text('\n'.join(lines))
    print(m.encode({'report': m.pin(path), 'table': m.pin(md),
        'scenarios': [{'label': row['label'], 'profiles': [{key: p[key] for key in
            ('shards', 'worst_predicted_job_seconds', 'all_shards_meet_margin')} for p in row['profiles']]}
            for row in scenarios]}).decode())


if __name__ == '__main__':
    main()
