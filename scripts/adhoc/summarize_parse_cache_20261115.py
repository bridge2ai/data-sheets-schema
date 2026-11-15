"""Summarize saved before/after timing and profile evidence as JSON.

Input/output: assigned scratch directory. Lead parse-cache task, 2026-11-15.
"""
import json
from pathlib import Path
import pstats
import sys

root = Path(sys.argv[1])
version = sys.argv[2] if len(sys.argv) > 2 else 'v3'
if not version.isalnum():
    raise ValueError('measurement version must be an alphanumeric directory suffix')
rows = []
for mode in ('response', 'publication'):
    for profiled in (False, True):
        suffix = '-profile' if profiled else ''
        before_name = 'cache-before-' + mode + suffix
        if mode == 'response' and not profiled:
            before_name += '-v2'
        before = json.loads((root / before_name / 'metrics.json').read_text())
        after_dir = root / ('cache-after-' + version + '-' + mode + suffix)
        after = json.loads((after_dir / 'metrics.json').read_text())
        row = dict(mode=mode, profiled=profiled, before=before, after=after,
                   wall_speedup=before['wall_seconds']/after['wall_seconds'],
                   cpu_speedup=before['cpu_seconds']/after['cpu_seconds'])
        if profiled:
            stats = pstats.Stats(str(after_dir / 'costs.prof'))
            row['costs'] = [dict(file=key[0], line=key[1], function=key[2], calls=value[1],
                                 self_seconds=value[2], cumulative_seconds=value[3])
                            for key, value in sorted(stats.stats.items(), key=lambda item: item[1][3], reverse=True)[:30]]
        rows.append(row)
(root / ('parse-cache-summary-' + version + '.json')).write_text(json.dumps(rows, indent=2))
print(json.dumps(rows, indent=2))
