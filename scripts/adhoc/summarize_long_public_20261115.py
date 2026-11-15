"""Diagnose run 43664211357; inputs downloaded pytest logs, outputs JSON; 2026-11-15."""
import json
from pathlib import Path
import sys

root = Path(sys.argv[1])
summary = {}
for case in ('pending', 'correction', 'variant'):
    lines = (root / case / 'pytest.log').read_text().splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith('E       AssertionError: {'))
    text = '{\n' + '\n'.join(line[8:] for line in lines[start + 1:] if line.startswith('E       '))
    result, _ = json.JSONDecoder().raw_decode(text)
    (root / case / 'assertion-result.json').write_text(json.dumps(result, indent=2) + '\n')
    phase = result['gates']['live_attribution']['result'].get('phase_history', {})
    metadata = result.get('captured_metadata', {})
    times = {Path(path).name: item['mtime_ns'] for path, item in metadata.items()
             if 'mtime_ns' in item}
    summary[case] = {
        'first_stop': result['first_stop'],
        'pending_tool_ids': phase.get('pending_tool_ids'),
        'last_helpers': phase.get('checks', [])[-4:],
        'phase': phase,
        'subscription_guard': result.get('subscription_guard'),
        'pytest_summary': lines[-1],
        'stderr_after_control_seconds': (
            times['stderr.txt'] - times['control.jsonl']) / 1_000_000_000,
        'local_case_files': sorted(path.name for path in (root / case).iterdir()),
    }
(root / 'case-summary.json').write_text(json.dumps(summary, indent=2) + '\n')
print(json.dumps(summary, indent=2))
