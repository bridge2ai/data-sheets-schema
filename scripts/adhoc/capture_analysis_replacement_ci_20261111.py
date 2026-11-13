#!/usr/bin/env python3
"""Read-only CI snapshot for analysis PR5843 replacement PR5853, 2026-11-11.
Inputs: fixed old/new run IDs and Git heads, anonymous-content GitHub read queries.
Outputs: fresh ignored tmp/analysis-replacement-ci-<UTC>/ JSON responses and duration
summary. No test, dispatch, cancellation, remote write, or notification is performed.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
REPO = 'bridge2ai/data-sheets-schema'
RUNS = (42963052291, 42966522505)
HEADS = ('aa86cf0039293a042666751d69dd703a20bfabf5',
         '76a443ee34103ed18f30041c111f9f2aae1af40e')


def command(args):
    return subprocess.check_output(args, cwd=ROOT, text=True, timeout=30)


def utc():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def parse(value):
    if not value or value.startswith('0001-'):
        return None
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def main():
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    output = ROOT / ('tmp/analysis-replacement-ci-' + stamp)
    output.mkdir(parents=True, exist_ok=False)
    fields = 'databaseId,headSha,status,conclusion,createdAt,updatedAt,startedAt,url,workflowName,event,jobs'
    queries = {f'run-{run}': ['gh', 'run', 'view', str(run), '--repo', REPO, '--json', fields]
               for run in RUNS}
    for number in (5843, 5853):
        queries[f'pr-{number}'] = ['gh', 'pr', 'view', str(number), '--repo', REPO, '--json',
            'number,state,isDraft,headRefName,headRefOid,baseRefName,baseRefOid,url,statusCheckRollup,closedAt']
        queries[f'pr-{number}-merge'] = ['gh', 'api', f'repos/{REPO}/pulls/{number}', '--jq',
            '{number,state,merge_commit_sha,head: .head.sha,base: .base.sha}']
    responses = {}
    with ThreadPoolExecutor(max_workers=4) as pool:
        pending = {name: pool.submit(command, args) for name, args in queries.items()}
        for name, task in pending.items():
            raw = task.result()
            (output / (name + '.json')).write_text(raw)
            responses[name] = json.loads(raw)
    for number in (5843, 5853):
        sha = responses[f'pr-{number}-merge']['merge_commit_sha']
        name = f'pr-{number}-merge-tree'
        args = ['gh', 'api', f'repos/{REPO}/git/commits/{sha}', '--jq',
                '{sha,tree: .tree.sha,parents: [.parents[].sha]}']
        queries[name] = args
        raw = command(args)
        (output / (name + '.json')).write_text(raw)
        responses[name] = json.loads(raw)
    now = datetime.now(timezone.utc)
    summary = {'observed_at': now.isoformat(timespec='seconds'), 'runs': [],
               'head_trees': {sha: command(['git', 'rev-parse', sha + '^{tree}']).strip() for sha in HEADS},
               'merge_trees': {str(number): responses[f'pr-{number}-merge-tree'] for number in (5843, 5853)},
               'raw_directory': str(output)}
    for run in RUNS:
        record = responses[f'run-{run}']
        created = parse(record['createdAt'])
        jobs = []
        counts = {}
        for job in record['jobs']:
            status = job['status'] + '/' + (job['conclusion'] or 'pending')
            counts[status] = counts.get(status, 0) + 1
            started, completed = parse(job['startedAt']), parse(job['completedAt'])
            # Queued startedAt can be a scheduling placeholder. Do not call it execution.
            wall = ((completed - started).total_seconds() if completed and started
                    and job['status'] == 'completed' and job['conclusion'] != 'skipped' else None)
            running = ((now - started).total_seconds() if started and job['status'] == 'in_progress' else None)
            execution = []
            for step in job.get('steps', []):
                if not step['name'].startswith(('Run the ', 'Exercise ')):
                    continue
                begin, end = parse(step['startedAt']), parse(step['completedAt'])
                execution.append({'name': step['name'], 'status': step['status'],
                    'started_at': step['startedAt'], 'completed_at': step['completedAt'],
                    'completed_seconds': (end - begin).total_seconds() if begin and end else None})
            jobs.append({'id': job['databaseId'], 'name': job['name'], 'status': status,
                         'started_at': job['startedAt'], 'completed_at': job['completedAt'],
                         'completed_wall_seconds': wall, 'running_elapsed_seconds': running,
                         'queue_to_started_seconds': (started - created).total_seconds()
                             if started and job['status'] != 'queued' and job['conclusion'] != 'skipped' else None,
                         'execution_steps': execution})
        summary['runs'].append({'id': run, 'head': record['headSha'], 'status': record['status'],
            'conclusion': record['conclusion'], 'created_at': record['createdAt'],
            'updated_at': record['updatedAt'], 'observed_elapsed_seconds': (now - created).total_seconds(),
            'terminal_created_to_updated_seconds': (parse(record['updatedAt']) - created).total_seconds()
                if record['status'] == 'completed' else None, 'job_counts': counts, 'jobs': jobs})
    (output / 'commands.json').write_text(json.dumps(queries, indent=2) + '\n')
    summary['helper_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    summary['response_sha256'] = {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                                  for path in output.glob('*.json')}
    (output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps({'summary_path': str(output / 'summary.json'),
                     'observed_at': summary['observed_at'],
                     'merge_trees': summary['merge_trees'],
                     'runs': [{key: value for key, value in run.items() if key != 'jobs'}
                              for run in summary['runs']]}, indent=2))


if __name__ == '__main__':
    main()
