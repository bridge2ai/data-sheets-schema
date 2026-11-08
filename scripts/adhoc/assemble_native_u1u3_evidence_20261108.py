#!/usr/bin/env python3
"""U3-E 2026-11-08: plan/run bounded offline cohorts and retain exact outcomes.
Inputs: committed checkout and inherited rosters; outputs: scratch-native-u1u3.
PR assembly provenance; no publication, native execution or provider access.
"""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
EXEC = next(p for p in ROOT.parents if p.name == 'd4d-executions')
OUT = EXEC / 'scratch-native-u1u3'
PYTHON = EXEC.parent / 'data-sheets-schema/.venv/bin/python'
LOCK = EXEC / 'plans/native_quiet_window.lock'

def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts/adhoc' / (name + '.py'))
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value

def plan():
    groups = load('plan_native_u3d_round10_20261108').groups()
    groups.pop('collection')
    old = load('plan_native_u3c_round4_20261107').plan(PYTHON)['groups']
    for name in ('a-legacy-runtime', 'a-legacy-authority', 'b-shared', 'b-bc1', 'b-api-1', 'b-api-2', 'b-api-3', 'b-api-4'):
        groups[name] = old[name]['nodes']
    patterns = ('test_native*.py', 'test_api_*.py', 'test_shared_generation*.py', 'test_bc1*.py',
                'test_wave7*bc1*.py', 'test_wave7*5213*.py', 'test_source_heading*.py',
                'test_*schema_snapshot*.py', 'test_renderer_contract_captures.py',
                'test_generation_specificity*.py', 'test_neutral_generation_schema.py',
                'test_profiles.py', 'test_external_dataset_onboarding.py', 'test_prompt_registry.py')
    required = {str(p.relative_to(ROOT)) for pat in patterns for p in (ROOT / 'tests').glob(pat)}
    required.add('tests/test_download/test_api_runner.py')
    covered = {n.split('::')[0] for nodes in groups.values() for n in nodes}
    rest = sorted(required - covered)
    for i in range(4):
        groups['remaining-' + str(i + 1)] = rest[i::4]
    groups['collection'] = ['tests']
    return groups

def save(path, value):
    with path.open('x') as f:
        json.dump(value, f, indent=2, sort_keys=True)
        f.write('\n')

def run():
    groups = plan()
    save(OUT / 'suite-plan.json', groups)
    canary = json.loads((OUT / 'canary-retry/outcome.json').read_text())
    assert canary['returncode'] == 0 and canary['cleanup_verified']
    assert (OUT / 'canary-retry/pytest.xml').stat().st_size > 0
    for name, nodes in groups.items():
        while os.path.lexists(LOCK):
            print('Quiet window; waiting 60 seconds', flush=True)
            time.sleep(60)
        command = [str(PYTHON), '-S', '-P', '-B', str(ROOT / 'scripts/adhoc/run_native_u1u3_20261108.py'),
                   '--out', str(OUT / ('suite-' + name)), '--workers', '0' if name == 'collection' else '2']
        if name == 'collection':
            command.append('--collect-only')
        print('START ' + name, flush=True)
        result = subprocess.run(command + nodes, cwd=ROOT)
        print('END ' + name + ' returncode=' + str(result.returncode), flush=True)
        if result.returncode not in (0, 1):
            print('STOP: infrastructure/deadline/collection failure requires inspection', flush=True)
            return result.returncode
    return 0

def summarize():
    rows = []
    for path in sorted(OUT.glob('*/outcome.json')):
        row = {'run': path.parent.name, **json.loads(path.read_text())}
        xml = path.parent / 'pytest.xml'
        if xml.exists():
            cases = ET.parse(xml).findall('.//testcase')
            row['counts'] = {tag: sum(c.find(tag) is not None for c in cases) for tag in ('failure', 'error', 'skipped')}
            row['counts']['total'] = len(cases)
            row['nonpasses'] = [{'node': c.get('classname', '') + '::' + c.get('name', ''), 'tag': tag,
                                 'message': c.find(tag).get('message', ''), 'text': c.find(tag).text}
                                for c in cases for tag in ('failure', 'error', 'skipped') if c.find(tag) is not None]
        rows.append(row)
    save(OUT / 'validation-summary.json', rows)
    print(json.dumps([{'run': r['run'], 'seconds': r['seconds'], 'counts': r.get('counts'), 'returncode': r['returncode']} for r in rows], indent=2))

if __name__ == '__main__':
    if sys.argv[1:] == ['plan']:
        print(json.dumps(plan(), indent=2))
    elif sys.argv[1:] == ['run']:
        raise SystemExit(run())
    elif sys.argv[1:] == ['summarize']:
        summarize()
    else:
        raise SystemExit('choose plan, run, summarize')
