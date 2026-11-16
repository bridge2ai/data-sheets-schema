"""Summarize saved CI failures for PR 5968; input scratch JSON/logs, output cause JSON; 2026-11-16."""
import json
from pathlib import Path
import sys

scratch = Path(sys.argv[1])
rows = json.loads((scratch / 'failed-native-summary.json').read_text())
groups = {}
for row in rows:
    for failure in row['failures']:
        test = failure.split('FAILED ', 1)[1].split(' - ', 1)[0]
        if 'saved_readback_revalidates' in test or 'saved_failure_rechecks' in test:
            cause = 'frozen clock omitted fresh D156 guard module'
        elif 'pre_dispatch_failure' in test:
            cause = 'process allowlist omitted exact fresh verifier'
        elif 'declared_runtime_failure' in test:
            cause = 'sidecar fault injection targeted ambient power module'
        elif 'subscription_expiring' in test:
            cause = 'clock advanced before deferred capture and on ambient guard'
        elif 'unplug_before' in test:
            cause = 'exception assertion targeted ambient power class'
        elif 'unplug_after' in test:
            cause = 'power observer targeted ambient function'
        elif 'merged_omissions' in test or 'pending_floor_public' in test:
            cause = 'helper environment fixture not inherited by public sibling module'
        else:
            raise AssertionError(test)
        group = groups.setdefault(cause, {'jobs': [], 'tests': []})
        group['jobs'].append(row['id'])
        if test not in group['tests']:
            group['tests'].append(test)
result = {'failed_jobs': len(rows), 'unique_tests': len({test for group in groups.values() for test in group['tests']}), 'groups': groups}
(scratch / 'causes.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
