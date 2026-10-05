"""Explicit one-use native26 execution through the fixed common lifetime.

Only launch can invoke the declared native runtime. Preparation/readback and
all selection helpers remain offline; there is no public synthetic bypass.
"""
from __future__ import annotations

from pathlib import Path
import sys

from . import native_execution as legacy
from . import native_execution_authority as authority
from . import native_shared_contract as c
from . import native_shared_controller as composition
from . import native_shared_registration as registration
from . import native_shared_gates as gates
from . import native_shared_results as results
from . import native_shared_evidence as evidence
from .native_attempt_supervisor import durable_new, _sync_directory

KIND = c.KINDS['attempt']
VERSION = 1
REQUIRED_CHECKS = legacy.REQUIRED_CHECKS
UNASSESSED = legacy.UNASSESSED
_signals, _mkdir_durable = legacy._signals, legacy._mkdir_durable
_now, _platform = legacy._now, legacy._platform
_probe_runtime = legacy._probe_runtime
expected_runtime_observation = legacy.expected_runtime_observation


def _file(path, name):
    return evidence.read_regular(str(path), name, max_bytes=c.HARD_LIMITS['request_bytes']).captured.raw


def _unchanged(value, raw, authorization):
    if registration.verified(raw) != value:
        raise ValueError('native shared execution selection changed')
    authority.require_committed(value['dependencies'])
    for name, path in authorization['inputs'].items():
        if _file(path, name + ' evidence') != authorization['raw'][name]:
            raise ValueError('external native shared launch authority changed')
    if _platform() != value['runtime']['keep_awake']['host_platform']:
        raise ValueError('registered execution host differs from this process')


def _engine_bindings():
    from .native_execution_engine import ExecutionContract, ExecutionEffects
    contract = ExecutionContract(kind=KIND, registration=registration, composition=composition,
        authority=authority, gates=gates, replay=results, shared=results)
    effects = ExecutionEffects(file=_file, durable_new=durable_new, sync_directory=_sync_directory,
        mkdir_durable=_mkdir_durable, signals=_signals, now=_now, probe_runtime=_probe_runtime,
        expected_runtime_observation=expected_runtime_observation, authorizations=authorizations,
        unchanged=_unchanged, sys=sys)
    return contract, effects


def authorizations(raw, value, *, review_path, ci_path, launch_word_path):
    from .native_execution_engine import authorizations as check
    contract, _ = _engine_bindings()
    return check(raw, value, review_path=review_path, ci_path=ci_path,
        launch_word_path=launch_word_path, contract=contract, file=_file)


def launch(registration_raw, *, review_path, ci_path, launch_word_path):
    from .native_execution_engine import launch as execute
    contract, effects = _engine_bindings()
    return execute(registration_raw, review_path=review_path, ci_path=ci_path,
        launch_word_path=launch_word_path, contract=contract, effects=effects)


def read_final(registration_raw):
    from .native_execution_engine import read_final as read
    contract, effects = _engine_bindings()
    return read(registration_raw, contract=contract, effects=effects)
