"""Extract profile costs for the variant handoff, 2026-11-15.

Input: profile directory. Output: profile-costs.json beside the profiles.
Cumulative costs overlap and must not be added together.
"""
import json
from pathlib import Path
import pstats
import sys

root = Path(sys.argv[1])
results = {}
for path in sorted(root.glob('*.prof')):
    stats = pstats.Stats(str(path))
    rows = []
    for (file, line, name), (primitive, calls, own, cumulative, callers) in stats.stats.items():
        if name in ('run', '_bounded_json', 'nesting_exceeds', '_state', 'runtime_token',
                    '_derive_uncached', '_fresh_schema_data', '_read', '_open') or 'openssl_sha256' in name:
            rows.append({'file': file, 'line': line, 'function': name, 'calls': calls,
                         'own_seconds': own, 'cumulative_seconds': cumulative})
    results[path.name] = sorted(rows, key=lambda row: -row['cumulative_seconds'])
output = root / 'profile-costs.json'
output.write_text(json.dumps(results, indent=2))
print(output)
