#!/usr/bin/env python3
"""Plan 15 U3-A r4 mutants; run the remaining 14 after MA, 2026-11-07.

Inputs: exact local --base, physical dependency --python, new --out case parent,
and (for --run) the independently completed MA --canary result.json.
Outputs: plans, per-helper console logs, immutable progress records and summary,
all under scratch-native-u3a-r4. Default --plan is read-only; --plan-out may save
that plan to a new file there. No production imports or native/provider calls.
The existing helper owns each matched control/mutant and its 3600s test limit.
This coordinator never kills a helper or its descendants: interruption requests
stop after the current supervised helper finishes and cleanup is audited.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[2]
_roots = [path for path in ROOT.parents if path.name == 'd4d-executions']
if (len(_roots) != 1 or _roots[0] != _roots[0].resolve(strict=True)
        or not (_roots[0] / 'plans').is_dir()):
    raise RuntimeError('source must be below the canonical d4d-executions root')
EXECUTIONS = _roots[0]
SCRATCH = EXECUTIONS / 'scratch-native-u3a-r4'
LOCK = EXECUTIONS / 'plans/native_quiet_window.lock'
HELPER = ROOT / 'scripts/adhoc/mutate_native_u3a_round2_20261107.py'
SELF = 'scripts/adhoc/run_native_u3a_round4_mutations_20261107.py'
CASES = ('MA', 'MB', 'MC', 'MD', 'ME', 'MF', 'MG', 'MI', 'MJ', 'MK', 'ML', 'MM', 'MN', 'MO', 'MP')
MAX_EVIDENCE_BYTES = 4 * 1024 * 1024


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def environment():
    return {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'LANG': 'en_US.UTF-8',
        'GIT_NO_LAZY_FETCH': '1', 'GIT_CONFIG_GLOBAL': os.devnull,
        'GIT_CONFIG_SYSTEM': os.devnull, 'PYTHONDONTWRITEBYTECODE': '1',
        'PYTHONNOUSERSITE': '1', 'PYTHONSAFEPATH': '1',
        'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1', 'PIP_NO_INDEX': '1', 'UV_OFFLINE': '1'}


def scratch_path(value):
    path = value.absolute()
    if path != path.resolve() or path == SCRATCH or not path.is_relative_to(SCRATCH):
        raise ValueError('path must be canonical and strictly inside round-4 scratch')
    return path


def outside_checkout(path):
    if any((parent / '.git').exists() for parent in (path, *path.parents)
           if parent.is_relative_to(EXECUTIONS)):
        raise ValueError('campaign evidence must stay outside source checkouts')


def read(path):
    path = scratch_path(path)
    if not path.is_file() or path.stat().st_size > MAX_EVIDENCE_BYTES:
        raise ValueError('evidence must be a bounded regular file')
    raw = path.read_bytes()
    if not raw or len(raw) > MAX_EVIDENCE_BYTES:
        raise ValueError('evidence is empty or exceeded its bound')
    return raw


def save(path, value):
    path = scratch_path(path)
    outside_checkout(path)
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')


def quiet():
    if LOCK.exists():
        raise RuntimeError('quiet-window lock exists; no next helper started')


def command(args, case):
    return [str(args.python), '-S', '-P', '-B', str(HELPER),
            '--base', args.base, '--case', case]


def plans(args):
    result = {}
    helper_sha = sha(HELPER.read_bytes())
    for case in CASES:
        quiet()
        planned = subprocess.run(command(args, case), cwd=ROOT, env=environment(),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        value = json.loads(planned.stdout)
        if (value['case'] != case or value['base'] != args.base
                or value['harness_sha256'] != helper_sha
                or value['scratch_root'] != str(SCRATCH)
                or value['quiet_window_lock'] != str(LOCK)):
            raise ValueError('mutation helper returned a mismatched plan for ' + case)
        result[case] = value
    return result


def checked_result(path, expected):
    raw = read(path)
    value = json.loads(raw)
    for key in ('case', 'base', 'source_sha256', 'mutated_source_sha256',
                'test_node', 'harness_sha256'):
        if value.get(key) != expected[key]:
            raise ValueError('saved mutation identity differs: ' + key)
    if value.get('status') != 'killed':
        raise ValueError('mutation did not produce a valid kill')
    witnesses = {}
    for phase, returncode in (('baseline', 0), ('mutant', 1)):
        recorded = value[phase]
        directory = scratch_path(Path(recorded['evidence']))
        outcome_raw, xml_raw = read(directory / 'outcome.json'), read(directory / 'pytest.xml')
        if (sha(outcome_raw) != recorded['outcome_sha256']
                or sha(xml_raw) != recorded['junit_sha256']):
            raise ValueError('saved mutation evidence digest changed')
        outcome = json.loads(outcome_raw)
        network = json.loads(read(directory / 'network.json'))
        if (recorded['returncode'] != returncode or outcome['returncode'] != returncode
                or outcome.get('cleanup_verified') is not True
                or outcome.get('forced_cleanup') is not False
                or outcome.get('observed_surviving_pids') != []
                or (outcome.get('worker') or {}).get('source_origin_checks_passed') is not True
                or network.get('network_bind_denied') is not True):
            raise ValueError('invalid source/network/cleanup witness for ' + phase)
        cases = list(ET.fromstring(xml_raw).iter('testcase'))
        counts = {'tests': len(cases),
            'failures': sum(item.find('failure') is not None for item in cases),
            'errors': sum(item.find('error') is not None for item in cases),
            'skipped': sum(item.find('skipped') is not None for item in cases)}
        if (not cases or counts['errors'] or counts['skipped'] == counts['tests']
                or any(recorded[key] != number for key, number in counts.items())
                or (phase == 'baseline' and counts['failures'])
                or (phase == 'mutant' and not counts['failures'])):
            raise ValueError('setup, empty selection or wrong counts cannot prove a kill')
        for name in ('origins-before.json', 'origins-after.json', 'subprocess-origins.json'):
            read(directory / name)
        witnesses[phase] = {**counts, 'outcome_sha256': sha(outcome_raw), 'junit_sha256': sha(xml_raw)}
    return {'case': value['case'], 'status': 'killed', 'result': str(path),
        'result_sha256': sha(raw), 'mutant_commit': value['mutant_commit'], 'witnesses': witnesses}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', required=True)
    parser.add_argument('--python', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--plan', action='store_true', help='read-only default')
    mode.add_argument('--run', action='store_true')
    parser.add_argument('--plan-out', type=Path, help='optional new saved plan in round-4 scratch')
    parser.add_argument('--canary', type=Path, help='completed matching MA result.json; required for --run')
    args = parser.parse_args()
    if not re.fullmatch(r'[0-9a-f]{40}', args.base):
        parser.error('--base must be the exact full local reviewed commit')
    args.python = args.python.absolute()
    if not args.python.is_file() or not (args.python.parent.parent / 'pyvenv.cfg').is_file():
        parser.error('--python must be an existing explicit dependency-venv interpreter')
    out = scratch_path(args.out)
    outside_checkout(out)
    if out.exists() or not out.parent.is_dir():
        parser.error('--out must be new and its parent must already exist')
    if args.run and (args.canary is None or args.plan_out is not None):
        parser.error('--run requires --canary and does not use --plan-out')
    if args.run and not (sys.flags.no_site and sys.flags.safe_path and sys.dont_write_bytecode):
        parser.error('invoke --run with Python -S -P -B')
    planned = plans(args)  # All fifteen edits must resolve before any trial begins.
    plan = {'base': args.base, 'out': str(out), 'scratch_root': str(SCRATCH),
        'quiet_window_lock': str(LOCK), 'coordinator_sha256': sha(Path(__file__).read_bytes()),
        'plans': planned, 'remaining_cases': list(CASES[1:]),
        'supervision': 'Each existing runner owns 3600s and cleanup; coordinator has no kill timeout.'}
    if not args.run:
        if args.plan_out is not None:
            save(args.plan_out, plan)
        print(json.dumps(plan, indent=2, sort_keys=True))
        return 0
    committed = subprocess.run(['/usr/bin/git', '--no-replace-objects', 'show', args.base + ':' + SELF],
        cwd=ROOT, env=environment(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True).stdout
    if committed != Path(__file__).read_bytes():
        raise ValueError('commit this exact coordinator with the campaign baseline first')
    canary_path = scratch_path(args.canary)
    canary = checked_result(canary_path, planned['MA'])
    quiet()
    out.mkdir(mode=0o700)
    save(out / 'plans.json', plan)
    summary = {'base': args.base, 'canary': canary, 'completed': [], 'status': 'running'}
    requested = []
    previous = {number: signal.getsignal(number) for number in (signal.SIGINT, signal.SIGTERM)}

    def stop_after_current(number, frame):
        requested.append(number)

    for number in previous:
        signal.signal(number, stop_after_current)
    try:
        for index, case in enumerate(CASES[1:], 1):
            if requested:
                summary.update(status='interrupted_between_cases', signals=requested)
                break
            quiet()
            case_command = command(args, case) + ['--run', '--python', str(args.python),
                '--out', str(out / case), '--canary', str(canary_path)]
            print('Starting ' + case, flush=True)
            with (out / (case + '.console.log')).open('xb') as console:
                # No control timeout and no child signals: keep the established
                # test runner alive until it has performed its own cleanup.
                with subprocess.Popen(case_command, cwd=ROOT, env=environment(),
                        stdout=console, stderr=subprocess.STDOUT, start_new_session=True) as child:
                    returncode = child.wait()
            if returncode != 0:
                raise RuntimeError(case + ' helper failed; inspect its retained console and result')
            checked = checked_result(out / case / 'result.json', planned[case])
            checked['console_sha256'] = sha(read(out / (case + '.console.log')))
            summary['completed'].append(checked)
            save(out / f'progress-{index:02d}.json', summary)
            print(case + ' killed; witnesses verified', flush=True)
        else:
            summary['status'] = 'complete'
    except Exception as exc:
        summary.update(status='stopped', reason=type(exc).__name__ + ': ' + str(exc))
    finally:
        for number, handler in previous.items():
            signal.signal(number, handler)
        save(out / 'summary.json', summary)
    print(json.dumps({'status': summary['status'], 'completed': len(summary['completed']),
        'summary': str(out / 'summary.json')}, sort_keys=True), flush=True)
    return 0 if summary['status'] == 'complete' else 1


if __name__ == '__main__':
    raise SystemExit(main())
