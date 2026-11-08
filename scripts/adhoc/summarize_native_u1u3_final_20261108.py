#!/usr/bin/env python3
"""U3-E final evidence reconciliation, 2026-11-08.
Inputs: retained immediate-run outcomes/JUnit/collection and committed source.
Outputs: exact node ledger, per-run table, uncovered planned nodes and hashes
under scratch-native-u1u3. No source mutations, test launches or network.
"""
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT.parent / 'scratch-native-u1u3'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def nodeid(case):
    parts = case.get('classname', '').split('.')
    for end in range(len(parts), 0, -1):
        path = '/'.join(parts[:end]) + '.py'
        if (ROOT / path).is_file():
            return '::'.join([path, *parts[end:], case.get('name', '')])
    return case.get('classname', '') + '::' + case.get('name', '')

def main():
    rows, nodes, hashes = [], [], {}
    for outcome in sorted(OUT.glob('*/outcome.json')):
        folder = outcome.parent
        raw = json.loads(outcome.read_text())
        plan = json.loads((folder / 'plan.json').read_text())
        row = {'run': folder.name, 'source_root': plan['source_root'], 'source_commit': plan['source_commit'],
               'seconds': raw.get('seconds'), 'returncode': raw.get('returncode'),
               'cleanup_verified': raw.get('cleanup_verified'), 'interrupted': raw.get('interrupted'),
               'deadline_seconds': plan.get('deadline_seconds'), 'counts': None}
        host = folder / 'host-load.json'
        if host.exists():
            row['host'] = json.loads(host.read_text())
        stability = folder / 'source-stability.json'
        row['source_stable'] = json.loads(stability.read_text()).get('unchanged') if stability.exists() else None
        xml = folder / 'pytest.xml'
        if xml.exists():
            counts = dict(passed=0, failure=0, error=0, skipped=0)
            for case in ET.parse(xml).findall('.//testcase'):
                tag = next((t for t in ('failure', 'error', 'skipped') if case.find(t) is not None), 'passed')
                counts[tag] += 1
                item = {'run': folder.name, 'source_root': plan['source_root'], 'node': nodeid(case), 'status': tag}
                if tag != 'passed':
                    item.update(message=case.find(tag).get('message', ''), text=case.find(tag).text)
                nodes.append(item)
            row['counts'] = counts
        rows.append(row)
        for file in folder.iterdir():
            if file.is_file() and not file.is_symlink():
                hashes[str(file.relative_to(OUT))] = {'sha256': sha(file), 'bytes': file.stat().st_size}
    collected = set()
    for line in (OUT / 'full-collection/pytest.log').read_text().splitlines():
        if line.startswith('tests/') and '::' in line:
            collected.add(line)
    expected_files = set()
    plan = json.loads((OUT / 'suite-plan.json').read_text())
    for name, values in plan.items():
        if name != 'collection':
            expected_files.update(v.split('::')[0] for v in values)
    continuation = OUT / 'continuation-plan.json'
    if continuation.exists():
        for _, values in json.loads(continuation.read_text()):
            expected_files.update(v.split('::')[0] for v in values)
    expected = {node for node in collected if any(node.startswith(path + '::') or node.startswith(path + '/') for path in expected_files)}
    observed = defaultdict(set)
    for item in nodes:
        if item['source_root'] == str(ROOT):
            observed[item['node']].add(item['status'])
    reconciliation = {'collected_unique_nodes': len(collected), 'planned_files_or_directories': sorted(expected_files),
        'planned_collected_nodes': len(expected), 'candidate_observed_unique_nodes': len(observed),
        'uncovered_planned_nodes': sorted(expected - observed.keys()),
        'mixed_candidate_outcomes': {key: sorted(value) for key, value in observed.items() if len(value) > 1},
        'scope': 'Completed XML only; interrupted runs without XML and collection alone provide no execution credit. Packet and baseline nodes excluded from candidate coverage.'}
    table = ['| Run | Pass | Fail | Error | Skip | Supervised seconds | Exit | Cleanup |',
             '|---|---:|---:|---:|---:|---:|---:|---|']
    for row in rows:
        counts = row['counts'] or {}
        fields = [str(counts.get(key, 'incomplete')) for key in ('passed', 'failure', 'error', 'skipped')]
        table.append('| ' + ' | '.join([row['run'], *fields, f"{row['seconds']:.2f}", str(row['returncode']), str(row['cleanup_verified'])]) + ' |')
    for name, value in [('validation-summary.json', rows), ('exact-node-ledger.json', nodes),
                        ('coverage-reconciliation.json', reconciliation), ('evidence-hashes.json', hashes)]:
        with (OUT / name).open('x') as f:
            json.dump(value, f, indent=2, sort_keys=True)
            f.write('\n')
    (OUT / 'validation-table.md').write_text('\n'.join(table) + '\n')
    print(json.dumps({'runs': len(rows), 'node_records': len(nodes), 'uncovered': len(reconciliation['uncovered_planned_nodes'])}))

if __name__ == '__main__':
    main()
