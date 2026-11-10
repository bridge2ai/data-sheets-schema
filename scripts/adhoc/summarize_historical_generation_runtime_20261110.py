#!/usr/bin/env python3
"""Purpose: historical generation timing for the lead ETA analysis, 2026-11-10.

Inputs: retained scratch-budget/budget_evidence.json (committed-corpus extraction)
and local provenance files, including untracked/ignored files under data.
Outputs: JSON to stdout, separated API usage sum from first-to-last-call span.
Serves: user-requested D4D generation ETA; no issue/PR assigned yet.
"""
import argparse
import datetime as dt
import json
from pathlib import Path
import statistics

import yaml


def timing(path, record, basis):
    usage = record.get('api_usage') or []
    timed = [u for u in usage if u.get('started_at') and isinstance(u.get('seconds'), (float, int))]
    if not timed:
        return None
    starts = [dt.datetime.fromisoformat(u['started_at']) for u in timed]
    ends = [t + dt.timedelta(seconds=u['seconds']) for t, u in zip(starts, timed)]
    return {
        'path': str(path), 'basis': basis, 'run': record.get('run'),
        'calls': len(timed), 'first_call': min(starts).isoformat(),
        'last_call_end': max(ends).isoformat(),
        'api_seconds_sum': sum(u['seconds'] for u in timed),
        'first_to_last_call_span_seconds': (max(ends) - min(starts)).total_seconds(),
        'transport_error_rows': sum('transport' in str(u.get('outcome', '')).lower() and 'error' in str(u.get('outcome', '')).lower() for u in timed),
        'completed_call_seconds_sum': sum(u['seconds'] for u in timed if u.get('stop_reason') == 'end_turn'),
        'caution': 'Usage-row seconds can overlap or include retries; sum is not total wall time. First-to-last span includes interruptions and intervention.',
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    args = parser.parse_args()
    evidence = json.loads(args.evidence.read_text())
    rows = []
    for record in evidence['inventory']:
        path = record['path']
        if 'generic-v10' in path or '2026-09-04f_' in path or '2026-09-04g_' in path:
            row = timing(path, record, 'pinned-budget-evidence')
            if row:
                rows.append(row)
    candidates = list((args.repo / 'data').rglob('*provenance.yaml'))
    local = []
    for path in candidates:
        if 'generic-v10' not in str(path) and '2026-09-04f_' not in str(path) and '2026-09-04g_' not in str(path):
            continue
        record = yaml.safe_load(path.read_text())
        if isinstance(record, dict):
            row = timing(path.relative_to(args.repo), record, 'local-ignore-independent')
            if row:
                local.append(row)
    reference = [r for r in rows if ('2026-09-04f_' in r['path'] and r['run']['project'] in ('CHORUS', 'VOICE')) or '2026-09-04g_' in r['path']]
    groups = {}
    for project in sorted({r['run']['project'] for r in reference}):
        spans = [r['first_to_last_call_span_seconds']/60 for r in reference if r['run']['project'] == project]
        groups[project] = {'n': len(spans), 'min_minutes': min(spans), 'median_minutes': statistics.median(spans), 'max_minutes': max(spans)}
    print(json.dumps({'evidence_commit': evidence['commit'], 'local_provenance_files_enumerated': len(candidates), 'reference_span_summary': groups, 'pinned': rows, 'local': local}, indent=2))


if __name__ == '__main__':
    main()
