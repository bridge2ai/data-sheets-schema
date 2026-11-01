#!/usr/bin/env python3
# Purpose: distinguish completed pytest outcomes from interrupted JUnit placeholders.
# Inputs: selected node IDs and phase reports; output: occurrence-level counts/ledger.
# Serves #5213/D76 harness finding H4; 2026-10-31. Pure function, no I/O.
from collections import Counter


def phase_accounting(selected, reports):
    selected_counts = Counter(selected)
    groups = {}
    old_ordinal = Counter()
    old_current = {}
    ambiguous = set()
    for report in reports:
        node = report['nodeid']
        index = report.get('item_index')
        if index is None:
            # Old evidence has no execution index. Unique IDs are unambiguous;
            # duplicate IDs without indices must never borrow each other's phases.
            if selected_counts[node] > 1:
                ambiguous.add(node)
            if report['when'] == 'setup' or node not in old_current:
                index = ('legacy', old_ordinal[node])
                old_ordinal[node] += 1
                old_current[node] = index
            else:
                index = old_current[node]
        else:
            index = ('indexed', index)
        groups.setdefault((node, index), []).append(report)
    counts = Counter({kind: 0 for kind in ('passed', 'failed', 'errors', 'skipped',
                                          'xpassed', 'interrupted', 'not_started', 'unexpected')})
    seen = Counter()
    rows = []
    for (node, index), phases in groups.items():
        seen[node] += 1
        by_phase = {}
        for phase in phases:
            by_phase.setdefault(phase['when'], []).append(phase)
        complete = False
        if seen[node] > selected_counts[node]:
            status = 'unexpected'
        elif node in ambiguous:
            status = 'interrupted'
        else:
            setup = by_phase.get('setup', [])
            required = {'setup', 'teardown'} if len(setup) == 1 and setup[0]['outcome'] in ('failed', 'skipped') else {'setup', 'call', 'teardown'}
            complete = set(by_phase) == required and all(len(values) == 1 for values in by_phase.values())
            if not complete:
                status = 'interrupted'
            elif any(row['outcome'] == 'failed' and row['when'] != 'call' for row in phases):
                status = 'errors'
            elif any(row['outcome'] == 'failed' for row in phases):
                status = 'failed'
            elif any(row['outcome'] == 'skipped' for row in phases):
                status = 'skipped'
            elif any(row.get('xfail') is not None for row in phases):
                status = 'xpassed'
            elif all(row['outcome'] == 'passed' for row in phases):
                status = 'passed'
            else:
                status = 'interrupted'
                complete = False
        counts[status] += 1
        rows.append({'nodeid': node, 'item_index': index, 'status': status,
                     'complete': complete, 'reports': phases})
    counts['not_started'] = sum((selected_counts - seen).values())
    return {'counts': dict(counts), 'occurrences': rows,
            'ambiguous_legacy_duplicate_nodes': sorted(ambiguous),
            'all_selected_completed': bool(selected) and not any(counts[key] for key in ('interrupted', 'not_started', 'unexpected')),
            'selected_occurrences': len(selected), 'started_occurrences': len(groups)}
