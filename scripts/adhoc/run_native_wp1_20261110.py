#!/usr/bin/env python3
"""WP1 fixed-node driver with bounded supervision, 2026-11-10.

Inputs: the fresh closed WP1 contract and outer supervisor's absolute deadline.
Outputs: inherited M sandbox/origin/cleanup evidence plus WP1 deadline witnesses.
Derived by composition from the unchanged M runner, not by editing protected
files or its packet approvals. No setup/hydration mode is exposed here.

Measured arms authenticate the inherited read-only lease carrier and the real
process ancestry at M import, C/A entry and A's runtime pause observation.
This source implementation conveys no permission to execute a measured arm.
"""
from __future__ import annotations

import importlib.util
import json
import math
import os
from pathlib import Path
import signal
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[2]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


contract_module = load('native_wp1_contract', ROOT / 'scripts/adhoc/native_wp1_validation_20261110.py')
MANIFEST, MANIFEST_SHA, CONTRACT = contract_module.contract()
KIND = os.environ['U3WP1_KIND']
if KIND not in contract_module.KINDS:
    raise ValueError('WP1 admits only the fixed equivalence canary and arms')
NODE, ARM, LIMIT = contract_module.KINDS[KIND]
CLASSIFICATION = contract_module.measurement_classification(KIND)
if os.environ.get('U3WP1_MEASUREMENT_CLASS') != CLASSIFICATION['measurement_class']:
    raise ValueError('WP1 measurement class must match the selected kind')
if os.environ.get('U3WP1_CONSUMER_ARM') != ARM or os.environ.get('U3K_PROFILE') != 'control':
    raise ValueError('WP1 arm and control metrics selection must be explicit')
STARTED = float(os.environ['U3WP1_STARTED_MONOTONIC'])
HARD_DEADLINE = float(os.environ['U3WP1_HARD_DEADLINE'])
now = time.monotonic()
if (not math.isfinite(STARTED) or not math.isfinite(HARD_DEADLINE)
        or HARD_DEADLINE - STARTED != LIMIT or not STARTED <= now < HARD_DEADLINE):
    raise ValueError('WP1 absolute invocation deadline is missing, invalid or expired')
quiet = contract_module.wp1_helper('quiet')
LEASE = None
if KIND in contract_module.NO_LEASE_KINDS:
    quiet.refuse_existing(contract_module.QUIET_LOCK)
    if 'U3WP1_LEASE_FD' in os.environ:
        raise ValueError(KIND + ' cannot borrow a measured-arm lease')
else:
    sys.path.append(str(contract_module.dependency_site()))
    import psutil
    role = 'child-check' if '--child-check' in sys.argv else ('worker' if '--worker' in sys.argv else 'driver')
    LEASE = contract_module.read_quiet_lease(quiet, psutil, role, MANIFEST_SHA, CONTRACT)
os.environ['U3M_MANIFEST'] = CONTRACT['composition_manifest']
os.environ['U3M_MANIFEST_SHA'] = CONTRACT['composition_manifest_sha256']
os.environ['U3M_OBSERVE'] = '1'
for name in ('U3F_PARITY', 'U3M_D126', 'U3M_DEPENDENCY_CANARY'):
    if os.environ.get(name, '0') != '0':
        raise ValueError('WP1 cannot select another validation mode')
if LEASE is None:
    m = load('native_wp1_retained_m', ROOT / 'scripts/adhoc/run_native_u3m_20261109.py')
else:
    m = contract_module.load_with_lease_os('native_wp1_retained_m',
        ROOT / 'scripts/adhoc/run_native_u3m_20261109.py', LEASE)
runner = m.runner
wrapper = m.wrapper
r = m.h.g.f.r
original_popen = r.original_popen
original_environment = runner.clean_environment
original_worker = runner.worker
children = []
timers = []
watchdog_events = []
runner.__file__ = wrapper.__file__ = str(Path(__file__).resolve())
original_lock = runner.LOCK
original_wrapper_os = wrapper.os
if LEASE is not None:
    runner.LOCK = LEASE.lock_view()
    wrapper.os = LEASE.os_proxy()


def restore_adapters():
    runner.LOCK = original_lock
    wrapper.os = original_wrapper_os
    m.os = os


def check_args(args):
    if LEASE is not None:
        LEASE.validate()
        if args.out != LEASE.output:
            raise ValueError('WP1 arguments differ from the inherited lease output')
    if args.collect_only or args.workers != 1 or args.nodes != [NODE]:
        raise ValueError('WP1 requires its exact fixed node and one worker; no collection/batch mode')
    expected_prefix = 'wp1-' + CONTRACT['source_commit'][:12] + '-' + KIND + '-'
    if args.out.parent != contract_module.SCRATCH or not args.out.name.startswith(expected_prefix):
        raise ValueError('WP1 output must identify this source and arm')
    if time.monotonic() >= HARD_DEADLINE:
        raise ValueError('WP1 invocation deadline expired before test entry')


def environment(out, interpreter_directory):
    result = original_environment(out, interpreter_directory)
    # The inherited allowlist removes credentials before any Python child starts.
    result.update(U3WP1_MANIFEST=str(MANIFEST), U3WP1_MANIFEST_SHA=MANIFEST_SHA,
        U3WP1_KIND=KIND, U3WP1_CONSUMER_ARM=ARM,
        U3WP1_MEASUREMENT_CLASS=CLASSIFICATION['measurement_class'], U3K_PROFILE='control',
        U3WP1_STARTED_MONOTONIC=repr(STARTED), U3WP1_HARD_DEADLINE=repr(HARD_DEADLINE),
        U3M_OBSERVE='1')
    if result.get('PYTEST_PLUGINS') != 'scripts.adhoc.u3m_metrics_plugin_20261109':
        raise ValueError('WP1 requires exactly the existing control metrics plugin')
    if LEASE is not None:
        LEASE.validate()
        result.update(LEASE.environment())
    return result


def worker(args):
    check_args(args)
    runner.subprocess.Popen = bounded_popen
    try:
        return original_worker(args)
    finally:
        runner.subprocess.Popen = original_popen


def bounded_popen(command, *args, **kwargs):
    """Keep inherited child session and owned-descendant cleanup unchanged."""
    is_test = bool(command and command[0] == '/usr/bin/sandbox-exec')
    is_check = (isinstance(command, (list, tuple)) and len(command) == 5
        and command[1:3] == ['-P', '-B']
        and command[3] == str(Path(__file__).resolve()) and command[4] == '--child-check')
    if LEASE is not None and (is_test or is_check):
        LEASE.validate()
        if kwargs.get('env', {}).get('U3WP1_LEASE_FD') != str(LEASE.witness_fd):
            raise ValueError('WP1 child spawn lost its inherited lease carrier')
    if is_test:
        # The driver cutoff is recomputed at actual launch, after preparation,
        # rather than granting a new full budget when preparation finishes.
        remaining = HARD_DEADLINE - time.monotonic()
        if remaining <= 10:
            raise RuntimeError('insufficient WP1 invocation budget for child and cleanup')
        runner.DEADLINE = remaining - 10
        if kwargs.get('start_new_session') is not True:
            raise RuntimeError('WP1 sandbox child must retain its isolated session')
        if kwargs.get('pass_fds'):
            raise RuntimeError('unexpected inherited descriptors at the WP1 sandbox boundary')
        ready_fd = int(os.environ['U3WP1_READY_FD'])
        release_fd = int(os.environ['U3WP1_RELEASE_FD'])
        # The gate is a pinned diagnostic helper, before sandbox-exec. It cannot
        # exec the unchanged test command until the OUTER supervisor owns its
        # detached session. The inner watchdog is no longer the sole owner.
        command = [sys.executable, '-S', '-P', '-B',
            str(ROOT / 'scripts/adhoc/native_wp1_child_gate_20261110.py'),
            '--ready-fd', str(ready_fd), '--release-fd', str(release_fd),
            '--nonce', os.environ['U3WP1_HANDOFF_NONCE'],
            '--deadline', repr(HARD_DEADLINE - 5), '--', *command]
        kwargs['pass_fds'] = (ready_fd, release_fd) + (() if LEASE is None else (LEASE.witness_fd,))
    elif is_check and LEASE is not None:
        if kwargs.get('pass_fds'):
            raise ValueError('unexpected descriptors at the WP1 child-check boundary')
        kwargs['pass_fds'] = (LEASE.witness_fd,)
    child = original_popen(command, *args, **kwargs)
    if is_test:
        os.close(ready_fd)
        os.close(release_fd)
        children.append(child)

        def cutoff():
            if child.poll() is None:
                watchdog_events.append(dict(pid=child.pid, reason='sandbox_hard_cutoff',
                    elapsed=time.monotonic() - STARTED, invocation_limit_seconds=LIMIT))
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass

        # Independent from the inherited process-tree observation loop. This is
        # five seconds before the same outer hard deadline, never old3250/3300s.
        timer = threading.Timer(max(0, HARD_DEADLINE - 5 - time.monotonic()), cutoff)
        timer.daemon = True
        timer.start()
        timers.append(timer)
    return child


def supervised(args):
    before = {'load': os.getloadavg(), 'logical_cpus': os.cpu_count()}
    runner.subprocess.Popen = bounded_popen
    code = 125
    try:
        # r.parent is the retained C/A supervisor below the old3300s wrapper.
        # It retains the clean-source/origin/OS-denial/observed-cleanup guards.
        code = r.parent(args)
    finally:
        for child in children:
            if child.poll() is None:
                watchdog_events.append(dict(pid=child.pid, reason='supervisor_exit_with_live_child',
                    elapsed=time.monotonic() - STARTED))
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
        for timer in timers:
            timer.cancel()
        runner.subprocess.Popen = original_popen
        if args.out.is_dir():
            runner.save(args.out / 'wp1-cutoff.json', dict(
                invocation_limit_seconds=LIMIT, outer_deadline=HARD_DEADLINE,
                driver_cutoff_seconds_before_outer=10,
                sandbox_cutoff_seconds_before_outer=5, events=watchdog_events,
                elapsed=time.monotonic() - STARTED))
            runner.save(args.out / 'host-load.json', dict(before=before,
                after={'load': os.getloadavg()}, scope='instant samples; not an idle-host gate'))
            runner.save(args.out / 'wp1-quiet-lease.json',
                dict(kind=KIND, **CLASSIFICATION,
                     lease=None if LEASE is None else LEASE.witness()))
    return 125 if watchdog_events or time.monotonic() > HARD_DEADLINE else code


def parent(args):
    check_args(args)
    m.require_composition()
    current = contract_module.contract()
    if current[:2] != (MANIFEST, MANIFEST_SHA) or current[2] != CONTRACT:
        raise ValueError('WP1 contract changed before invocation')
    code = m.parent(args)
    current = contract_module.contract()
    unchanged = current[:2] == (MANIFEST, MANIFEST_SHA) and current[2] == CONTRACT
    if args.out.is_dir():
        harness_ok = (code == 0 and unchanged and time.monotonic() <= HARD_DEADLINE)
        harness_class = contract_module.measurement_classification(
            KIND, qualification=contract_module.read_qualification_witness(args.out),
            certified=harness_ok, final_owner=False)
        runner.save(args.out / 'wp1-harness.json', dict(kind=KIND, arm=ARM, node=NODE,
            **harness_class,
            manifest=str(MANIFEST), manifest_sha256=MANIFEST_SHA,
            composition_manifest=CONTRACT['composition_manifest'],
            composition_manifest_sha256=CONTRACT['composition_manifest_sha256'],
            source_commit=CONTRACT['source_commit'], source_unchanged=unchanged,
            implementation_sha256=CONTRACT['implementation_sha256'],
            interpreter=CONTRACT['interpreter'], invocation_limit_seconds=LIMIT,
            seconds=time.monotonic() - STARTED, metrics_profile='control',
            quiet_window=(KIND + ' refuses any lock') if LEASE is None else LEASE.witness(),
            scope=('Unqualified contended relative CPU/call-count diagnostic only; wall time and freshness non-authoritative, no quiet-host, production or native acceptance'
                   if KIND in contract_module.CPU_DIAGNOSTIC_KINDS
                   else 'Observer diagnostic only; no production or native acceptance')))
    return code if unchanged and time.monotonic() <= HARD_DEADLINE else 125


m.original_parent = supervised
runner.clean_environment = environment
runner.worker = worker
runner.parent = parent
runner.DEADLINE = LIMIT - 10
if __name__ == '__main__':
    # No hydration, preparation, arbitrary nodes or wider timeout modes.
    if '--hydrate-local-dependency' in sys.argv:
        raise ValueError('WP1 setup is a separately authorized action')
    runner.time = wrapper.DeadlineClock()
    try:
        raise SystemExit(runner.main())
    finally:
        restore_adapters()
