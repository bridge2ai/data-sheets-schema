#!/usr/bin/env python3
"""Save G2 issue and immutable baseline evidence, 2026-11-14.
Inputs: assigned GitHub issue bodies (read-only), exact baseline Git blobs and
review files. Outputs: exclusive scratch evidence. No project runtime or sends.
"""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT.parent / 'scratch-g2-20261114'
BASE = 'dc7fa08c508da6acfc91ca7c8998133e78f05795'
ISSUES = (6207, 6208, 6215, 6216, 6217, 6218, 6224, 6225)
FILES = ('native_launch_sequence.py', 'native_sequence_start.py', 'native_host_power.py',
         'native_execution_orchestration.py', 'native_execution.py', 'native_subscription_guard_v2.py')


def pin(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def main():
    directory = OUT / 'baseline'
    directory.mkdir(exist_ok=False)
    issues = []
    for number in ISSUES:
        command = ['gh', 'issue', 'view', str(number), '--repo', 'bridge2ai/data-sheets-schema',
                   '--json', 'number,title,body,state,url']
        value = json.loads(subprocess.check_output(command, cwd=ROOT))
        target = directory / ('issue-' + str(number) + '.json')
        target.write_text(json.dumps({'command': command, 'issue': value}, indent=2) + '\n')
        issues.append(pin(target))
    sources = []
    for name in FILES:
        relative = 'src/data_sheets_schema/' + name
        command = ['git', 'show', BASE + ':' + relative]
        raw = subprocess.check_output(command, cwd=ROOT)
        target = directory / name
        target.write_bytes(raw)
        sources.append({'source_relative_path': relative, 'command': command, 'snapshot': pin(target)})
    reviews = []
    for name in ('pr5968_adversarial_B_codex_2026-11-13.md', 'pr5968_adversarial_B_claude_2026-11-13.md'):
        reviews.append(pin(ROOT.parent / 'plans/reviews' / name))
    value = {'base': BASE, 'issues': issues, 'sources': sources, 'reviews': reviews,
             'scope': 'Read-only evidence; no GitHub write, runtime invocation or protected-file edit.'}
    target = directory / 'index.json'
    target.write_text(json.dumps(value, indent=2) + '\n')
    print(json.dumps(pin(target)))


if __name__ == '__main__':
    main()
