#!/usr/bin/env python3
"""One <=30s WP1 quiet-lock fixture, 2026-11-10 (5755/5757/5760).

Inputs: frozen helpers, existing physical dependency venv, one fresh scratch
directory. Outputs: synthetic refusals, actual five-process/FD evidence and
bounded cleanup. Only fixture locks below that directory are used. No live
quiet lock, composition, sampler, native runtime, provider or test environment
is created/used. A pass is not the real runner's same-path canary or timing gate.
"""
import time
STARTED = time.monotonic()

import argparse
import builtins
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import select
import signal
import stat
import subprocess
import sys
import traceback

ROOT = Path(__file__).resolve().parents[2]
SELF = Path(__file__).resolve()
PRIMARY = ROOT.parent.parent / 'data-sheets-schema'
PYTHON = PRIMARY / '.venv/bin/python'
SCRATCH = ROOT.parent / 'scratch-native-u1u3'
FILES = (
    'scripts/adhoc/native_wp1_quiet_fixture_20261110.py',
    'scripts/adhoc/native_wp1_quiet_20261110.py',
    'scripts/adhoc/native_wp1_qualification_20261110.py',
    'scripts/adhoc/native_wp1_validation_20261110.py',
    'scripts/adhoc/run_native_wp1_20261110.py',
    'scripts/adhoc/native_wp1_synthetic_smoke_20261110.py',
)
ROLE_NAMES = ('outer', 'supervised', 'driver', 'worker', 'child-check')
ROLES = {role: SELF for role in ROLE_NAMES}
CHILD = None
HANDOFF = None
TERMINAL_FD = None
END = None
WORK_END = None


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def write(path, value):
    raw = (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()
    temporary = path.with_name('.' + path.name + '.pending-' + str(os.getpid()))
    with temporary.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    # Publish complete bytes exclusively. Readers never see a partially written
    # ready/result path, and an existing artifact is never overwritten.
    os.link(temporary, path)
    temporary.unlink()
    if path.read_bytes() != raw:
        raise RuntimeError('fixture artifact did not persist exactly')
    return {'path': str(path), 'bytes': len(raw), 'sha256': digest(raw)}


def pins():
    result = {}
    for name in FILES:
        path = ROOT / name
        if path.resolve(strict=True) != path:
            raise ValueError('fixture source is aliased')
        raw = path.read_bytes()
        result[name] = {'bytes': len(raw), 'sha256': digest(raw)}
    return result


def git(*arguments):
    return subprocess.check_output(['/usr/bin/git', '--no-replace-objects',
        '-c', 'core.hooksPath=/dev/null', *arguments], cwd=ROOT,
        timeout=max(0.001, min(2, END - time.monotonic())), env={
        'PATH': '/usr/bin:/bin', 'GIT_NO_LAZY_FETCH': '1', 'GIT_ALLOW_PROTOCOL': '',
        'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_CONFIG_SYSTEM': '/dev/null',
        'GIT_OPTIONAL_LOCKS': '0'})


def dependencies():
    # Keep the venv spelling. Resolving the executable first loses this prefix.
    executable = Path(sys.executable).absolute()
    prefix = executable.parent.parent
    site = prefix / 'lib/python3.13/site-packages'
    if (executable != PYTHON or not (prefix / 'pyvenv.cfg').is_file()
            or not site.is_dir() or site.resolve(strict=True) != site
            or sys.implementation.name != 'cpython' or sys.version_info[:2] != (3, 13)
            or not sys.flags.isolated or not sys.flags.no_site or not sys.dont_write_bytecode):
        raise ValueError('fixture requires physical installed venv spelling and Python 3.13 -I -S -B')
    sys.path[:0] = [str(ROOT), str(site)]
    import psutil
    if not Path(psutil.__file__).resolve().is_relative_to(site):
        raise ValueError('fixture imported psutil from another dependency directory')
    return psutil, site


def environment(root, source, extra=None):
    value = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'LANG': 'en_US.UTF-8',
             'TMPDIR': str(root / 'tmp'), 'PYTHONDONTWRITEBYTECODE': '1',
             'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1', 'PYTEST_ADDOPTS': '',
             'WP1_FIXTURE_ROOT': str(root), 'WP1_FIXTURE_SOURCE': source,
             'WP1_FIXTURE_END': repr(END), 'WP1_FIXTURE_WORK_END': repr(WORK_END)}
    if extra:
        value.update(extra)
    return value


def terminal(number, frame):
    # Unknown interruption never removes any lock. Each child has the same
    # independent absolute work deadline; signal only still-owned identities.
    if HANDOFF is not None:
        try:
            HANDOFF.kill_detached()
        except BaseException:
            pass
    if CHILD is not None and CHILD.poll() is None:
        try:
            os.killpg(CHILD.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    if TERMINAL_FD is not None:
        os.write(TERMINAL_FD, b'Interrupted/deadline; cleanup uncertified and fixture locks retained.\n')
    os._exit(124 if number == signal.SIGALRM else 128 + number)


def arm_deadline(deadline, *, outer=False):
    remaining = deadline - time.monotonic()
    if not 0 < remaining <= 30:
        raise ValueError('fixture deadline is invalid, expired or renewed')
    signal.signal(signal.SIGALRM, terminal if outer else lambda number, frame: os._exit(124))
    signal.setitimer(signal.ITIMER_REAL, remaining)
    if outer:
        signal.signal(signal.SIGTERM, terminal)
        signal.signal(signal.SIGINT, terminal)


def bootstrap(args):
    global END, WORK_END
    END, WORK_END = STARTED + 30, STARTED + 25
    arm_deadline(END, outer=True)
    if (args.out is None or args.out.parent != SCRATCH
            or SCRATCH.resolve(strict=True) != SCRATCH
            or not re.fullmatch('wp1-quiet-fixture-[A-Za-z0-9_-]+', args.out.name)
            or os.path.lexists(args.out)):
        raise ValueError('fresh physical fixture output required')
    sys.pycache_prefix = str(args.out / 'unused-pycache')
    dependencies()
    if git('rev-parse', 'HEAD').decode().strip() != args.source:
        raise ValueError('fixture requires its frozen current source HEAD')
    if git('status', '--porcelain=v1', '--untracked-files=all').strip():
        raise ValueError('fixture requires a clean frozen worktree')
    source_pins = pins()
    for name, identity in source_pins.items():
        if digest(git('show', args.source + ':' + name)) != identity['sha256']:
            raise ValueError('fixture helper differs from frozen source: ' + name)
    from scripts.adhoc.native_wp1_synthetic_smoke_20261110 import runtime_binaries
    binaries = runtime_binaries()
    args.out.mkdir()
    (args.out / 'tmp').mkdir()
    policy = '\n'.join((
        '(version 1)', '(allow default)', '(deny network*)',
        '(deny process-exec (require-all (require-not (literal ' + json.dumps(str(PYTHON)) + '))',
        ' (require-not (literal ' + json.dumps(str(PYTHON.resolve(strict=True))) + '))))',
        '(deny file-write* (require-all (require-not (subpath ' + json.dumps(str(args.out)) + '))',
        ' (require-not (literal "/dev/null"))))', ''))
    with (args.out / 'sandbox.sb').open('x') as stream:
        stream.write(policy)
    write(args.out / 'manifest.json', {'source_commit': args.source,
        'source_files': source_pins, 'runtime_binaries': binaries,
        'started_monotonic': STARTED, 'end_monotonic': END, 'work_end_monotonic': WORK_END,
        'parent_limit_seconds': 30, 'campaign_limit_seconds': 25,
        'interpreter_spelling': str(PYTHON), 'sandbox_sha256': digest(policy.encode()),
        'scope': 'Synthetic lease/FD/topology fixture only; no real qualification, composition, native runtime or timing arm.'})
    # Same PID becomes the sandboxed outer. The absolute deadlines include
    # bootstrap; no new budget or second fixture campaign is granted by exec.
    command = ['/usr/bin/sandbox-exec', '-f', str(args.out / 'sandbox.sb'), str(PYTHON),
               '-I', '-S', '-B', str(SELF), '--outer', '--source', args.source, '--out', str(args.out)]
    os.execve(command[0], command, environment(args.out, args.source))


def context(args):
    global END, WORK_END
    root = Path(os.environ['WP1_FIXTURE_ROOT'])
    if (root.parent != SCRATCH or root.resolve(strict=True) != root
            or not re.fullmatch('wp1-quiet-fixture-[A-Za-z0-9_-]+', root.name)):
        raise ValueError('fixture root hint is outside the assigned physical directory')
    END, WORK_END = float(os.environ['WP1_FIXTURE_END']), float(os.environ['WP1_FIXTURE_WORK_END'])
    arm_deadline(END if args.outer else WORK_END, outer=args.outer)
    sys.pycache_prefix = str(root / 'unused-pycache')  # -B: never create this directory.
    psutil, site = dependencies()
    raw = (root / 'manifest.json').read_bytes()
    manifest = json.loads(raw)
    if (manifest['source_commit'] != args.source or args.source != os.environ['WP1_FIXTURE_SOURCE']
            or manifest['end_monotonic'] != END or manifest['work_end_monotonic'] != WORK_END
            or END - manifest['started_monotonic'] != 30
            or WORK_END - manifest['started_monotonic'] != 25
            or pins() != manifest['source_files']):
        raise ValueError('fixture source or absolute budget differs')
    from scripts.adhoc import native_wp1_quiet_20261110 as quiet
    from scripts.adhoc import native_wp1_validation_20261110 as validator
    return root, manifest, digest(raw), psutil, quiet, validator


class LiteralPath(os.PathLike):
    def __init__(self, value):
        self.value = str(value)
    def __fspath__(self):
        return self.value


def refused(exception, action):
    try:
        action()
    except exception as error:
        return type(error).__name__ + ': ' + str(error)
    raise AssertionError('fixture expected a refusal')


def acquisition(quiet, psutil, root, name, manifest_sha, source):
    output = root / name
    output.mkdir()
    return quiet.acquire(root / (name + '.lock'), output,
        manifest_sha256=manifest_sha, source_commit=source,
        qualification_seconds=1, arm_seconds=20, role_scripts=ROLES, psutil_module=psutil)


def reader_checks(reader, quiet, validator, output, label):
    original_import = builtins.__import__
    original_lexists = os.path.lexists
    view = reader.lock_view()
    proxy = reader.os_proxy()
    assert os.path.lexists(os.fspath(view))
    assert isinstance(view, os.PathLike) and view.exists() is False and view.lexists() is False
    assert proxy.path.lexists(LiteralPath(view)) is False
    toy = output / (label + '-import-guard.py')
    with toy.open('x') as stream:
        stream.write('import os\nLOCK = ' + repr(os.fspath(view))
                     + '\nif os.path.lexists(LOCK):\n    raise RuntimeError("fixture lock refused")\n')
    module = validator.load_with_lease_os('wp1_fixture_' + label.replace('-', '_'), toy, reader)
    try:
        assert module.os.path.lexists(LiteralPath(view)) is False
        assert module.__dict__['__builtins__'] is vars(builtins)
        module.LOCK = view  # C/A entry and pause expressions use this exact view.
        assert module.LOCK.exists() is False
    finally:
        module.os, module.LOCK = os, Path(os.fspath(view))
    assert module.os is os and module.LOCK.exists()
    assert builtins.__import__ is original_import and os.path.lexists is original_lexists
    busy = refused(quiet.LeaseBusy, lambda: quiet.refuse_existing(LiteralPath(view)))
    return {'pathlike': True, 'owned_hidden_only_by_adapter': True,
            'canary_still_refuses_owned': busy, 'module_adapters_restored': True,
            'global_os_and_builtins_unchanged': True,
            'toy_source_sha256': digest(toy.read_bytes())}


def entry_identity(path):
    info = path.lstat()
    result = {'device': info.st_dev, 'inode': info.st_ino, 'mode': info.st_mode}
    if stat.S_ISLNK(info.st_mode):
        result['link_target'] = os.readlink(path)
    elif stat.S_ISREG(info.st_mode):
        raw = path.read_bytes()
        result.update(bytes=len(raw), sha256=digest(raw))
    elif stat.S_ISFIFO(info.st_mode):
        result['kind'] = 'fifo'  # Identity only: never open a fixture FIFO.
    else:
        raise AssertionError('fixture expected a regular file, symlink or FIFO')
    return result


def release_boundary_cases(base, source, manifest_sha, psutil, quiet):
    """Inject at capture after validation; do not weaken the release checks."""
    results = []
    for kind in ('regular', 'symlink', 'fifo', 'restore-conflict'):
        name = 'release-boundary-' + kind
        owner = acquisition(quiet, psutil, base, name, manifest_sha, source)
        lock = base / (name + '.lock')
        owned_before = entry_identity(lock)
        owned_archive = base / (name + '.original-owned-lock.json')
        foreign = base / (name + '.foreign')
        target = None
        if kind == 'symlink':
            target = base / (name + '.target')
            target.write_bytes(b'foreign symlink target must survive\n')
            target_before = entry_identity(target)
            foreign.symlink_to(target)
        elif kind == 'fifo':
            os.mkfifo(foreign, 0o600)
        else:
            foreign.write_bytes(b'foreign lock injected at the atomic capture boundary\n')
        foreign_before = entry_identity(foreign)
        observations = {'successful_validations': 0, 'capture_calls': 0}
        actual_validate, actual_capture = owner.validate, quiet._capture_lock

        def validate():
            value = actual_validate()
            observations['successful_validations'] += 1
            return value

        def inject(source_path, captured_path):
            assert Path(source_path) == lock
            assert observations['successful_validations'] >= 1
            assert observations['capture_calls'] == 0
            assert entry_identity(lock) == owned_before
            observations['capture_calls'] += 1
            # The production prechecks have already succeeded. Preserve the
            # owner object, then replace only this fixture's canonical entry.
            os.rename(lock, owned_archive)
            os.rename(foreign, lock)
            assert entry_identity(lock) == foreign_before
            value = actual_capture(source_path, captured_path)
            assert entry_identity(Path(captured_path)) == foreign_before
            observations['captured_path'] = str(captured_path)
            if kind == 'restore-conflict':
                with lock.open('xb') as stream:
                    stream.write(b'a second foreign owner occupies the canonical path\n')
                observations['new_canonical_identity'] = entry_identity(lock)
            return value

        owner.validate, quiet._capture_lock = validate, inject
        try:
            release = owner.release(cleanup_verified=True)
        finally:
            owner.validate, quiet._capture_lock = actual_validate, actual_capture
        assert observations['capture_calls'] == 1
        assert release['retained'] and not release['released']
        assert release['reason'] and entry_identity(owned_archive) == owned_before
        captured = Path(release['captured_path'])
        quarantine = Path(release['quarantine_path'])
        assert str(captured) == observations['captured_path']
        assert captured.parent == quarantine and quarantine.is_dir()
        assert stat.S_IMODE(quarantine.stat().st_mode) == 0o700
        if kind == 'restore-conflict':
            assert not release['foreign_restored'] and release['canonical_already_occupied']
            assert entry_identity(captured) == foreign_before
            assert entry_identity(lock) == observations['new_canonical_identity']
            assert Path(release['recovery_path']) == captured
        else:
            assert release['foreign_restored'] and not release['canonical_already_occupied']
            assert entry_identity(lock) == foreign_before and not os.path.lexists(captured)
            assert Path(release['recovery_path']) == lock
        if target is not None:
            assert entry_identity(target) == target_before
        results.append({'case': name, 'injection': observations, 'release': release,
            'foreign_before': foreign_before, 'canonical_after': entry_identity(lock),
            'original_owned_lock_preserved': str(owned_archive),
            'original_owned_identity': owned_before,
            'scope': 'Deterministic replacement at the real capture boundary after validation; preserved-object evidence, not uninterrupted canonical-path availability.'})
    return results


def pure_cases(root, source, manifest_sha, psutil, quiet, validator):
    base = root / 'cases'
    base.mkdir()
    result = []
    for name, raw in (('foreign', b'foreign owner\n'), ('stale', b'{"owner":-1,"expired":true}\n')):
        lock = base / (name + '.lock')
        lock.write_bytes(raw)
        before = (lock.stat().st_ino, lock.read_bytes())
        refusal = refused(quiet.LeaseBusy, lambda: quiet.refuse_existing(LiteralPath(lock)))
        refusal2 = refused(quiet.LeaseBusy, lambda: quiet.acquire(lock, base / name,
            manifest_sha256=manifest_sha, source_commit=source, qualification_seconds=1,
            arm_seconds=20, role_scripts=ROLES, psutil_module=psutil))
        assert (lock.stat().st_ino, lock.read_bytes()) == before
        result.append({'case': name, 'canary': refusal, 'acquisition': refusal2, 'unchanged': True})
    target = base / 'symlink-target'
    target.write_bytes(b'preserve target\n')
    symlink = base / 'symlink.lock'
    symlink.symlink_to(target)
    refusal = refused(quiet.LeaseBusy, lambda: quiet.refuse_existing(symlink))
    refusal2 = refused(quiet.LeaseBusy, lambda: quiet.acquire(symlink, base / 'symlink',
        manifest_sha256=manifest_sha, source_commit=source, qualification_seconds=1,
        arm_seconds=20, role_scripts=ROLES, psutil_module=psutil))
    assert symlink.is_symlink() and target.read_bytes() == b'preserve target\n'
    result.append({'case': 'symlink', 'canary': refusal, 'acquisition': refusal2, 'target_unchanged': True})
    normal = acquisition(quiet, psutil, base, 'normal', manifest_sha, source)
    adapter = reader_checks(normal, quiet, validator, base / 'normal', 'normal')
    # A forged descriptor hint cannot replace the inherited readonly capability.
    bad_fd = refused(quiet.LeaseLost, lambda: quiet.read_lease(-1, role='outer',
        expected_lock=base / 'normal.lock', expected_manifest_sha256=manifest_sha,
        expected_source_commit=source, role_scripts=ROLES, psutil_module=psutil))
    owned_before = entry_identity(base / 'normal.lock')
    release = normal.release(cleanup_verified=True)
    assert release['released'] and not os.path.lexists(base / 'normal.lock')
    assert entry_identity(Path(release['captured_path'])) == owned_before
    result.append({'case': 'normal_owned_and_release', 'adapters': adapter,
                   'missing_carrier_refused': bad_fd, 'release': release})
    for name in ('altered', 'replaced', 'lost'):
        owner = acquisition(quiet, psutil, base, name, manifest_sha, source)
        lock = base / (name + '.lock')
        original = lock.read_bytes()
        (base / (name + '.original-lock.json')).write_bytes(original)
        if name == 'altered':
            lock.write_bytes(b'altered fixture lock\n')
        elif name == 'replaced':
            replacement = base / 'replacement-candidate'
            replacement.write_bytes(b'replacement fixture owner\n')
            os.replace(replacement, lock)
        else:
            lock.unlink()
        reason = refused(quiet.LeaseLost, owner.validate)
        assert owner.failure_reason and reason.endswith(owner.failure_reason)
        retained = owner.release(cleanup_verified=True)
        assert retained['retained'] and not retained['released']
        if name == 'lost':
            assert not os.path.lexists(lock)
        else:
            assert lock.read_bytes() in (b'altered fixture lock\n', b'replacement fixture owner\n')
        result.append({'case': name, 'sticky_failure_reason': owner.failure_reason, 'release': retained})
    unknown = acquisition(quiet, psutil, base, 'unknown-cleanup', manifest_sha, source)
    lock = base / 'unknown-cleanup.lock'
    before = lock.read_bytes()
    retained = unknown.release(cleanup_verified=False)
    assert retained['retained'] and lock.read_bytes() == before
    result.append({'case': 'unknown_cleanup_retains', 'release': retained,
        'scope': 'Pure unknown-cleanup/hard-exit policy witness; no external hard termination was injected.'})
    result.extend(release_boundary_cases(base, source, manifest_sha, psutil, quiet))
    return result


def qualification_cases():
    from scripts.adhoc import native_wp1_qualification_20261110 as qualification
    start = datetime(2026, 11, 10, tzinfo=timezone.utc)
    samples = [{'kind': 'sample', 'observer_pid': 2, 'sequence': i + 1,
        'at': (start + timedelta(seconds=i + 1)).isoformat(), 'monotonic': float(i + 1),
        'logical_cpus': 4, 'cpu_percent': 10.0, 'load': [1.0, 0.0, 0.0],
        'processes': [{'pid': 1, 'ppid': 0, 'cpu_percent': 0.0, 'name': 'launchd'},
                      {'pid': 2, 'ppid': 1, 'cpu_percent': 0.0, 'name': 'synthetic observer'}]}
        for i in range(60)]
    idle = qualification.evaluate_samples(samples, owned_roots={2}, elapsed_seconds=60)
    assert idle['idle'] is True
    busy_samples = deepcopy(samples)
    busy_samples[-1]['processes'].append({'pid': 3, 'ppid': 1, 'cpu_percent': 5.0, 'name': 'synthetic competitor'})
    busy = qualification.evaluate_samples(busy_samples, owned_roots={2}, elapsed_seconds=60)
    assert busy['idle'] is False
    insufficient_count = refused(ValueError, lambda: qualification.evaluate_samples(samples[:-1], owned_roots={2}, elapsed_seconds=60))
    insufficient_elapsed = refused(ValueError, lambda: qualification.evaluate_samples(samples, owned_roots={2}, elapsed_seconds=59))
    boundaries = {}
    for name, boundary, exceeding in (('mean', 15.0, 15.01), ('peak', 35.0, 35.01), ('load', 2.0, 2.01)):
        decisions = []
        for value, expected in ((boundary, True), (exceeding, False)):
            rows = deepcopy(samples)
            if name == 'mean':
                for row in rows:
                    row['cpu_percent'] = value
            elif name == 'peak':
                rows[-1]['cpu_percent'] = value
            else:
                rows[-1]['load'][0] = value
            decision = qualification.evaluate_samples(rows, owned_roots={2}, elapsed_seconds=60)
            assert decision['idle'] is expected
            decisions.append(decision)
        boundaries[name] = {'exact_boundary_accepted': decisions[0], 'above_boundary_refused': decisions[1]}
    below_foreign = deepcopy(busy_samples)
    below_foreign[-1]['processes'][-1]['cpu_percent'] = 4.99
    below_foreign_decision = qualification.evaluate_samples(below_foreign, owned_roots={2}, elapsed_seconds=60)
    assert below_foreign_decision['idle'] is True
    assert qualification.SETTLING_SECONDS == 60 and qualification.SAMPLE_COUNT == 60
    return {'synthetic_idle': idle, 'synthetic_busy': busy,
            'insufficient_count_refused': insufficient_count, 'insufficient_elapsed_refused': insufficient_elapsed,
            'threshold_boundaries': boundaries, 'foreign_below_boundary_accepted': below_foreign_decision,
            'inputs_sha256': digest(json.dumps(samples, sort_keys=True).encode()),
            'scope': 'Pure synthetic sample evaluation; no real host observation, settling or qualification occurred.'}


def cpu_diagnostic_cases(validator):
    assert validator.KINDS['cpu-legacy'] == (validator.DIAGNOSTIC, 'legacy', 900)
    assert validator.KINDS['cpu-monitoring'] == (validator.DIAGNOSTIC, 'monitoring', 900)
    assert validator.QUALIFIED_KINDS == frozenset({'legacy', 'monitoring'})
    assert validator.CPU_DIAGNOSTIC_KINDS == frozenset({'cpu-legacy', 'cpu-monitoring'})
    assert validator.NO_LEASE_KINDS == frozenset({'canary', 'cpu-legacy', 'cpu-monitoring', 'capture-recheck'})
    passed_witness = {'qualification_passed': True, 'cleanup_verified': True}
    unverified_classes = {kind: validator.measurement_classification(kind) for kind in validator.KINDS}
    for kind, row in unverified_classes.items():
        assert row['host_qualified'] is False
        assert row['wall_time_freshness_qualified'] is False
        assert row['accepted_quiet_host_timing'] is False
    failed_default_class = validator.measurement_classification(
        'legacy', qualification=passed_witness, certified=False, final_owner=True
    )
    assert failed_default_class['host_qualified'] is False
    assert failed_default_class['wall_time_freshness_qualified'] is False
    assert failed_default_class['accepted_quiet_host_timing'] is False
    intermediate_default_class = validator.measurement_classification(
        'legacy', qualification=passed_witness, certified=True, final_owner=False
    )
    assert intermediate_default_class['host_qualified'] is True
    assert intermediate_default_class['wall_time_freshness_qualified'] is False
    assert intermediate_default_class['accepted_quiet_host_timing'] is False
    final_classes = {
        kind: validator.measurement_classification(
            kind, qualification=passed_witness, certified=True, final_owner=True
        )
        for kind in validator.KINDS
    }
    for kind in ('canary', 'cpu-legacy', 'cpu-monitoring', 'capture-recheck'):
        assert final_classes[kind]['host_qualified'] is False
        assert final_classes[kind]['wall_time_freshness_qualified'] is False
        assert final_classes[kind]['accepted_quiet_host_timing'] is False
    for kind in ('legacy', 'monitoring'):
        assert final_classes[kind]['measurement_class'] == 'qualified_quiet_window'
        assert final_classes[kind]['host_qualified'] is True
        assert final_classes[kind]['wall_time_freshness_qualified'] is True
        assert final_classes[kind]['accepted_quiet_host_timing'] is True
    accepted_sample = {
        'kind': 'legacy', **final_classes['legacy'], 'cleanup_verified': True,
        'returncode': 0, 'qualification': dict(passed_witness),
    }
    assert validator.require_accepted_measurement(accepted_sample) is True
    cpu_refused = {
        kind: refused(ValueError, lambda kind=kind: validator.require_accepted_measurement({
            'kind': kind, **final_classes[kind], 'cleanup_verified': True,
            'returncode': 0, 'qualification': dict(passed_witness),
        }))
        for kind in ('canary', 'cpu-legacy', 'cpu-monitoring', 'capture-recheck')
    }
    failed_default_refused = refused(
        ValueError,
        lambda: validator.require_accepted_measurement({
            'kind': 'legacy', **failed_default_class, 'cleanup_verified': False,
            'returncode': 125, 'qualification': dict(passed_witness),
        }),
    )
    intermediate_default_refused = refused(
        ValueError,
        lambda: validator.require_accepted_measurement({
            'kind': 'legacy', **intermediate_default_class, 'cleanup_verified': True,
            'returncode': 0, 'qualification': dict(passed_witness),
        }),
    )
    missing_witness_refused = refused(
        ValueError,
        lambda: validator.require_accepted_measurement(
            {key: value for key, value in accepted_sample.items() if key != 'qualification'}
        ),
    )
    failed_qual_refused = refused(
        ValueError,
        lambda: validator.require_accepted_measurement(
            dict(accepted_sample, qualification={'qualification_passed': False, 'cleanup_verified': True})
        ),
    )

    def synthetic_arm(kind, arm, thread_cpu_launch):
        return {
            'kind': kind, 'arm': arm, 'node': validator.DIAGNOSTIC,
            **final_classes[kind],
            'manifest_sha256': 'a' * 64, 'source_commit': 'b' * 40,
            'harness': {'interpreter': {'path': '/venv/bin/python', 'sha256': 'c' * 64, 'version': '3.13'}},
            'cleanup_verified': True, 'returncode': 0, 'qualification': None,
            'host_contention': {'qualified': False, 'samples': 3, 'mean_cpu_percent': 42.0,
                                'peak_cpu_percent': 55.0, 'max_one_minute_load_per_cpu': 1.25},
            'diagnostic': {
                'wp1_kind': kind, **final_classes[kind],
                'outcome': 'reached_reservation_without_effect', 'error': 'stopped at mkdir',
                'open_call_rows': 0, 'open_thread_stacks': 0,
                'profile_stability': {'stable': True, 'restored': True},
            },
            'measurement': {
                'mode': 'control', 'open_call_rows': 0,
                'phases': [
                    {'name': 'fixture', 'outcome': 'return', 'error': None,
                     'first_call_row': 0, 'last_call_row_exclusive': 1,
                     'elapsed': {'wall_monotonic': 1.5, 'thread_cpu': 1.0, 'process_cpu': 1.0,
                                 'self_user_cpu': 0.8, 'self_system_cpu': 0.2,
                                 'reaped_child_user_cpu': 0.0, 'reaped_child_system_cpu': 0.0}},
                    {'name': 'launch', 'outcome': 'exception', 'error': '_ReachedReservation: stopped',
                     'first_call_row': 1, 'last_call_row_exclusive': 3,
                     'elapsed': {'wall_monotonic': 12.0, 'thread_cpu': thread_cpu_launch,
                                 'process_cpu': thread_cpu_launch, 'self_user_cpu': thread_cpu_launch - 0.5,
                                 'self_system_cpu': 0.5, 'reaped_child_user_cpu': 0.0,
                                 'reaped_child_system_cpu': 0.0}},
                ],
                'calls': [
                    {'phase': 'fixture', 'label': 'public_fixture', 'name': 'make_case',
                     'first_line': 10, 'outcome': 'return', 'inclusive_thread_cpu': 1.0},
                    {'phase': 'launch', 'label': 'public_launch', 'name': 'synthetic_launch',
                     'first_line': 20, 'outcome': 'exception:_ReachedReservation',
                     'inclusive_thread_cpu': thread_cpu_launch},
                    {'phase': 'launch', 'label': 'attempt_mkdir', 'name': 'mkdir',
                     'first_line': 30, 'outcome': 'exception:_ReachedReservation',
                     'inclusive_thread_cpu': 0.01},
                ],
            },
        }

    legacy_arm = synthetic_arm('cpu-legacy', 'legacy', 10.0)
    monitoring_arm = synthetic_arm('cpu-monitoring', 'monitoring', 8.0)
    comparable = validator.compare_cpu_diagnostic_arms(legacy_arm, monitoring_arm)
    assert comparable['equal_completed_work'] is True
    assert comparable['host_qualified'] is False and comparable['accepted_quiet_host_timing'] is False
    assert comparable['total_explicit_phase_cpu']['thread_cpu']['difference'] == -2.0
    assert all('within_label_inclusive_thread_cpu' not in row['legacy'] for row in comparable['phases'])
    comparison_refused_as_accepted = refused(
        ValueError, lambda: validator.require_accepted_measurement(comparable)
    )
    divergent_outcome = deepcopy(monitoring_arm)
    divergent_outcome['diagnostic']['outcome'] = 'genuine_refusal'
    divergent_outcome['diagnostic']['error'] = 'subscription pre-reservation freshness margin is insufficient'
    divergent_outcome['measurement']['phases'][1]['error'] = 'ValueError: freshness margin insufficient'
    divergent_outcome['measurement']['phases'][1]['last_call_row_exclusive'] = 2
    divergent_outcome['measurement']['calls'] = divergent_outcome['measurement']['calls'][:2]
    divergent_outcome['measurement']['calls'][1]['outcome'] = 'exception:ValueError'
    divergent = validator.compare_cpu_diagnostic_arms(legacy_arm, divergent_outcome)
    assert divergent['equal_completed_work'] is False
    assert divergent['total_explicit_phase_cpu'] is None
    assert divergent['phases'][0]['phase'] == 'fixture' and divergent['phases'][0]['comparable'] is True
    assert divergent['phases'][0]['relative_cpu']['thread_cpu']['difference'] == 0.0
    assert divergent['phases'][1]['phase'] == 'launch' and divergent['phases'][1]['comparable'] is False
    assert divergent['phases'][1]['relative_cpu'] is None
    missing_identity_left = deepcopy(legacy_arm)
    missing_identity_right = deepcopy(monitoring_arm)
    del missing_identity_left['harness']
    del missing_identity_right['harness']
    missing_identity = validator.compare_cpu_diagnostic_arms(missing_identity_left, missing_identity_right)
    assert missing_identity['same_identity'] is False
    assert missing_identity['equal_completed_work'] is False
    assert missing_identity['total_explicit_phase_cpu'] is None
    assert all('pair_identity_differs' in row['reasons'] and row['relative_cpu'] is None
               for row in missing_identity['phases'])
    nonterminal_left = deepcopy(legacy_arm)
    nonterminal_right = deepcopy(monitoring_arm)
    nonterminal_left['measurement']['calls'][0]['outcome'] = None
    nonterminal_right['measurement']['calls'][0]['outcome'] = None
    nonterminal = validator.compare_cpu_diagnostic_arms(nonterminal_left, nonterminal_right)
    assert nonterminal['arms_clean'] is False
    assert nonterminal['equal_completed_work'] is False
    assert nonterminal['total_explicit_phase_cpu'] is None
    assert all(row['relative_cpu'] is None for row in nonterminal['phases'])
    forged_qualified_refused = refused(
        ValueError,
        lambda: validator.compare_cpu_diagnostic_arms(dict(legacy_arm, host_qualified=True), monitoring_arm),
    )
    return {
        'cpu_kinds_refused_as_accepted': cpu_refused,
        'failed_default_arm_refused': failed_default_refused,
        'intermediate_default_arm_refused': intermediate_default_refused,
        'missing_qualification_witness_refused': missing_witness_refused,
        'failed_qualification_refused': failed_qual_refused,
        'comparable_pair_equal_work': comparable['equal_completed_work'],
        'comparison_refused_as_accepted': comparison_refused_as_accepted,
        'divergent_launch_retains_equal_fixture_prefix': divergent['phases'][0]['comparable'],
        'divergent_launch_suppresses_launch_and_total': (
            divergent['phases'][1]['relative_cpu'] is None and divergent['total_explicit_phase_cpu'] is None
        ),
        'missing_identity_on_both_refused': not missing_identity['same_identity'],
        'nonterminal_outcome_on_both_refused': not nonterminal['arms_clean'],
        'forged_qualification_refused': forged_qualified_refused,
        'scope': 'Pure classification and equal-work CPU diagnostic comparison checks (#5817/#5818/#5819/#5820).',
    }


def role_environment(root, source, lease, extra=None):
    additions = dict(lease.environment())
    for name in ('WP1_FIXTURE_READY_FD', 'WP1_FIXTURE_RELEASE_FD', 'WP1_FIXTURE_NONCE'):
        if name in os.environ:
            additions[name] = os.environ[name]
    if extra:
        additions.update(extra)
    return environment(root, source, additions)


def command(role, source, output=None):
    result = [str(PYTHON), '-I', '-S', '-B', str(SELF), '--' + role, '--source', source]
    if output is not None:
        result += ['--out', str(output)]
    return result


def stage(args):
    root, manifest, manifest_sha, psutil, quiet, validator = context(args)
    role = next(name for name in ROLE_NAMES[1:] if getattr(args, name.replace('-', '_')))
    lease_fd = int(os.environ['U3WP1_LEASE_FD'])
    if role == 'worker':
        ready_fd, release_fd = int(os.environ['WP1_FIXTURE_READY_FD']), int(os.environ['WP1_FIXTURE_RELEASE_FD'])
        nonce = os.environ['WP1_FIXTURE_NONCE']
        ready = (json.dumps({'kind': 'wp1_sandbox_ready', 'nonce': nonce, 'pid': os.getpid(),
            'ppid': os.getppid(), 'pgid': os.getpgid(0), 'sid': os.getsid(0)}, sort_keys=True) + '\n').encode()
        if os.write(ready_fd, ready) != len(ready):
            raise RuntimeError('fixture detached ownership handoff was partial')
        os.close(ready_fd)
        available, _, _ = select.select([release_fd], [], [], max(0, WORK_END - time.monotonic()))
        if not available or os.read(release_fd, 256) != (nonce + '\n').encode():
            raise RuntimeError('fixture detached child was not ACKed by its outer owner')
        os.close(release_fd)
    reader = quiet.read_lease(lease_fd, role=role, expected_lock=root / 'tree.lock',
        expected_manifest_sha256=manifest_sha, expected_source_commit=args.source,
        role_scripts=ROLES, psutil_module=psutil)
    output = reader.output
    assert output == root / 'tree'
    if role in ('driver', 'worker'):
        assert args.out == output
    if role == 'child-check':
        assert args.out is None and '--out' not in sys.argv
    result = {'role': role, 'ready': reader.witness(),
              'adapters': reader_checks(reader, quiet, validator, output, role),
              'output_from_descriptor': str(output), 'argv': sys.argv,
              'interpreter_spelling': sys.executable, 'passed_expected_loss': False,
              'child_reaped': True, 'forced_cleanup': False,
              'child_was_live_at_loss': False}
    write(output / (role + '.ready.json'), result)
    child = None
    try:
        if role == 'child-check':
            while not (root / 'loss-trigger.json').is_file():
                if time.monotonic() >= WORK_END:
                    raise TimeoutError('fixture loss trigger deadline')
                time.sleep(0.01)
        else:
            following = {'supervised': 'driver', 'driver': 'worker', 'worker': 'child-check'}[role]
            descriptors = [lease_fd]
            if role in ('supervised', 'driver'):
                descriptors += [int(os.environ['WP1_FIXTURE_READY_FD']), int(os.environ['WP1_FIXTURE_RELEASE_FD'])]
            with (output / (following + '.log')).open('xb') as log:
                child = subprocess.Popen(command(following, args.source, output if following in ('driver', 'worker') else None),
                    cwd=ROOT, env=role_environment(root, args.source, reader), pass_fds=tuple(descriptors),
                    stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                    start_new_session=following == 'worker')
                if role in ('supervised', 'driver'):
                    for descriptor in descriptors[1:]:
                        os.close(descriptor)
                while child.poll() is None:
                    reader.validate()
                    if time.monotonic() >= WORK_END:
                        raise TimeoutError('fixture parent wait deadline')
                    time.sleep(0.01)
                child.wait()
                result.update(child_pid=child.pid, child_returncode=child.returncode)
                assert child.returncode == 125
        reader.validate()  # Deliberate lease replacement must raise through this boundary.
        raise AssertionError('fixture accepted a replaced lock')
    except quiet.LeaseLost as error:
        result.update(passed_expected_loss=True, lease_loss_reason=str(error),
                      sticky_failure_reason=reader.failure_reason,
                      child_was_live_at_loss=child is not None and child.poll() is None)
        write(output / (role + '.loss.json'), {
            'role': role, 'lease_loss_reason': str(error),
            'child_pid': child.pid if child is not None else None,
            'child_was_live_at_loss': result['child_was_live_at_loss']})
    except BaseException as error:
        result['error'] = {'type': type(error).__name__, 'message': str(error), 'traceback': traceback.format_exc()}
    finally:
        if child is not None and child.poll() is None:
            try:
                # Deliberate replacement propagates to every role. Give its
                # cooperative refusal/unwind a bounded chance to reap normally.
                child.wait(timeout=max(0.001, min(2, WORK_END - time.monotonic())))
            except subprocess.TimeoutExpired:
                result['forced_cleanup'] = True
                if child.poll() is None:
                    child.kill()  # Unreaped direct child, never a reused PID/group.
                try:
                    child.wait(timeout=0.5)
                except subprocess.TimeoutExpired:
                    result['child_reaped'] = False
        if child is not None:
            result.update(child_pid=child.pid, child_returncode=child.returncode)
            result['child_reaped'] = result['child_reaped'] and child.returncode is not None
        write(output / (role + '.result.json'), result)
        os.close(lease_fd)
    return 125 if (result['passed_expected_loss'] and result['child_reaped']
        and not result['forced_cleanup'] and (child is None or child.returncode == 125)) else 1


def outer(args):
    global CHILD, HANDOFF, TERMINAL_FD
    root, manifest, manifest_sha, psutil, quiet, validator = context(args)
    TERMINAL_FD = os.open(root / 'interruption.txt', os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    result = {'source_commit': args.source, 'passed': False,
              'scope': 'Synthetic helpers/process topology only; not real M/C/A runner, host qualification, same-path canary or timing readiness.'}
    owner = None
    try:
        result['pure_cases'] = pure_cases(root, args.source, manifest_sha, psutil, quiet, validator)
        result['qualification_fixtures'] = qualification_cases()
        result['cpu_diagnostic_fixtures'] = cpu_diagnostic_cases(validator)
        owner = acquisition(quiet, psutil, root, 'tree', manifest_sha, args.source)
        output = owner.output
        result['outer_witness'] = owner.witness()
        (root / 'tree.original-lock.json').write_bytes((root / 'tree.lock').read_bytes())
        HANDOFF = validator._SandboxHandoff(psutil)
        extras = {'WP1_FIXTURE_READY_FD': str(HANDOFF.ready_write),
                  'WP1_FIXTURE_RELEASE_FD': str(HANDOFF.release_read),
                  'WP1_FIXTURE_NONCE': HANDOFF.nonce}
        with (root / 'supervised.log').open('xb') as log:
            CHILD = subprocess.Popen(command('supervised', args.source), cwd=ROOT,
                env=role_environment(root, args.source, owner, extras),
                pass_fds=(owner.witness_fd, HANDOFF.ready_write, HANDOFF.release_read),
                stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            HANDOFF.attach(CHILD)
            while not (output / 'child-check.ready.json').is_file():
                HANDOFF.poll()
                owner.validate()
                if CHILD.poll() is not None or time.monotonic() >= WORK_END - 2:
                    raise RuntimeError('fixture process tree did not reach the child-check')
                time.sleep(0.01)
            HANDOFF.poll()
            assert HANDOFF.admitted
            ready = {role: json.loads((output / (role + '.ready.json')).read_bytes()) for role in ROLE_NAMES[1:]}
            leaf_chain = ready['child-check']['ready']['processes']
            assert [row['role'] for row in leaf_chain] == list(ROLE_NAMES)
            assert leaf_chain[1]['sid'] != leaf_chain[3]['sid']
            result['actual_process_chain'] = leaf_chain
            replacement = root / 'replacement-tree-lock'
            replacement.write_bytes(b'fixture foreign replacement; preserve this file\n')
            os.replace(replacement, root / 'tree.lock')
            # Keep the leaf alive until a real parent has noticed lease loss
            # during its wait. This makes active-child cleanup a measured path,
            # rather than validating only after all descendants already exit.
            active_loss = None
            while active_loss is None:
                HANDOFF.poll(allow_release=False)
                for role in ('supervised', 'driver', 'worker'):
                    path = output / (role + '.loss.json')
                    if path.is_file():
                        candidate = json.loads(path.read_bytes())
                        if candidate['child_was_live_at_loss']:
                            active_loss = candidate
                            break
                if active_loss is None:
                    if CHILD.poll() is not None or time.monotonic() >= WORK_END - 2:
                        raise RuntimeError('fixture did not observe loss with an active child')
                    time.sleep(0.01)
            result['active_child_loss_evidence'] = active_loss
            write(root / 'loss-trigger.json', {'kind': 'synthetic_lease_replacement'})
            while CHILD.poll() is None:
                HANDOFF.poll(allow_release=False)
                if time.monotonic() >= WORK_END:
                    raise TimeoutError('fixture lease-loss cleanup deadline')
                time.sleep(0.01)
            CHILD.wait()
        HANDOFF.poll(allow_release=False)
        result['sandbox_handoff'] = HANDOFF.witness()
        result['roles'] = {role: json.loads((output / (role + '.result.json')).read_bytes()) for role in ROLE_NAMES[1:]}
        assert CHILD.returncode == 125
        assert all(row['passed_expected_loss'] and row['child_reaped'] and not row['forced_cleanup']
                   and row['sticky_failure_reason'] for row in result['roles'].values())
        assert any(result['roles'][role]['child_was_live_at_loss'] for role in ('supervised', 'driver', 'worker'))
        assert all(result['roles'][role]['child_returncode'] == 125 for role in ('supervised', 'driver', 'worker'))
        assert not result['sandbox_handoff']['errors'] and not result['sandbox_handoff']['observed_surviving_pids']
        result['cleanup_verified'] = True
        result['lease_release'] = owner.release(cleanup_verified=True)
        assert result['lease_release']['retained'] and not result['lease_release']['released']
        assert (root / 'tree.lock').read_bytes() == b'fixture foreign replacement; preserve this file\n'
        result['passed'] = True
    except BaseException as error:
        result['error'] = {'type': type(error).__name__, 'message': str(error), 'traceback': traceback.format_exc()}
    finally:
        if not result.get('cleanup_verified', False):
            if HANDOFF is not None:
                HANDOFF.kill_detached()
                result['sandbox_handoff'] = HANDOFF.witness()
            if CHILD is not None and CHILD.poll() is None:
                os.killpg(CHILD.pid, signal.SIGKILL)
                try:
                    CHILD.wait(timeout=0.5)
                except subprocess.TimeoutExpired:
                    pass
            if owner is not None:
                result['lease_release'] = owner.retain('fixture_cleanup_uncertified')
        if HANDOFF is not None:
            HANDOFF.close()
        from scripts.adhoc.native_wp1_synthetic_smoke_20261110 import runtime_binaries
        result['sources_after'] = pins()
        result['source_unchanged'] = result['sources_after'] == manifest['source_files']
        result['runtime_binaries_after'] = runtime_binaries()
        result['runtime_unchanged'] = result['runtime_binaries_after'] == manifest['runtime_binaries']
        result['bytecode_cache_created'] = os.path.lexists(root / 'unused-pycache')
        result['elapsed_seconds'] = time.monotonic() - manifest['started_monotonic']
        result['passed'] = result['passed'] and result['source_unchanged'] and result['runtime_unchanged'] and not result['bytecode_cache_created']
        write(root / 'outcome.json', result)
        if TERMINAL_FD is not None:
            os.close(TERMINAL_FD)
    return 0 if result['passed'] else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True)
    parser.add_argument('--out', type=Path)
    role = parser.add_mutually_exclusive_group()
    for name in ROLE_NAMES:
        role.add_argument('--' + name, action='store_true')
    args = parser.parse_args()
    if not re.fullmatch('[0-9a-f]{40}', args.source):
        raise ValueError('full frozen source SHA required')
    if not any(getattr(args, name.replace('-', '_')) for name in ROLE_NAMES):
        return bootstrap(args)
    return outer(args) if args.outer else stage(args)


if __name__ == '__main__':
    raise SystemExit(main())
