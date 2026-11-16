#!/usr/bin/env python3
"""Summarize saved CI logs and local lane evidence for draft PR 5968.

Purpose: helper handoff provenance, 2026-11-16.
Inputs: scratch directory containing downloaded logs, job JSON and lane outputs.
Outputs: JSON summary on stdout; no network calls or mutations.
"""
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

scratch = Path(sys.argv[1])
report = {'ci_failures': {}, 'pr_shards': [], 'local_lanes': {}}
for path in sorted(scratch.glob('*.log')):
    failures = []
    for line in path.read_text(errors='replace').splitlines():
        if 'FAILED tests/' in line and ' - ' in line:
            failures.append(line.split('FAILED ', 1)[1])
    if failures:
        report['ci_failures'][path.name] = failures
jobs = scratch / 'pr-jobs.json'
if jobs.is_file() and jobs.stat().st_size:
    for job in json.loads(jobs.read_text())['jobs']:
        if '/ shard ' in job['name']:
            report['pr_shards'].append({key: job[key] for key in
                ('id', 'name', 'status', 'conclusion')})
for path in sorted(scratch.glob('*/lane_summary.json')):
    lane = json.loads(path.read_text())
    xml = path.parent / 'results/unit.xml'
    suites = [] if not xml.is_file() else [node.attrib for node in
        ET.parse(xml).getroot().iter('testsuite')]
    report['local_lanes'][path.parent.name] = {
        'returncode': lane['overall_returncode'], 'steps': lane['steps'],
        'testsuites': suites}
print(json.dumps(report, indent=2, sort_keys=True).replace(chr(64), '[at]'))
