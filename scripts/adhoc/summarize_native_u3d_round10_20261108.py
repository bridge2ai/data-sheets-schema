#!/usr/bin/env python3
"""Archive D10 validation identities, failures and digests, 2026-11-08.

Inputs: explicit completed/incomplete D scratch runs and local source history.
Output: exclusive JSON manifest in assigned scratch. No tests or external I/O.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-native-u3d'
BASE = '59d2982cfa3f0e88acc66047d2d9428c61eed74b'
C_HEAD = '0a260a632394ce43ae2c8ed2144c05f7a8a21def'
A_HEAD = 'a6da0cd2a5227d768c9f3e21291a0ce848d66640'
ENV = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'GIT_NO_LAZY_FETCH': '1',
       'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_CONFIG_SYSTEM': '/dev/null'}
PROTECTED = (
    'src/data_sheets_schema/shared_generation.py', 'src/data_sheets_schema/api_runner.py',
    'src/download/prompts/canonical_hashes.yaml', 'tests/utils/run_spec_boundary_contracts.json',
    'scripts/adhoc/native_u1_packets', 'data/ATTIC', 'notes/matched_cborg_2026-09-13',
    'src/data_sheets_schema/native_execution.py', 'src/data_sheets_schema/native_execution_authority.py',
    'src/data_sheets_schema/native_execution_registration.py', 'src/data_sheets_schema/native_execution_gates.py',
    'src/data_sheets_schema/native_supervisor_gates.py', 'src/data_sheets_schema/native_attribution_registration.py',
    'src/data_sheets_schema/native_attribution_controller.py', 'src/data_sheets_schema/native_attribution_registration_v2.py',
    'src/data_sheets_schema/native_attribution_controller_v2.py', 'src/data_sheets_schema/native_controller_sources_v2.json',
)


def git(*args):
    return subprocess.check_output(['git', '--no-replace-objects', *args], cwd=ROOT,
                                   env=ENV, timeout=60).decode().strip()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(name):
    directory = SCRATCH / name
    if (directory != directory.resolve(strict=True) or not directory.is_dir()
            or '/' in name or not name.startswith('round10-')):
        raise ValueError('run must be a literal D10 scratch directory')
    plan = json.loads((directory / 'plan.json').read_text())
    outcome = json.loads((directory / 'outcome.json').read_text())
    stability = json.loads((directory / 'source-stability.json').read_text())
    cases = []
    if (directory / 'pytest.xml').is_file():
        for node in ET.parse(directory / 'pytest.xml').iter('testcase'):
            problem = next((item for item in node if item.tag in ('failure', 'error', 'skipped')), None)
            cases.append({'node': node.get('classname', '') + '::' + node.get('name', ''),
                'state': 'passed' if problem is None else problem.tag,
                'message': None if problem is None else problem.get('message'),
                'detail': None if problem is None else problem.text,
                'seconds': float(node.get('time', '0')),
                'properties': [dict(item.attrib) for item in node.iter('property')]})
    log = (directory / 'pytest.log').read_text()
    collected = re.findall(r'(\d+) tests? collected', log)
    return {'source_commit': plan['source_commit'], 'seconds': outcome['seconds'],
        'returncode': outcome['returncode'], 'cleanup_verified': outcome['cleanup_verified'],
        'source_stable': stability['unchanged'], 'source_origin_checks_passed':
            (outcome.get('worker') or {}).get('source_origin_checks_passed', False),
        'counts': dict(Counter(row['state'] for row in cases)), 'testcases': cases,
        'collected': int(collected[-1]) if collected else None,
        'artifacts': {path.name: sha(path) for path in sorted(directory.iterdir()) if path.is_file()}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('runs', nargs='+')
    args = parser.parse_args()
    if args.output.parent.resolve() != SCRATCH.resolve():
        raise ValueError('summary must stay directly under assigned scratch')
    value = {'head': git('rev-parse', 'HEAD'), 'branch': git('branch', '--show-current'),
        'merge_base_head': BASE, 'c_final_head': C_HEAD, 'runs': {name: run(name) for name in args.runs},
        'protected_diff': git('diff', '--name-only', BASE, 'HEAD', '--', *PROTECTED).splitlines(),
        'a_final_head': A_HEAD,
        'a_sources_differ_from_a6': git('diff', '--name-only', A_HEAD, 'HEAD', '--',
            'src/data_sheets_schema/native_execution_authority_v2.py',
            'src/data_sheets_schema/native_execution_registration_v2.py').splitlines(),
        'working_status': git('status', '--porcelain'),
        'scope': 'offline tests and fabricated observations; no native/provider admission'}
    with args.output.open('x') as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write('\n')
    print(json.dumps({'path': str(args.output), 'sha256': sha(args.output),
        'runs': {name: {key: row[key] for key in ('counts', 'returncode', 'collected')}
                 for name, row in value['runs'].items()}}, indent=2))


if __name__ == '__main__':
    main()
