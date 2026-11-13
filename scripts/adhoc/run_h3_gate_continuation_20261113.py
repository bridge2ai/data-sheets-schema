#!/usr/bin/env python3
"""Contingent fresh gate job over the fixed final-format-02 cohort, 2026-11-13.

Inputs: frozen G code, the existing cohort interpreter and complete original
expanded report. Outputs: fresh continuation lifecycle evidence and a fresh
28-case demonstration. No source writes, cache, case reuse or native execution.
Use the dependency Python with -S -P -B. --smoke checks only origins, network
denial and cleanup; it never invokes the driver and may run beside the builder.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import stat
import subprocess
import sys
import time

N = Path(__file__).resolve().parents[2]
E = N.parent
G = E / 'codex-native-pin-comparison-20261113'
EXPECTED_HEAD = 'f98435a0dac3591a2680c595fb7283101e644965'
S = E / 'scratch-h3-gate-refinements-20261113'
COHORT = S / 'tests/final-format-02'
REPORT = COHORT / 'cases/test_final_format_registration0/expanded-project-report.json'
LOCK = E / 'plans/native_quiet_window.lock'
DRIVER = 'scripts/adhoc/run_h3_refinement_demonstration_20261113.py'
RUNNER = 'scripts/adhoc/run_h3_refinement_tests_20261113.py'
ORIGINS = 'tests/utils/native_test_environment.py'
SOURCES = (RUNNER, DRIVER, ORIGINS,
    'scripts/adhoc/run_h3_gate_demonstration_20261113.py',
    'scripts/adhoc/h3_refinement_cases_20261113.json',
    'scripts/adhoc/h3_refinement_mutations_20261113.py',
    'scripts/adhoc/h3_source_commit_control_20261113.py',
    *('scripts/' + name for name in ('native_registration_pin_gate.py',
      'native_registration_validation_worker.py', 'native_registration_fields_v1.json',
      'native_registration_field_gate.py', 'native_registration_documents.py')))


def physical(path):
    path = Path(path)
    if not path.is_absolute() or '..' in path.parts or path.resolve(strict=True) != path:
        raise ValueError('continuation requires physical absolute paths')
    return path


def read(path):
    path = physical(path)
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW), 'rb') as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size > 256_000_000:
            raise ValueError('continuation input must be a bounded regular file')
        raw = stream.read(256_000_001)
        after = os.fstat(stream.fileno())
    fields = ('st_dev', 'st_ino', 'st_mode', 'st_nlink', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
    signature = lambda info: tuple(getattr(info, name) for name in fields)
    if signature(before) != signature(after) or signature(after) != signature(path.lstat()) or len(raw) != before.st_size:
        raise ValueError('continuation input changed while reading')
    return raw


def pin(path):
    raw = read(path)
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def checked(item):
    if type(item) is not dict or set(item) != {'path', 'bytes', 'sha256'}:
        raise ValueError('continuation requires an exact file pin')
    raw = read(item['path'])
    if len(raw) != item['bytes'] or hashlib.sha256(raw).hexdigest() != item['sha256']:
        raise ValueError('continuation input differs from its original bytes')
    return raw


def save(path, value):
    raw = json.dumps(value, sort_keys=True, indent=2, allow_nan=False).encode() + b'\n'
    with Path(path).open('xb') as stream:
        stream.write(raw)
    Path(path).chmod(0o444)
    return pin(path)


def git(*arguments):
    environment = {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}
    environment.update(GIT_NO_LAZY_FETCH='1', GIT_NO_REPLACE_OBJECTS='1', GIT_OPTIONAL_LOCKS='0',
        GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_SYSTEM='/dev/null', GIT_CONFIG_GLOBAL='/dev/null', GIT_TERMINAL_PROMPT='0')
    return subprocess.check_output(['/Library/Developer/CommandLineTools/usr/bin/git',
        '--no-replace-objects', '-c', 'core.hooksPath=/dev/null', '-c', 'core.fsmonitor=false',
        '-c', 'protocol.allow=never', *arguments], cwd=G, env=environment, timeout=30)


def frozen_sources():
    if git('rev-parse', '--verify', 'HEAD^{commit}').decode().strip() != EXPECTED_HEAD:
        raise ValueError('frozen G HEAD differs; continuation refused')
    captures = {}
    for relative in SOURCES:
        expected = git('show', EXPECTED_HEAD + ':' + relative)
        actual = read(G / relative)
        if actual != expected:
            raise ValueError('frozen G source differs: ' + relative)
        captures[relative] = {'path': str(G / relative), 'bytes': len(actual),
                              'sha256': hashlib.sha256(actual).hexdigest()}
    return captures


def source_module(declaration, name):
    raw = checked(declaration)
    namespace = {'__file__': declaration['path'], '__name__': name}
    exec(compile(raw, declaration['path'], 'exec'), namespace)
    return namespace


def fresh(path, parent):
    path, parent = Path(path), Path(parent)
    if (path.parent != parent or not re.fullmatch('[A-Za-z0-9][A-Za-z0-9_-]*', path.name)
            or path.exists() or path.is_symlink()):
        raise ValueError('continuation output must be a fresh direct owned child')
    physical(parent.parent)
    if parent.exists() or parent.is_symlink():
        physical(parent)
    return path


def cohort_inputs(*, smoke):
    physical(COHORT)
    boot_pin = pin(COHORT / 'bootstrap.json')
    boot = json.loads(checked(boot_pin))
    python = COHORT / 'venv/bin/python'
    if boot['test_python'] != str(python) or not python.is_file():
        raise ValueError('saved cohort interpreter differs from its original identity')
    underlying = pin(python.resolve(strict=True))
    if underlying['sha256'] != boot['underlying_python_sha256']:
        raise ValueError('saved cohort interpreter bytes changed')
    originals = [boot_pin, underlying]
    for name, digest in boot['files'].items():
        observed = pin(Path(name))
        if observed['sha256'] != digest:
            raise ValueError('saved cohort bootstrap changed')
        originals.append(observed)
    for name, expected in boot['controlled_distribution']['files'].items():
        observed = pin(Path(name))
        if any(observed[key] != expected[key] for key in ('bytes', 'sha256')):
            raise ValueError('controlled installed dependency was not restored')
        originals.append(observed)
    result = {'python': str(python), 'dependency_site': str(physical(boot['dependency_site'])),
              'originals': originals, 'report': None, 'original_outcome': None, 'git_dir': None}
    if smoke:
        return result
    # A live producer has no final outcome. Do not overlap it or its own matrix.
    original_outcome = pin(COHORT / 'outcome.json')
    outcome = json.loads(checked(original_outcome))
    if type(outcome.get('worker_returncode')) is not int or outcome.get('observed_surviving_pids'):
        raise ValueError('original cohort has not completed without observed survivors')
    report_pin = pin(REPORT)
    report = json.loads(checked(report_pin))
    required = {'reference', 'later', 'AI_READI', 'CM4AI', 'VOICE', 'VOICE_PEDIATRIC', 'registered', 'expired'}
    if set(report['packets']) != required:
        raise ValueError('continuation requires all original packets')
    for row in report['packets'].values():
        if (row['status'] != 'SYNTHETIC-registration-verified'
                or not Path(row['registration']['path']).is_relative_to(COHORT)
                or any(row[key] != 0 for key in ('native_executions', 'model_calls', 'probes_executed', 'captures', 'reservations'))):
            raise ValueError('continuation packet lacks its original synthetic builder proof')
        originals.extend((row['registration'], row['byte_inventory']))
        for item in json.loads(checked(row['byte_inventory'])):
            original = {key: item[key] for key in ('path', 'bytes', 'sha256')}
            if checked(original) != read(item['saved_object']):
                raise ValueError('retained original packet object changed')
            originals.append(original)
    control = report['source_commit_controls']
    control_base = S / 'source-commit/final-format-02'
    if control['root'] != str(control_base / 'tree') or control['git_dir'] != str(control_base / 'git-metadata'):
        raise ValueError('private source metadata is outside the fixed cohort')
    physical(control['git_dir'])
    originals.extend((report_pin, original_outcome, control['manifest'], control['export'],
                      control['reference'], control['candidate']))
    for item in originals:
        checked(item)
    result.update(report=report_pin, original_outcome=original_outcome, git_dir=control['git_dir'])
    return result


def original_processes_absent(psutil, declaration):
    if declaration is None:
        return {'not_checked': 'smoke only; original builder may remain active'}
    outcome = json.loads(checked(declaration))
    for pid, created in outcome.get('observed_processes', []):
        try:
            process = psutil.Process(pid)
            if process.create_time() == created and process.is_running() and process.status() != psutil.STATUS_ZOMBIE:
                raise ValueError('an observed original-cohort process is still alive')
        except psutil.NoSuchProcess:
            pass
    return {'observed_processes_absent': True,
            'original_cleanup_verified': outcome.get('cleanup_verified'),
            'scope': 'saved PID/creation-time observations; no proof about never-observed orphans'}


def sandbox(lifecycle, job, output, git_dir):
    # Preserve all original network/native denials, then narrow the write set.
    allowed = [job, output] + ([] if git_dir is None else [Path(git_dir)])
    return lifecycle['sandbox_profile']() + (
        '(deny file-write* (require-all\n'
        + ''.join('  (require-not (subpath ' + json.dumps(str(path)) + '))\n' for path in allowed)
        + '  (require-not (literal "/dev/null"))\n'
          '  (require-not (literal "/dev/tty"))))\n'
        + '(deny file-write* (subpath ' + json.dumps(str(G)) + '))\n'
        + '(deny file-write* (subpath ' + json.dumps(str(COHORT)) + '))\n')


def supervise(child, owned, quiet, *, seconds, clock=time.monotonic, sleep=time.sleep):
    started, previous, active = clock(), clock(), 0.0
    interrupted, forced = None, False
    try:
        while child.poll() is None:
            tick = clock()
            if not quiet.paused:
                active += tick - previous
            previous = tick
            owned.observe()
            if active >= seconds:
                interrupted = 'active_deadline'
                break
            quiet.update(owned)
            sleep(0.25)
    except BaseException as error:
        interrupted = type(error).__name__
    finally:
        owned.observe()
        if quiet.paused:
            owned.signal(signal.SIGCONT)
        if owned.live():
            forced = True
            owned.signal(signal.SIGTERM)
            until = clock() + 5
            while owned.live() and clock() < until:
                sleep(0.1)
            if owned.live():
                owned.signal(signal.SIGKILL)
        try:
            child.wait(timeout=5)
        except subprocess.TimeoutExpired:
            interrupted = interrupted or 'cleanup_timeout'
    return {'active_seconds': active, 'wall_seconds': clock() - started,
            'interrupted': interrupted, 'forced_cleanup': forced,
            'observed_surviving_pids': [process.pid for process in owned.live()],
            'observation_errors': list(owned.errors), 'observed_processes': sorted(owned.known)}


def child(config):
    job = physical(config['job'])
    if (job.parent != S / 'continuations' or not sys.flags.isolated or not sys.flags.no_site
            or not sys.dont_write_bytecode or sys.executable != str(COHORT / 'venv/bin/python')):
        raise ValueError('continuation child requires the exact existing cohort and -I -S -B')
    if frozen_sources() != config['sources']:
        raise ValueError('continuation sources changed before child entry')
    for item in config['inputs']['originals']:
        checked(item)
    prefix = COHORT / 'venv'
    sites = list((prefix / 'lib').glob('python*/site-packages'))
    if len(sites) != 1:
        raise ValueError('cohort installed root is ambiguous')
    roots = [str(G / 'src'), str(G)]
    if (G / 'fairscape_models/fairscape_models').is_dir():
        roots.append(str(G / 'fairscape_models'))
    sys.path[:] = list(dict.fromkeys([*roots, *[value for value in sys.path if value and Path(value).is_absolute()],
        str(sites[0]), config['inputs']['dependency_site']]))
    sys.prefix = sys.exec_prefix = str(prefix)
    lifecycle = source_module(config['sources'][RUNNER], 'fixed_continuation_lifecycle')
    witness = source_module(config['sources'][ORIGINS], 'fixed_continuation_origin_witness')['origin_witness']
    save(job / 'network.json', lifecycle['network_witness']())
    save(job / 'origins-before.json', witness(G))
    code = 0
    if not config['smoke']:
        # The exact existing driver runs every case afresh; no prior result is
        # accepted as a substitute for a new CLI comparison.
        driver = source_module(config['sources'][DRIVER], 'fixed_continuation_driver')
        sys.argv = [str(G / DRIVER), '--cohort', str(COHORT), '--report', str(REPORT),
                    '--output', config['output'], '--worker-timeout-seconds', '3600']
        code = int(driver['main']())
        result_path = Path(config['output']) / 'demonstration-results.json'
        result = json.loads(read(result_path))
        if code == 0 and (result['status'] != 'all_requested_demonstrations_passed' or len(result['cases']) != 28):
            raise ValueError('driver success lacks all freshly persisted comparisons')
    for item in config['inputs']['originals']:
        checked(item)
    if frozen_sources() != config['sources']:
        raise ValueError('continuation sources changed during child execution')
    save(job / 'origins-after.json', witness(G))
    save(job / 'worker-outcome.json', {'returncode': code, 'source_origin_checks_passed': True,
        'driver_launched': not config['smoke'], 'mode': 'smoke' if config['smoke'] else 'fresh_full_matrix'})
    return code


def parent(args):
    if not (sys.flags.no_site and sys.flags.safe_path and sys.dont_write_bytecode):
        raise ValueError('invoke continuation parent with dependency Python -S -P -B')
    if not 1 <= args.timeout_seconds <= 14400:
        raise ValueError('continuation active deadline must be 1..14400 seconds')
    job = fresh(args.job, S / 'continuations')
    output = fresh(args.output, S / 'demonstrations')
    if LOCK.exists():
        raise ValueError('quiet window active; continuation was not launched')
    sources = frozen_sources()
    inputs = cohort_inputs(smoke=args.smoke)
    lifecycle = source_module(sources[RUNNER], 'fixed_continuation_lifecycle')
    dependency = lifecycle['dependency_site']()
    sys.path.append(str(dependency))
    import psutil
    original = original_processes_absent(psutil, inputs['original_outcome'])
    job.parent.mkdir(exist_ok=True)
    output.parent.mkdir(exist_ok=True)
    job.mkdir(mode=0o700)
    (job / 'home').mkdir(); (job / 'tmp').mkdir()
    config = {'job': str(job), 'output': str(output), 'smoke': args.smoke,
              'sources': sources, 'inputs': inputs, 'expected_head': EXPECTED_HEAD}
    config_pin = save(job / 'inputs.json', config)
    original_matrix = S / 'demonstrations/final-format-02-full/demonstration-results.json'
    if not args.smoke and original_matrix.is_file():
        previous = json.loads(read(original_matrix))
        if previous.get('status') == 'all_requested_demonstrations_passed':
            save(job / 'outcome.json', {'status': 'unused_original_matrix_completed', 'launched': False,
                                       'original_result': pin(original_matrix)})
            return 0
    profile = job / 'network-denied.sb'
    with profile.open('xb') as stream:
        stream.write(sandbox(lifecycle, job, output, inputs['git_dir']).encode())
    profile.chmod(0o444)
    raw = read(Path(__file__).resolve())
    program = ('exec(compile(' + repr(raw) + ', ' + repr(str(Path(__file__).resolve()))
        + ", 'exec'), {'__name__': '__main__', '__file__': " + repr(str(Path(__file__).resolve())) + '})\n').encode()
    with (job / 'bootstrap.py').open('xb') as stream:
        stream.write(program)
    (job / 'bootstrap.py').chmod(0o444)
    command = ['/usr/bin/sandbox-exec', '-f', str(profile), inputs['python'], '-I', '-S', '-B', '-',
               '--child-config', config_pin['path'], '--config-sha256', config_pin['sha256']]
    environment = lifecycle['clean_environment'](job, Path(inputs['python']).parent)
    save(job / 'plan.json', {'command': command, 'cwd': str(G), 'environment': environment,
        'inputs': config_pin, 'bootstrap': pin(job / 'bootstrap.py'), 'wrapper': pin(Path(__file__).resolve()),
        'sandbox': pin(profile), 'original_process_check': original,
        'active_deadline_seconds': args.timeout_seconds, 'prior_case_results_reused': False})
    process = owned = None
    with (job / 'driver.log').open('xb') as log:
        try:
            process = subprocess.Popen(command, cwd=G, env=environment, stdin=subprocess.PIPE,
                stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            owned = lifecycle['OwnedProcesses'](psutil, process.pid)
            process.stdin.write(program)
            process.stdin.close()
            result = supervise(process, owned, lifecycle['QuietWindow'](LOCK), seconds=args.timeout_seconds)
        except BaseException:
            if owned is not None:
                owned.signal(signal.SIGTERM)
            elif process is not None and process.poll() is None:
                process.terminate()
            if process is not None:
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    if owned is not None:
                        owned.signal(signal.SIGKILL)
                    else:
                        process.kill()
                    process.wait(timeout=5)
            raise
    worker_path = job / 'worker-outcome.json'
    worker = json.loads(read(worker_path)) if worker_path.is_file() else None
    clean = (process.returncode is not None and process.returncode >= 0 and worker is not None
             and not result['interrupted'] and not result['forced_cleanup']
             and not result['observation_errors'] and not result['observed_surviving_pids'])
    code = 124 if result['interrupted'] == 'active_deadline' else (process.returncode if clean else 125)
    result.update(returncode=code, worker_returncode=process.returncode, worker=worker,
        cleanup_verified=clean, contingent=True, prior_case_results_reused=False,
        cleanup_scope='observed PID/creation-time descendants; no proof about never-observed orphans')
    save(job / 'outcome.json', result)
    print(json.dumps(result, sort_keys=True))
    return int(code)


def main(argv=None):
    # H3-RF17: this unexecuted draft inherited a sandbox around the gate parent.
    # Preserve it for review, but refuse until the closed staged launcher is
    # implemented and independently checked. A nested sandbox is not supported.
    raise RuntimeError('H3-RF17: continuation draft disabled pending staged launcher repair')
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--job', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--timeout-seconds', type=int, default=14400)
    parser.add_argument('--smoke', action='store_true')
    parser.add_argument('--child-config', type=Path, help=argparse.SUPPRESS)
    parser.add_argument('--config-sha256', help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.child_config is not None:
        if args.child_config.parent.parent != S / 'continuations' or args.child_config.name != 'inputs.json':
            parser.error('fixed child config must belong to its continuation job')
        raw = read(args.child_config)
        if hashlib.sha256(raw).hexdigest() != args.config_sha256:
            parser.error('continuation child config differs from its captured bytes')
        return child(json.loads(raw))
    if args.job is None or args.output is None:
        parser.error('job and output are required; no caller command is accepted')
    return parent(args)


if __name__ == '__main__':
    raise SystemExit(main())
