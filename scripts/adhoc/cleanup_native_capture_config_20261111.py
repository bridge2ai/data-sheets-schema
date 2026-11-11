#!/usr/bin/env python3
"""Bound the unchanged S382f private-config cleanup; native capture, 2026-11-11.

Inputs: exact frozen source/composer and its existing composition/backup.
Outputs: fresh wrapper evidence plus the composer's config-restored.json.
The lead authorized this separate helper; it changes neither frozen worktree,
launches no tests, and applies no packets. Run only after independent review.
A timeout is failure, even if config replacement preceded interruption; inspect
retained bytes and evidence before any retry. No descendant-retirement claim
is made by this wrapper: it preserves the composer's existing Git cleanup.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import runpy
import signal
import stat
import sys
import time

HEAD = '382f0dfd1ce863fdf257a77e2bbb2637dbe2f67b'
TOOLS = Path(__file__).resolve().parents[2]
SOURCE = TOOLS.parent / 'codex-native-u1u3'
COMPOSER = SOURCE / 'scripts/adhoc/compose_native_u3m_20261109.py'
COMPOSER_SHA = 'a61c01d768a9c88a7bcd10921b6fe84c6111649f42378553a06efba8bb34bb76'
BASE = SOURCE / 'scripts/adhoc/compose_native_u1u3_20261108.py'
BASE_SHA = '6b474a73891f613b19034f4d618dbf8a93e8d360cb7724d6959117912e8d547a'
SCRATCH = TOOLS.parent / 'scratch-native-u1u3/u3m'
COMPOSITION = SCRATCH / ('composition-' + HEAD[:12])
EVIDENCE = SCRATCH / ('cleanup-wrapper-' + HEAD[:12] + '-20261111')
SOFT_SECONDS = 170
HARD_SECONDS = 180


def need(condition, message):
    if not condition:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def regular(path):
    need(path.resolve(strict=True) == path and path.is_file(),
         'physical regular file required: ' + str(path))
    return path.read_bytes()


def save(path, value):
    raw = (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()
    with path.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    need(regular(path) == raw, 'wrapper evidence did not persist exactly')


def main():
    started = time.monotonic()
    hard_deadline = started + HARD_SECONDS
    need(len(sys.argv) == 1, 'this cleanup wrapper accepts no arguments')
    need(sys.flags.no_site and sys.flags.safe_path and sys.dont_write_bytecode,
         'run with the retained Python -S -P -B')
    need(TOOLS.name == 'codex-native-capture-cleanup-20261111'
         and TOOLS.resolve(strict=True) == TOOLS, 'assigned physical helper worktree required')
    need(signal.getitimer(signal.ITIMER_REAL) == (0.0, 0.0),
         'cleanup wrapper cannot replace an existing alarm')
    expired = False

    def hard_stop(number, frame):
        os._exit(124)

    def soft_stop(number, frame):
        nonlocal expired
        expired = True
        signal.signal(signal.SIGALRM, hard_stop)
        signal.setitimer(signal.ITIMER_REAL, max(0.001, hard_deadline - time.monotonic()))
        raise TimeoutError('private config cleanup reached its 170-second soft deadline')

    previous_alarm = signal.signal(signal.SIGALRM, soft_stop)
    signal.setitimer(signal.ITIMER_REAL, max(0.001, started + SOFT_SECONDS - time.monotonic()))
    previous_argv, previous_cache = sys.argv, sys.pycache_prefix
    result = None
    try:
        need(SOURCE.resolve(strict=True) == SOURCE and SCRATCH.resolve(strict=True) == SCRATCH,
             'physical frozen source and scratch roots required')
        need(sha(regular(COMPOSER)) == COMPOSER_SHA and sha(regular(BASE)) == BASE_SHA,
             'frozen composer or retained base helper changed')
        manifest_raw = regular(COMPOSITION / 'composition.json')
        manifest = json.loads(manifest_raw)
        need(manifest['source_commit'] == HEAD, 'composition source differs')
        need(not os.path.lexists(EVIDENCE), 'wrapper evidence exists; preserve it and stop')
        EVIDENCE.mkdir()
        sys.pycache_prefix = str(EVIDENCE / 'never-created-pycache')
        need(not os.path.lexists(sys.pycache_prefix), 'fresh isolated pycache prefix required')
        result = dict(status='started', source_commit=HEAD, source_worktree=str(SOURCE),
            helper=str(Path(__file__).resolve()), helper_sha256=sha(regular(Path(__file__).resolve())),
            composer_sha256=COMPOSER_SHA, base_helper_sha256=BASE_SHA,
            composition_manifest_sha256=sha(manifest_raw),
            soft_limit_seconds=SOFT_SECONDS, hard_limit_seconds=HARD_SECONDS,
            timeout=False, descendant_retirement_verified=False,
            acceptance_requires_zero_wrapper_exit=True)
        save(EVIDENCE / 'started.json', result)
        # M's unchanged require_source checks exact clean HEAD/branch and all
        # protected preimages before touching config; retain every such check.
        sys.argv = [str(COMPOSER), 'cleanup', '--commit', HEAD]
        runpy.run_path(str(COMPOSER), run_name='__main__')
        need(not expired and time.monotonic() < started + SOFT_SECONDS,
             'cleanup completed after its soft deadline; not accepted')
        restored_path = COMPOSITION / 'config-restored.json'
        restored_raw = regular(restored_path)
        restored = json.loads(restored_raw)
        row = manifest['private_config']
        config = regular(Path(row['path']))
        backup = regular(Path(row['backup']))
        need(restored['source_commit'] == HEAD
             and restored['status'] == 'config_restored_evidence_and_worktree_retained'
             and restored['composition_manifest_sha256'] == sha(manifest_raw)
             and config == backup and sha(config) == row['original_sha256']
             and stat.S_IMODE(Path(row['path']).stat().st_mode) == row['original_mode']
             and restored['restored_sha256'] == restored['backup_sha256'] == sha(config)
             and regular(COMPOSITION / 'composition.json') == manifest_raw,
             'saved restoration or restored config differs')
        # This records an observation before process exit, never a standalone
        # success certificate. A signal during final persistence still fails.
        result.update(status='config_restoration_observed', restored_report_sha256=sha(restored_raw),
                      restored_config_sha256=sha(config))
    except BaseException as exc:
        if result is not None:
            result.update(status='failed', timeout=expired or isinstance(exc, TimeoutError),
                          error_type=type(exc).__name__, error=str(exc)[:4096])
        raise
    finally:
        try:
            if result is not None:
                result.update(elapsed_seconds=time.monotonic() - started)
                # Both soft and hard guards remain armed during Git cleanup and
                # evidence persistence. A hard exit leaves only started evidence.
                save(EVIDENCE / 'result.json', result)
        finally:
            sys.argv, sys.pycache_prefix = previous_argv, previous_cache
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, previous_alarm)


if __name__ == '__main__':
    main()
