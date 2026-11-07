#!/usr/bin/env python3
"""Audit retained U3-A R4 evidence and source contract, 2026-11-07.

Inputs: named bounded test runs, mutation result files and actual-helper probe
under scratch-native-u3a-r4. Output: exclusive JSON summary, source/signature
digests and retained artifact hashes. No tests, network, imports of project code
or deletion. The report is produced from these saved witnesses, not exit codes.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
if ROOT.parent.name != 'd4d-executions' or ROOT.name != 'codex-native-u3a':
    raise RuntimeError('audit must run from the assigned U3-A worktree')
SCRATCH = ROOT.parent / 'scratch-native-u3a-r4'
BASE = 'dd3bb23bde5b8e04bb0fa65c040c5121474130fa'


def artifact(path):
    path = path.absolute()
    if path.is_symlink() or path.resolve() != path or not path.is_relative_to(SCRATCH):
        raise ValueError('evidence must be canonical inside round-4 scratch')
    raw = path.read_bytes()
    if not raw:
        raise ValueError('empty artifact: ' + str(path))
    return raw, hashlib.sha256(raw).hexdigest()


def read_json(path):
    raw, digest = artifact(path)
    return json.loads(raw), digest


def audit_run(directory):
    names = ('plan.json', 'outcome.json', 'pytest.xml', 'pytest.log', 'network.json',
             'origins-before.json', 'origins-after.json', 'subprocess-origins.json')
    values = {name: artifact(directory / name) for name in names}
    plan = json.loads(values['plan.json'][0])
    outcome = json.loads(values['outcome.json'][0])
    suites = list(ET.fromstring(values['pytest.xml'][0]).iter('testsuite'))
    counts = {key: sum(int(s.get(key, '0')) for s in suites)
              for key in ('tests', 'failures', 'errors', 'skipped')}
    expected = str(Path(plan['source_root']) / 'src') + ':' + plan['source_root']
    assert plan['workers'] <= 2 and plan['deadline_seconds'] == 3600
    assert plan['environment']['PYTHONPATH'] == expected
    assert plan['scratch_root'] == str(SCRATCH)
    assert plan['quiet_window_lock'] == str(ROOT.parent / 'plans/native_quiet_window.lock')
    assert outcome['cleanup_verified'] and not outcome['observed_surviving_pids']
    assert outcome['worker']['source_origin_checks_passed']
    assert outcome['seconds'] < 3600
    assert json.loads(values['network.json'][0])['network_bind_denied']
    assert json.loads(values['subprocess-origins.json'][0])['network']['network_bind_denied']
    return {'directory': str(directory), 'source_commit': plan['source_commit'],
            'counts': counts, 'returncode': outcome['returncode'],
            'seconds': outcome['seconds'], 'cleanup_verified': True,
            'sha256': {name: item[1] for name, item in values.items()}}


def git(*args):
    return subprocess.check_output(['/usr/bin/git', '--no-replace-objects',
        '-c', 'core.hooksPath=/dev/null', *args], cwd=ROOT,
        env={'PATH': '/usr/bin:/bin', 'GIT_NO_LAZY_FETCH': '1',
             'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_CONFIG_SYSTEM': '/dev/null'}, timeout=30)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--run', action='append', default=[], type=Path)
    parser.add_argument('--mutation', action='append', default=[], type=Path)
    parser.add_argument('--probe', type=Path)
    args = parser.parse_args()
    if args.out.resolve() != args.out or args.out.parent != SCRATCH:
        raise ValueError('summary must be a new direct file under round-4 scratch')
    source = ROOT / 'src/data_sheets_schema/native_execution_registration_v2.py'
    source_raw = source.read_bytes()
    tree = ast.parse(source_raw)
    signatures = {node.name: ast.unparse(node.args) for node in tree.body
                  if isinstance(node, ast.FunctionDef) and node.name in ('verified', 'admit')}
    inputs = next(ast.literal_eval(node.value) for node in tree.body
                  if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name)
                     and t.id == '_REBUILD_INPUTS' for t in node.targets))
    signature = 'rebuild_v2_body(*, ' + ', '.join(inputs) + ')'
    bridge_tree = ast.parse((ROOT / 'tests/test_native_execution_bridge_v2.py').read_bytes())
    fixture = next(ast.literal_eval(node.value) for node in bridge_tree.body
                   if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name)
                      and t.id == 'CONSUMER_SOURCE' for t in node.targets))
    authority = 'src/data_sheets_schema/native_execution_authority_v2.py'
    assert git('show', BASE + ':' + authority) == (ROOT / authority).read_bytes()
    assert git('show', 'HEAD:' + str(source.relative_to(ROOT))) == source_raw
    result = {'head': git('rev-parse', 'HEAD').decode().strip(), 'base': BASE,
              'source_sha256': hashlib.sha256(source_raw).hexdigest(),
              'entry_signatures': signatures, 'consumer_signature': signature,
              'signature_sha256_utf8_no_newline': hashlib.sha256(signature.encode()).hexdigest(),
              'synthetic_committed_consumer_source_sha256': hashlib.sha256(fixture).hexdigest(),
              'authority_map_guard_loader_unchanged': True,
              'runs': [audit_run(path) for path in args.run], 'mutations': []}
    for path in args.mutation:
        value, digest = read_json(path)
        assert value['status'] == 'killed'
        control = audit_run(Path(value['baseline']['evidence']))
        mutant = audit_run(Path(value['mutant']['evidence']))
        assert control['source_commit'] == value['base']
        assert mutant['source_commit'] == value['mutant_commit']
        assert control['returncode'] == 0 and control['counts']['failures'] == 0
        assert mutant['returncode'] == 1 and mutant['counts']['failures'] > 0
        assert not mutant['counts']['errors'] and not mutant['counts']['skipped']
        result['mutations'].append({'case': value['case'], 'base': value['base'],
            'mutant_commit': value['mutant_commit'], 'result_sha256': digest,
            'control': control, 'mutant': mutant})
    if args.probe:
        probe, digest = read_json(args.probe / 'probe-result.json')
        outcome, outcome_digest = read_json(args.probe / 'outcome.json')
        network, network_digest = read_json(args.probe / 'network.json')
        assert probe['valid'] and not probe['executed_forged_bytecode']
        assert probe['source']['unchanged'] and probe['retained_forged_cache']['unchanged']
        assert network['network_bind_denied']
        assert outcome['returncode'] == 0 and outcome['stopped'] is None
        assert outcome['parent_error'] is None and not outcome['timed_out']
        assert outcome['cleanup_verified'] and outcome['process_group_alive'] is False
        assert not outcome['observed_survivors'] and not outcome['observation_errors']
        assert outcome['result_exists'] and outcome['result_valid']
        assert outcome['result_sha256'] == digest and outcome['elapsed_seconds'] < 180
        result['probe'] = {'result': probe, 'outcome': outcome,
            'sha256': {'probe-result.json': digest, 'outcome.json': outcome_digest,
                       'network.json': network_digest}}
    with args.out.open('x') as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps({'head': result['head'], 'runs': len(result['runs']),
                      'mutations_killed': len(result['mutations']),
                      'summary_sha256': hashlib.sha256(args.out.read_bytes()).hexdigest()}))


if __name__ == '__main__':
    main()
