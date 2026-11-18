"""Diagnose F3 and collect bounded CI timing evidence for issue 6289, 2026-11-18.

Inputs: run 44235627132, three retained cancellation logs, prior actual collection.
Outputs: small immutable evidence and capacity summaries in the assigned scratch.
Read-only GitHub API calls; no tests, code changes, providers, or native runtime.
"""
import argparse
from collections import Counter, defaultdict, deque
from datetime import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import zipfile
import xml.etree.ElementTree as ET

RUN = 44235627132
REPO = 'bridge2ai/data-sheets-schema'
BASE = Path('/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions')
ROOT = BASE / 'codex196-fix6289b-20261118'
REPORT = BASE / 'codex-development-efficiency-20261111'
OUT = BASE / 'scratch-codex196-fix6289b-20261118/f3'
OLD = BASE / 'scratch-codex196-fix6289-20261118'
LOGS = BASE / 'scratch-lead-ci-gaps-7b98-20261117/disk-20261118'
CANCELLED = {7: 134570948409, 10: 134570948684, 12: 134570948739}


def encode(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False).replace(chr(64), '\\u0040') + '\n').encode()


def pin(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def save(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != raw:
            raise ValueError('refusing different existing evidence: ' + str(path))
    else:
        path.write_bytes(raw)
    return pin(path)


def fetch(path, endpoint):
    if path.is_file():
        return path.read_bytes()
    args = ['gh', 'api', '--allow-escape-sequences', endpoint]
    value = subprocess.run(args, capture_output=True, timeout=60)
    save(path.with_suffix(path.suffix + '.command.json'), encode({
        'argv': args, 'returncode': value.returncode,
        'stderr': value.stderr.decode(errors='replace')}))
    value.check_returncode()
    save(path, value.stdout)
    return value.stdout


def stamp(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def parse_log(path):
    starts, finishes, pending, durations = [], [], defaultdict(deque), []
    active = False
    cancellation = None
    workers, items = None, None
    for number, raw in enumerate(path.read_text().splitlines(), 1):
        if 'Z ' not in raw:
            continue
        timestamp, text = raw.split('Z ', 1)
        timestamp += 'Z'
        text = re.sub(r'\x1b\[[0-9;]*m', '', text).rstrip()
        header = re.search(r'(\d+) workers \[(\d+) items\]', text)
        if header:
            workers, items = map(int, header.groups())
            active = True
        if 'The operation was canceled' in text or 'operation was canceled' in text:
            cancellation = cancellation or timestamp
        finish = re.fullmatch(r'\[(gw\d+)\] \[\s*(\d+)%\] (PASSED|FAILED|SKIPPED|ERROR|XFAIL|XPASS) ((?:tests|notes)/.*?\.py::.*)', text)
        if finish:
            worker, progress, status, node = finish.groups()
            row = {'node': node, 'timestamp': timestamp, 'worker': worker, 'status': status, 'line': number}
            if pending[node]:
                begun = pending[node].popleft()
                row['start_line'] = begun['line']
                row['start_timestamp'] = begun['timestamp']
                row['interval_seconds'] = (stamp(timestamp) - stamp(begun['timestamp'])).total_seconds()
            finishes.append(row)
        elif active and re.fullmatch(r'(?:tests|notes)/.*?\.py::.*', text):
            row = {'node': text, 'timestamp': timestamp, 'line': number}
            starts.append(row)
            pending[text].append(row)
        phase = re.fullmatch(r'([0-9.]+)s\s+(setup|call|teardown)\s+((?:tests|notes)/.*?\.py::.*)', text)
        if phase:
            seconds, name, node = phase.groups()
            durations.append({'node': node, 'phase': name, 'seconds': float(seconds), 'line': number})
    unfinished = [row for rows in pending.values() for row in rows]
    for row in unfinished:
        row['elapsed_until_cancellation_seconds'] = ((stamp(cancellation) - stamp(row['timestamp'])).total_seconds()
                                                     if cancellation else None)
    return {'log': pin(path), 'workers': workers, 'items': items, 'cancellation': cancellation,
            'started_count': len(starts), 'finished_count': len(finishes),
            'unfinished': unfinished, 'starts': starts, 'finishes': finishes, 'printed_phases': durations}


def pending_report():
    rows = {str(shard): parse_log(LOGS / f'job-{job}.log') for shard, job in CANCELLED.items()}
    path = OUT / 'cancelled-shards.json'
    save(path, encode({'run': RUN, 'shards': rows, 'producer': pin(Path(__file__))}))
    print(encode({'path': pin(path), 'shards': {shard: {key: row[key] for key in
        ('workers', 'items', 'started_count', 'finished_count', 'cancellation', 'unfinished')}
        for shard, row in rows.items()}}).decode())


def metadata():
    run = fetch(OUT / 'run.json', f'repos/{REPO}/actions/runs/{RUN}')
    artifacts = fetch(OUT / 'artifacts.json', f'repos/{REPO}/actions/runs/{RUN}/artifacts?per_page=100')
    jobs = fetch(OUT / 'jobs.json', f'repos/{REPO}/actions/runs/{RUN}/jobs?per_page=100')
    artifacts, jobs = json.loads(artifacts), json.loads(jobs)
    if artifacts['total_count'] > 100 or jobs['total_count'] > 100:
        raise ValueError('pagination required')
    print(encode({'run': json.loads(run)['head_sha'], 'artifacts': [{key: row[key] for key in
        ('id', 'name', 'size_in_bytes', 'expired')} for row in artifacts['artifacts']
        if re.fullmatch(r'tests-py3\.12-shard\d+', row['name'])],
        'jobs': [{key: row[key] for key in ('id', 'name', 'conclusion', 'started_at', 'completed_at')}
                 for row in jobs['jobs'] if re.search(r'/ shard \d+$', row['name'])]}).decode())


def artifact(identifier):
    metadata = json.loads((OUT / 'artifacts.json').read_bytes())
    row = next(row for row in metadata['artifacts'] if row['id'] == identifier)
    if not re.fullmatch(r'tests-py3\.12-shard\d+', row['name']) or row['expired'] or row['size_in_bytes'] > 10_000_000:
        raise ValueError('not an authorized small ordinary-shard artifact')
    path = OUT / 'artifacts' / f'{identifier}.zip'
    fetch(path, f'repos/{REPO}/actions/artifacts/{identifier}/zip')
    documents, count = [], 0
    with zipfile.ZipFile(path) as archive:
        for item in archive.infolist():
            if not item.filename.endswith('.xml'):
                continue
            if item.file_size > 50_000_000 or Path(item.filename).is_absolute() or '..' in Path(item.filename).parts:
                raise ValueError('unsafe XML artifact')
            target = OUT / 'artifacts' / row['name'] / item.filename
            raw = archive.read(item)
            elements = list(ET.fromstring(raw).iter('testcase'))
            if not elements:
                raise ValueError('empty XML artifact')
            documents.append(save(target, raw))
            count += len(elements)
    if not documents:
        raise ValueError('no XML documents')
    receipt = {'artifact': row, 'archive': pin(path), 'documents': documents, 'testcase_occurrences': count}
    save(OUT / 'artifacts' / f'{identifier}-receipt.json', encode(receipt))
    print(encode(receipt).decode())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['pending', 'metadata', 'artifact'])
    parser.add_argument('--id', type=int)
    args = parser.parse_args()
    {'pending': pending_report, 'metadata': metadata,
     'artifact': lambda: artifact(args.id)}[args.action]()


if __name__ == '__main__':
    main()
