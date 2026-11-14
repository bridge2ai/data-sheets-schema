"""Recheck PR 5968 delta test failures, 2026-11-14, issues 6236-6240.
Inputs: completed pytest log, checkout, scratch, label. Outputs: exact node list,
command metadata and pytest log under scratch. Uses the prescribed interpreter.
No provider calls; preserves all test outputs and uses four workers at most.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess

p = argparse.ArgumentParser()
p.add_argument('log', type=Path)
p.add_argument('checkout', type=Path)
p.add_argument('scratch', type=Path)
p.add_argument('label')
p.add_argument('--canary', action='store_true')
args = p.parse_args()
nodes = []
for line in args.log.read_text().splitlines():
    if line.startswith(('ERROR tests/', 'FAILED tests/')):
        node = line.split(' ', 1)[1].split(' - ', 1)[0]
        if node not in nodes:
            nodes.append(node)
if not nodes:
    raise SystemExit('No failing nodes found in completed log')
if args.canary:
    nodes = nodes[:1]
python = '/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python'
command = [python, '-m', 'pytest', *nodes, '-n', '4',
           '--basetemp=' + str(args.scratch / args.label),
           '--junitxml=' + str(args.scratch / (args.label + '.xml'))]
environment = dict(os.environ, PYTHONPATH=str(args.checkout / 'src'))
metadata = {'command': command, 'cwd': str(args.checkout),
            'PYTHONPATH': environment['PYTHONPATH'], 'nodes': nodes}
with (args.scratch / (args.label + '.log')).open('w') as output:
    result = subprocess.run(command, cwd=args.checkout, env=environment,
                            stdout=output, stderr=subprocess.STDOUT)
metadata['returncode'] = result.returncode
(args.scratch / (args.label + '.json')).write_text(json.dumps(metadata, indent=2) + '\n')
print(json.dumps(metadata, indent=2))
raise SystemExit(result.returncode)
