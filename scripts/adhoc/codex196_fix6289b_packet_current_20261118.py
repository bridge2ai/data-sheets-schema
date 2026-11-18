"""Capture current packet-fixture setup timings for F3, 2026-11-18.
Input: completed shard 2 log and retained fixture-consumer declaration.
Output: current cold-fixture sensitivity; no tests or source edits.
"""
from pathlib import Path
import codex196_fix6289b_capacity_20261118 as c
old = c.OLD / 'simulation-inputs-007/fixture-sensitivity.json'
import json
fixture = json.loads(old.read_bytes())['fixtures'][0]
path = c.OUT / 'packet-shard2.log'
c.fetch(path, f'repos/{c.REPO}/actions/jobs/134570948594/logs')
rows = c.parse_log(path)
setup = {row['node']: row['seconds'] for row in rows['printed_phases'] if row['phase'] == 'setup'
         and row['node'] in fixture['consumer_nodes']}
if not setup:
    raise ValueError('current packet log omitted every module setup')
fixture.update(cold_setup_seconds=max(setup.values()), recorded_setup_seconds=setup,
    basis='Current run printed packet-fixture setup phases; add maximum observed cold setup per new worker module entry. Missing setup phases subtract zero. This is not an upper bound.',
    current_source=c.pin(path), prior_declaration=c.pin(old))
value = {'fixtures': [fixture]}
target = c.OUT / 'current-fixture-model.json'
c.save(target, c.encode(value))
print(c.encode({'fixture_model': c.pin(target), 'cold_setup_seconds': fixture['cold_setup_seconds'],
                'recorded_setup_seconds': setup}).decode())
