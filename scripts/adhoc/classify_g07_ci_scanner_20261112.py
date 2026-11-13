#!/usr/bin/env python3
"""G07 retained CI inventory accounting, 2026-11-12.

Input: the saved CI failure inventory JSON. Output: JSON on stdout only.
Groups every distinct test identity and preserves raw messages/job occurrences;
does not execute tests, scanners, imports from the project, or network calls.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('inventory', type=Path)
    parser.add_argument('--nodes', action='store_true')
    args = parser.parse_args()
    raw = args.inventory.read_bytes()
    inventory = json.loads(raw)
    grouped = defaultdict(dict)
    for row in inventory['failures']:
        message = row['message']
        if 'shared selector call guards/order changed' in message:
            cause = 'scanner_shared_selector_guard_order'
        elif 'v2 envelope authority source changed' in message:
            cause = 'scanner_native_authority_source_pin'
        elif 'closed dependency registry is not ready' in message:
            cause = 'closed_dependency_registry_not_ready'
        else:
            cause = row['class'] + ': ' + message
        identity = row['file'] + ('::' + row['node'] if row['node'] else '')
        item = grouped[cause].setdefault(identity, {'nodeid': identity, 'class': row['class'], 'occurrences': []})
        item['occurrences'].append({k: row[k] for k in ('job', 'kind', 'message')})
    unique = {(row['file'], row['node']): row for row in inventory['failures']}
    result = {
        'inventory': str(args.inventory), 'sha256': hashlib.sha256(raw).hexdigest(),
        'run_id': inventory['run_id'], 'head': inventory['head'],
        'row_count': len(inventory['failures']), 'unique_node_count': len(unique),
        'class_unique_counts': dict(Counter(row['class'] for row in unique.values())),
        'groups': [{
            'cause': cause, 'unique_nodes': len(nodes),
            'occurrences': sum(len(row['occurrences']) for row in nodes.values()),
            'file_counts': dict(Counter(n.split('::')[0] for n in nodes)),
            'messages': dict(Counter(o['message'] for n in nodes.values() for o in n['occurrences'])),
            **({'nodes': list(nodes.values())} if args.nodes else {})
        } for cause, nodes in sorted(grouped.items())]
    }
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
