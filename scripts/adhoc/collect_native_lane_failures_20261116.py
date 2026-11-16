"""Collect failed native CI logs for PR 5968; inputs job JSON, outputs logs and summary; 2026-11-16."""
import argparse
import json
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument('scratch', type=Path)
parser.add_argument('--limit', type=int)
args = parser.parse_args()
jobs = {}
for name in ('pr-jobs.json', 'dispatch-jobs.json'):
    data = json.loads((args.scratch / name).read_text())
    assert len(data['jobs']) == data['total_count'], 'pagination required'
    for job in data['jobs']:
        if job['conclusion'] == 'failure' and 'native case' in job['name']:
            jobs[job['id']] = job
rows = []
for job in list(jobs.values())[:args.limit]:
    path = args.scratch / ('job-' + str(job['id']) + '.log')
    if not path.exists() or not path.stat().st_size:
        result = subprocess.run(['gh', 'api', '--allow-escape-sequences',
            'repos/bridge2ai/data-sheets-schema/actions/jobs/' + str(job['id']) + '/logs'],
            check=True, capture_output=True)
        path.write_bytes(result.stdout)
    assert path.stat().st_size
    lines = path.read_text().splitlines()
    failures = [line for line in lines if 'FAILED tests/' in line]
    rows.append({'id': job['id'], 'name': job['name'], 'log': str(path), 'failures': failures})
(args.scratch / 'failed-native-summary.json').write_text(json.dumps(rows, indent=2) + '\n')
for row in rows:
    print(row['name'], row['id'])
    print('\n'.join(row['failures']))
