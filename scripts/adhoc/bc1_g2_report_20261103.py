#!/usr/bin/env python3
# Purpose: retain integration evidence counts, byte table, and lost-line details.
# Inputs: local commit graph and immutable scratch results; outputs: JSON/Markdown
# under the designated external review folder. Integration task 9, 2026-11-03.
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
TARGET = '3f673180d6959f741d51db88f8c1fa6867e4d81d'
SCRATCH = ROOT.parent / 'scratch-bc1g2'


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT).decode()


def summarize(output):
    output.mkdir(parents=True, exist_ok=True)
    comparison = json.loads((SCRATCH / 'byte-proof/.bc1-byte-evidence/integration-comparison.json').read_bytes())
    units = {}
    for result in sorted(SCRATCH.rglob('result.json')):
        if any(part in ('tmp', '.git') for part in result.relative_to(SCRATCH).parts):
            continue
        data = json.loads(result.read_bytes())
        if 'suites' not in data or 'identity' not in data:
            continue
        events_path = result.with_name('events.jsonl')
        events = [json.loads(line) for line in events_path.read_text().splitlines()] if events_path.exists() else []
        failures = result.with_name('failures.jsonl')
        data['failures'] = [json.loads(line) for line in failures.read_text().splitlines()] if failures.exists() else []
        data['call_outcomes'] = dict(Counter(e['outcome'] for e in events if e['when'] == 'call'))
        data['report_sha256'] = hashlib.sha256(result.read_bytes()).hexdigest()
        units[str(result.parent.relative_to(SCRATCH))] = data
    lost = json.loads((SCRATCH / 'lost-lines-merge.json').read_bytes())
    extra = {}
    for item in lost['files']:
        path = item['path']
        target_lines = set(git('show', TARGET + ':' + path).splitlines())
        merged_lines = set(git('show', '009d32bfb:' + path).splitlines())
        already = {r['line'] for r in item['lines']}
        remaining = sorted(line for line in target_lines - merged_lines - already if line.strip())
        if remaining:
            extra[path] = remaining
    summary = {'head': git('rev-parse', 'HEAD').strip(),
        'commits': git('log', '--first-parent', '--format=%H %s', TARGET + '..HEAD').splitlines(),
        'units': units, 'lost_lines': lost, 'additional_target_lines': extra,
        'byte_proof': {'accepted': comparison['accepted'],
            'payloads': len(comparison['rows']), 'binding_checks': len(comparison['binding_checks']),
            'changed_pin_leaves': sum(leaf['kind'] == 'pins' for row in comparison['rows'] for leaf in row['differences']),
            'moved_code': comparison['moved_code'], 'unverified': [row for row in comparison['binding_checks'] if row['unverified']]}}
    (output / 'summary.json').write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')
    table = ['| Request | Incoming bytes | Integrated bytes | Delta |', '|---|---:|---:|---:|']
    for row in comparison['rows']:
        table.append(f"| `{row['name']}` | {row['before_bytes']} | {row['after_bytes']} | +{row['after_bytes'] - row['before_bytes']} |")
    (output / 'byte-table.md').write_text('\n'.join(table) + '\n')
    print('head', summary['head'], 'byte proof', summary['byte_proof'])
    print('additional target lines', json.dumps(extra))
    for name, unit in units.items():
        print(name, unit['returncode'], unit['call_outcomes'], 'suites', unit['suites'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('output', type=Path)
    summarize(parser.parse_args().output)
