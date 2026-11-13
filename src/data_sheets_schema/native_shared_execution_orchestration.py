"""Public orchestration for one-use native26 execution; not a consumer.

Only launch can invoke a declared native runtime. The separate synthetic entry
accepts only the exact ordinary-Python software peer and retains every gate.
Preparation/readback and all selection helpers remain offline.
"""
from __future__ import annotations

from . import native_pre_dispatch_timing as pre_timing

from pathlib import Path
import sys

from . import native_execution as legacy
from . import native_execution_authority_v2 as authority
from . import native_execution_registration_v2 as admission
from . import native_shared_contract as c
from . import native_shared_controller_orchestration as composition
from . import native_shared_registration_orchestration as registration
from . import native_shared_gates as gates
from . import native_shared_results_orchestration as results
from . import native_shared_evidence as evidence
from .native_attempt_supervisor import durable_new, _sync_directory

KIND = c.KINDS['attempt']
VERSION = 1
required_checks = admission.required_checks
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
    _unchanged_inputs(value, authorization)


def _unchanged_inputs(value, authorization):
    """Live refusal checks only; this does not verify or admit an execution.

    Keep the shared route's actual source, file and platform dependencies here.
    The launch-local reservation path separately reconstructs execution through
    full current capture authority before it can acquire the reservation lease.
    """
    authority.require_committed(value['dependencies'])
    for name, path in authorization['inputs'].items():
        if _file(path, name + ' evidence') != authorization['raw'][name]:
            raise ValueError('external native shared launch authority changed')
    if _platform() != value['runtime']['keep_awake']['host_platform']:
        raise ValueError('registered execution host differs from this process')


def _engine_bindings(*, launch_guard=None):
    from .native_execution_orchestration import ExecutionContract, ExecutionEffects
    contract = ExecutionContract(kind=KIND, registration=registration, composition=composition,
        authority=authority, gates=gates, replay=results, shared=results)
    effects = ExecutionEffects(file=_file, durable_new=durable_new, sync_directory=_sync_directory,
        mkdir_durable=_mkdir_durable, signals=_signals, now=_now, probe_runtime=_probe_runtime,
        expected_runtime_observation=expected_runtime_observation, authorizations=authorizations,
        unchanged=_unchanged, sys=sys, launch_guard=launch_guard)
    return contract, effects


def authorizations(raw, value, *, review_path, ci_path, launch_word_path):
    """    RunSpec boundary: validated-caller

    RunSpec precondition: Caller supplies execution bytes and a fixed verified value; the common authorization routine freshly verifies preparation before checking declarations.
    """
    from .native_execution_orchestration import authorizations as check
    contract, _ = _engine_bindings()
    return check(raw, value, review_path=review_path, ci_path=ci_path,
        launch_word_path=launch_word_path, contract=contract, file=_file)


def launch(registration_raw, *, review_path, ci_path, launch_word_path,
           subscription_guard_path, subscription_guard_sha256, expected_authority_sha256=None):
    """    RunSpec boundary: validated-caller

    RunSpec precondition: Caller supplies explicit execution registration; registration.verified reconstructs guarded preparation before creating fixed effects or dispatching.
    """
    with pre_timing.scope(registration_raw):
        from .native_execution_orchestration import launch as execute
        from .native_subscription_admission import preflight_current_selection, select_current
        from .native_u4b_runtime import validate_prepared_runtime
        from .native_runtime_profiles import require_production
        with authority.launch_derivations():
            value = registration.verified(registration_raw)
            require_production(value['runtime'])
            validate_prepared_runtime(value['runtime'])
            attempt = Path(value['attempt_directory'])
            if attempt.exists() or attempt.is_symlink():
                raise ValueError('native attempt must be new; spent identities cannot resume')
            guard = select_current(subscription_guard_path, subscription_guard_sha256,
                registration_raw=registration_raw, runtime=value['runtime'],
                launch_word_path=launch_word_path, review_path=review_path)
            preflight_current_selection(
                guard, registration_raw=registration_raw, value=value)
            contract, effects = _engine_bindings(launch_guard=guard)
            return execute(registration_raw, review_path=review_path, ci_path=ci_path,
                launch_word_path=launch_word_path, contract=contract, effects=effects,
                expected_authority_sha256=expected_authority_sha256)


def synthetic_launch(registration_raw, *, review_path, ci_path, launch_word_path,
                     subscription_guard_path, subscription_guard_sha256):
    """Run the fixed local software peer through the complete execution engine.

    This separate entry cannot accept a real executable/account. Saved authority
    remains expressly synthetic; actual capture and production launch refuse it.

    RunSpec boundary: validated-caller

    RunSpec precondition: Caller supplies explicit synthetic execution-registration bytes; registration.verified reconstructs guarded preparation before creating fixed effects, and the common synthetic engine retains fresh admission before dispatch.
    """
    with pre_timing.scope(registration_raw):
        from dataclasses import replace
        from .native_execution_orchestration import synthetic_launch as execute
        from .native_subscription_admission import preflight_current_selection, select_current
        from .native_u4b_runtime import validate_prepared_runtime
        from .native_runtime_profiles import require_synthetic
        with authority.launch_derivations():
            value = registration.verified(registration_raw)
            require_synthetic(value['runtime'])
            validate_prepared_runtime(value['runtime'])
            attempt = Path(value['attempt_directory'])
            if attempt.exists() or attempt.is_symlink():
                raise ValueError('native attempt must be new; spent identities cannot resume')
            guard = select_current(subscription_guard_path, subscription_guard_sha256,
                registration_raw=registration_raw, runtime=value['runtime'],
                launch_word_path=launch_word_path, review_path=review_path)
            preflight_current_selection(
                guard, registration_raw=registration_raw, value=value)
            contract, effects = _engine_bindings(launch_guard=guard)
            effects = replace(effects, probe_runtime=_synthetic_runtime_observation)
            return execute(registration_raw, review_path=review_path, ci_path=ci_path,
                launch_word_path=launch_word_path, contract=contract, effects=effects)


def _synthetic_runtime_observation(value):
    """Read fixed peer identity only; no auth command, account or provider."""
    from .native_runtime_profiles import require_synthetic
    runtime = value['runtime']
    require_synthetic(runtime)
    return {'checked': True, 'passed': True,
        'observed_at': 'EXPLICITLY SYNTHETIC SOFTWARE TEST ONLY',
        'binary': legacy.registration.executable_identity(runtime['executable']['path']),
        'version': runtime['executable']['version'],
        'auth': {key: runtime['auth'][key] for key in
                 ('loggedIn', 'authMethod', 'apiProvider', 'subscriptionType')},
        'environment_sha256': legacy.draft._sha(legacy.draft._encoded(value['environment'])),
        'scope': 'Synthetic software-peer fingerprint and declarations; no real authentication or native observation.'}


def read_final(registration_raw):
    """RunSpec boundary: validated-caller

    RunSpec precondition: Caller supplies exact execution-registration bytes; the fixed shared-v2 delegation freshly verifies guarded preparation for ordinary results. Explicit validation-failure diagnostics verify failed historical bytes only and cannot assert completion or authority.
    """
    from .native_execution_orchestration import read_final as read
    contract, effects = _engine_bindings()
    return read(registration_raw, contract=contract, effects=effects)
