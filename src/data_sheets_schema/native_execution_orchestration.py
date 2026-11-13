"""Orchestration for the explicit shared v2 route; never an A3 consumer.

Contracts are package-owned Python bindings, never selected by serialized import
names. This module owns reservation, signals, cleanup, sticky failure, strict
aggregation and publication; selected adapters supply semantic reconstruction.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
import stat
import threading
from types import ModuleType
from typing import Callable

from data_sheets_schema import native_attribution_registration as draft
from data_sheets_schema import native_execution_gates as lifecycle_checks
from data_sheets_schema import native_execution_registration_v2 as admission
from data_sheets_schema import native_shared_contract as c

from .native_execution_engine import GATES, UNASSESSED


@dataclass(frozen=True)
class ExecutionContract:
    kind: str
    registration: ModuleType
    composition: ModuleType
    authority: ModuleType
    gates: ModuleType
    replay: ModuleType
    shared: ModuleType

    def require_fixed(self):
        names = {
            'd4d_native_shared_attempt': (
                'native_shared_registration_orchestration', 'native_shared_controller_orchestration',
                'native_execution_authority_v2', 'native_shared_gates',
                'native_shared_results_orchestration', 'native_shared_results_orchestration'),
        }.get(self.kind)
        modules = (self.registration, self.composition, self.authority,
                   self.gates, self.replay, self.shared)
        if names is None or any(type(module) is not ModuleType or
                module.__name__ != 'data_sheets_schema.' + name
                for module, name in zip(modules, names)):
            raise ValueError('native engine requires a fixed package execution contract')
        if (tuple(self.gates.GATES) != GATES or GATES != admission.EXECUTION_GATES
                or type(self.registration.AUTHORITY_VERSION) is not int
                or self.registration.AUTHORITY_VERSION != 2):
            raise ValueError('native execution contract must retain all original runtime obligations')

    def make_controller(self, value, registration_raw):
        raw = value['composition_raw_json'].encode()
        return self.composition.CallbackAdapter(raw, execution=value,
                                                registration_raw=registration_raw)

    def prewarm_controller(self, adapter):
        """Warm cold pure work in a closed scope; no callback finder escapes.

        RunSpec boundary: validated-caller

        RunSpec precondition: The fixed contract supplies an adapter constructed
        from freshly verified execution/composition bytes; its prewarm method
        revalidates before opening and closing the callback admission scope.
        """
        adapter.prewarm_before_acceptance()

    def transport_phase_spec(self, adapter):
        # This is a fixed renderer26 adapter, not a caller-selected phase bypass.
        # Its observer and saved checker reconstruct all old phase obligations.
        adapter.require_phase_authority()
        if (type(getattr(adapter.spec, 'render_version', None)) is not int
                or adapter.spec.render_version != 26
                or type(getattr(adapter.spec, 'native_shared_generation_version', None)) is not int
                or adapter.spec.native_shared_generation_version != 1
                or type(adapter.policy) is not dict or not adapter.policy
                or not callable(adapter.classify) or not callable(adapter.observe)):
            raise ValueError('native shared transport requires its selected policy and phase observer')
        return None

    def activate_before_dispatch(self, adapter, started_raw):
        if self.kind == 'd4d_native_shared_attempt':
            self.transport_phase_spec(adapter)
            adapter.activate_before_dispatch(started_raw)

    def check_additional_readback(self, value, result):
        if self.kind == 'd4d_native_shared_attempt':
            self.replay.require_saved_basis(value, result)


@dataclass(frozen=True)
class ExecutionEffects:
    file: Callable
    durable_new: Callable
    sync_directory: Callable
    mkdir_durable: Callable
    signals: Callable
    now: Callable
    probe_runtime: Callable
    expected_runtime_observation: Callable
    authorizations: Callable
    unchanged: Callable
    sys: object
    launch_guard: object = None


def authorizations(raw, value, *, review_path, ci_path, launch_word_path, contract, file):
    """Check exact saved external declarations; this performs no web discovery.

    The artifacts are caller-supplied review/CI/owner evidence, not signatures.
    A matching hash does not authenticate their author or GitHub's service.

    RunSpec boundary: validated-caller

    RunSpec precondition: Caller supplies execution bytes and a fixed contract; verified reconstructs the selected preparation before external authorization comparisons.
    """
    contract.require_fixed()
    inputs = {name: str(Path(path).absolute()) for name, path in {
        'review': review_path, 'ci': ci_path, 'launch_word': launch_word_path}.items()}
    from .native_shared_controls_orchestration import loaded_controls
    with loaded_controls(value['dependencies']) as classifier_projection:
        if admission.verified(raw, classifier_projection=classifier_projection) != value:
            raise ValueError('authorization caller differs from fresh v2 execution')
    evidence = admission._authorizations(raw, value, review_path=inputs['review'],
        ci_path=inputs['ci'], launch_word_path=inputs['launch_word'], require_current=True)
    captured = {name: item.raw for name, item in evidence.items()}
    records = {name: c.strict_json(body, name + ' evidence') for name, body in captured.items()}
    binding = {'registration_sha256': c.sha(raw), 'attempt_id': value['attempt_id'],
               'source_commit': value['dependencies']['base']['source_commit'],
               'dependencies_sha256': c.sha(c.canonical(value['dependencies']))}
    contract.registration.execution_paths_v2(value, fresh=False, extra_protected=list(inputs.values()))
    for name, item in evidence.items():
        if file(inputs[name], name + ' evidence') != item.raw:
            raise ValueError('external v2 execution authority changed while observed')
    return {'inputs': inputs, 'raw': captured, 'records': records, 'binding': binding,
            'identity': {name: {'path': inputs[name], 'sha256': draft._sha(body)} for name, body in captured.items()}}


def _join_subscription_authority(guard, raw, value, authorization, *, current_launch=False):
    """Join admission to the engine's independently recaptured authority."""
    if guard is not None:
        from .native_subscription_admission import context
        module, extra = context(guard.raw, registration_raw=raw, runtime=value['runtime'],
            launch_word_raw=authorization['raw']['launch_word'], review_bundle_raw=authorization['raw']['review'],
            current=current_launch)
        if current_launch:
            from .native_u4b_runtime import validate_prepared_runtime
            from .native_subscription_guard_v2 import SubscriptionGuard
            validate_prepared_runtime(value['runtime'])
            if type(guard) is not SubscriptionGuard or module.VERSION != 2:
                raise ValueError('current native engine requires the exact v2 subscription guard')
            if guard._clock is not module._now:
                raise ValueError('current native engine requires the actual dispatch clock')
        module.SubscriptionGuard(guard.raw, expected_sha256=module.sha(guard.raw),
            registration_raw=raw, runtime=value['runtime'],
            launch_word_raw=authorization['raw']['launch_word'], check_freshness=current_launch, **extra)


def _saved_authorizations(raw, value, started_raw, result, *, contract, file):
    """Recheck consumed v2 approval bytes without reservation or re-aging.

    The original authority path map is evidence too: started/final maps must
    agree, match the current original bytes, and (for complete captures) match
    their separately captured input roles. A self-rehashed final result cannot
    replace independent review, CI or the owner word with assertion flags.
    """
    attempt = Path(value['attempt_directory'])
    captured = admission._authorizations(raw, value,
        review_path=attempt/'review.json', ci_path=attempt/'ci.json',
        launch_word_path=attempt/'launch_word.json')
    started = c.strict_json(started_raw, 'saved started identity')
    c.exact(started, {'kind', 'version', 'state', 'attempt_id', 'started_at',
        'registration_sha256', 'composition_sha256', 'authority', 'dispatch_limit',
        'dispatch_unit', 'profile', *UNASSESSED}, 'saved started identity')
    from .native_runtime_profiles import profile_name
    if (started['kind'] != contract.kind or type(started['version']) is not int
            or started['version'] != 1 or started['state'] != 'started'
            or started['attempt_id'] != value['attempt_id']
            or started['registration_sha256'] != c.sha(raw)
            or started['composition_sha256'] != value['composition_sha256']
            or type(started['dispatch_limit']) is not int or started['dispatch_limit'] != 1
            or started['dispatch_unit'] != 'native CLI process, not provider transactions'
            or started['profile'] != profile_name(value['runtime'])
            or result.get('profile') != started['profile']
            or any(started[name] != expected for name, expected in UNASSESSED.items())):
        raise ValueError('saved started identity differs from its one-use v2 execution')
    admission._text(started['started_at'], 'saved start timestamp')
    c.exact(result.get('authority'), {'review', 'ci', 'launch_word'}, 'saved authority paths')
    if c.canonical(started['authority']) != c.canonical(result['authority']):
        raise ValueError('started and final external authority identities differ')
    original_paths = []
    catalog = result.get('captured_files')
    if type(catalog) is not dict:
        raise ValueError('saved authority requires an explicit captured file map')
    for name, item in captured.items():
        pin = result['authority'][name]
        c.exact(pin, {'path', 'sha256'}, 'saved authority identity')
        c.canonical_path(pin['path'], 'saved original authority')
        if pin['sha256'] != item.pin.sha256 or file(pin['path'], name + ' original evidence') != item.raw:
            raise ValueError('saved authority identity differs from consumed and original bytes')
        original_paths.append(pin['path'])
        if result.get('runtime_gates_passed') is True:
            for path, role in ((pin['path'], 'authority:' + name),
                               (item.pin.path, 'authority:consumed_' + name)):
                basis = catalog.get(path)
                if (type(basis) is not dict or basis.get('sha256') != item.pin.sha256
                        or type(basis.get('bytes')) is not int or basis['bytes'] != item.pin.bytes
                        or type(basis.get('roles')) is not list or role not in basis['roles']):
                    raise ValueError('completed authority lacks its exact independent captured role')
    contract.registration.execution_paths_v2(value, fresh=False, extra_protected=original_paths)
    return captured


def _admit_subscription_guard(guard, attempt, file, write):
    """Consume exact saved admission before the caller may activate/spawn."""
    if guard is None:
        return
    if file(attempt/'subscription-guard.json', 'subscription guard') != guard.raw:
        raise ValueError('consumed subscription guard changed before dispatch')
    guard.before_dispatch()
    write(attempt/'subscription-dispatched.json', draft._encoded({
        'guard_sha256': draft._sha(guard.raw), 'consumed': True}))


def _guarded_observer(guard, adapter, budget_stop):
    def observe(event):
        if guard is not None:
            try:
                guard.observe(event)
            except ValueError as exc:
                raise budget_stop('subscription guard: ' + str(exc)) from exc
        _controller_call(adapter, 'observe', budget_stop, event)
    return observe


def _controller_call(adapter, name, budget_stop, *args):
    """Keep a C refusal's text across separately source-loaded exception types."""
    try:
        return getattr(adapter, name)(*args)
    except BaseException as error:
        if (isinstance(error, getattr(adapter, '_budget_stop', budget_stop))
                and not isinstance(error, budget_stop)):
            raise budget_stop(str(error)) from error
        raise


def _guarded_classifier(adapter, budget_stop):
    def classify(*args):
        return _controller_call(adapter, 'classify', budget_stop, *args)
    return classify


def launch(registration_raw, *, review_path, ci_path, launch_word_path,
           contract: ExecutionContract, effects: ExecutionEffects, expected_authority_sha256=None):
    """Consume one explicitly authorized native attempt, never retry or resume.

    This method can invoke the selected native executable. Calling it is a
    separate action from preparation; there is no inferred model or live value.

    RunSpec boundary: validated-caller

    RunSpec precondition: Caller supplies explicit execution registration and fixed effects; registration.verified reconstructs the guarded preparation before any execution effect.
    """
    contract.require_fixed()
    with contract.authority.launch_derivations():
        from .native_execution_capabilities import loaded_capabilities
        from .native_runtime_profiles import require_production, PRODUCTION_PROFILE
        value = contract.registration.verified(registration_raw)
        require_production(value['runtime'])
        # Resolve the complete reviewed execution/replay interface before entering
        # the path that can reserve directories, write evidence or probe a runtime.
        with loaded_capabilities(value['dependencies']) as controls:
            return _launch(registration_raw, review_path=review_path, ci_path=ci_path,
                launch_word_path=launch_word_path, contract=contract, effects=effects,
                controls=controls, expected_profile=PRODUCTION_PROFILE,
                expected_authority_sha256=expected_authority_sha256)


def synthetic_launch(registration_raw, *, review_path, ci_path, launch_word_path,
                     contract: ExecutionContract, effects: ExecutionEffects):
    """Fixed synthetic dispatch entry; the real launch entry always refuses it.

    RunSpec boundary: validated-caller

    RunSpec precondition: Caller supplies explicit synthetic execution-registration bytes and the fixed shared-v2 contract and effects; registration.verified reconstructs guarded preparation, and _launch retains fresh admission before execution effects.
    """
    contract.require_fixed()
    with contract.authority.launch_derivations():
        from .native_execution_capabilities import loaded_capabilities
        from .native_runtime_profiles import require_synthetic, SYNTHETIC_PROFILE
        value = contract.registration.verified(registration_raw)
        require_synthetic(value['runtime'])
        with loaded_capabilities(value['dependencies']) as controls:
            return _launch(registration_raw, review_path=review_path, ci_path=ci_path,
                launch_word_path=launch_word_path, contract=contract, effects=effects,
                controls=controls, expected_profile=SYNTHETIC_PROFILE)


def _require_launch_profile(runtime, expected):
    from .native_runtime_profiles import (
        PRODUCTION_PROFILE, SYNTHETIC_PROFILE, require_production, require_synthetic)
    if expected == PRODUCTION_PROFILE:
        require_production(runtime)
    elif expected == SYNTHETIC_PROFILE:
        require_synthetic(runtime)
    else:
        raise ValueError('unknown fixed execution profile')


def _execute_child(controls, argv, **kwargs):
    """The sole orchestration dispatch to the reviewed historical transport."""
    controls.require_complete()
    return controls['run_native_canary'].execute_child(argv, **kwargs)


def _launch(registration_raw, *, review_path, ci_path, launch_word_path,
            contract, effects, controls, expected_profile='production', expected_authority_sha256=None):
    controls.require_complete()
    registration, composition, authority = contract.registration, contract.composition, contract.authority
    gates, replay, shared = contract.gates, contract.replay, contract.shared
    KIND, VERSION = contract.kind, 1
    _file, durable_new, _sync_directory = effects.file, effects.durable_new, effects.sync_directory
    _mkdir_durable, _signals, _now = effects.mkdir_durable, effects.signals, effects.now
    _probe_runtime, expected_runtime_observation = effects.probe_runtime, effects.expected_runtime_observation
    authorizations, _unchanged, sys = effects.authorizations, effects.unchanged, effects.sys
    launch_guard = effects.launch_guard
    if contract.kind == 'd4d_native_shared_attempt' and launch_guard is None:
        raise ValueError('shared native launch requires a subscription guard')
    value = registration.verified(registration_raw)
    original_execution = c.canonical(value)  # Invocation-local comparison bytes, never authority.
    _require_launch_profile(value['runtime'], expected_profile)
    authorization = authorizations(registration_raw, value, review_path=review_path,
                                  ci_path=ci_path, launch_word_path=launch_word_path)
    from .native_sequence_inputs import check_authority
    check_authority(expected_authority_sha256, authorization['raw'])
    from .native_subscription_admission import (
        CurrentSelection, inspect_current_selection, accept_current_selection)
    if type(launch_guard) is CurrentSelection:
        inspect_current_selection(launch_guard, registration_raw=registration_raw,
            runtime=value['runtime'], authorization=authorization)
    else:
        # Existing lower-engine callers still supply an actual guard. Validate
        # its static join now; actual type/clock/current-word checks run below.
        _join_subscription_authority(
            launch_guard, registration_raw, value, authorization, current_launch=False)
    _unchanged(value, registration_raw, authorization)
    runtime_identity = expected_runtime_observation(value)
    selected = composition.verified_composition(value['composition_raw_json'].encode())
    attempt, evidence, *outputs = registration.execution_paths_v2(value, fresh=True,
        extra_protected=list(authorization['inputs'].values()))
    if threading.current_thread() is not threading.main_thread():
        raise ValueError('native launch requires the main thread')
    # This is the last check before the first effect. A prior verified value,
    # permission recipe or Admission object is never a launch capability.
    with controls.loaded_classifier() as classifier_projection:
        admitted = admission.admit(registration_raw, review_path=authorization['inputs']['review'],
            ci_path=authorization['inputs']['ci'], launch_word_path=authorization['inputs']['launch_word'],
            classifier_projection=classifier_projection)
    if (admitted.registration_raw != registration_raw
            or tuple((item.pin.path, item.raw) for item in admitted.evidence) != tuple(
                (authorization['inputs'][name], authorization['raw'][name])
                for name in ('review', 'ci', 'launch_word'))):
        raise ValueError('fresh v2 admission differs from the captured launch authority')
    # All cold controller/callback derivations finish before saved-capture
    # acceptance. The warmup closes its source-loader scope before returning:
    # never keep a consumer finder active across live bootstrap orchestration.
    adapter = contract.make_controller(value, registration_raw)
    contract.prewarm_controller(adapter)
    accepted_current_selection = False
    if type(launch_guard) is CurrentSelection:
        launch_guard = accept_current_selection(launch_guard,
            registration_raw=registration_raw, runtime=value['runtime'],
            authorization=authorization)
        accepted_current_selection = contract.kind == 'd4d_native_shared_attempt'
    _join_subscription_authority(
        launch_guard, registration_raw, value, authorization, current_launch=True)
    if accepted_current_selection:
        # Skip this effects.unchanged invocation only on the actual accepted
        # shared selection route. Its complete reconstruction/equality check is
        # joined to the fresh lease authority below; these input checks retain
        # the shared route's actual _file, _platform and source dependencies.
        from .native_shared_execution_orchestration import _unchanged_inputs
        _unchanged_inputs(value, authorization)
    else:
        _unchanged(value, registration_raw, authorization)
    from .native_subscription_capture import capture_admission_lease

    @contextmanager
    def reservation_lease():
        if not accepted_current_selection:
            with capture_admission_lease(registration_raw=registration_raw,
                    review_bundle_raw=authorization['raw']['review'],
                    launch_word_raw=authorization['raw']['launch_word'],
                    guard_raw=launch_guard.raw if launch_guard is not None else None) as current:
                yield current
            return
        # This input-only entry performs the full fresh preparation/consumer
        # reconstruction and current-protocol check. Neither saved bytes nor a
        # previous value supplies admission, and no loader scope is revived.
        from .native_subscription_capture import _current_authority, _require_latest_guard_claim
        from . import native_capture_words as words
        fresh_authority = _current_authority(registration_raw,
            authorization['raw']['review'], authorization['raw']['launch_word'])
        fresh_value = fresh_authority[0]
        if (c.canonical(fresh_value) != original_execution
                or c.canonical(value) != original_execution):
            raise ValueError('native shared execution selection changed before reservation')
        with words.locked(fresh_value, registration_raw, create=False) as journal:
            current = journal.require(authorization['raw']['launch_word'])
            _require_latest_guard_claim(launch_guard.raw, fresh_authority, journal,
                                        authorization['raw']['launch_word'])
            yield current

    # Hold the registration-wide word/limits lock through the first reservation
    # effect. A renewal cannot supersede the word between checking and mkdir.
    with reservation_lease():
        controls.require_complete()
        # Source recapture can be slow: measure the preparation margin only
        # after it, immediately before the attempt identity is consumed.
        launch_guard.before_reservation()
        _require_launch_profile(value['runtime'], expected_profile)
        attempt.mkdir(mode=0o700)  # Even a partial reservation consumes the identity.
        _sync_directory(attempt.parent)
    durable_new(attempt/'registration.json', registration_raw)
    if launch_guard is not None:
        durable_new(attempt/'subscription-guard.json', launch_guard.raw)
    started = {'kind': KIND, 'version': VERSION, 'state': 'started', 'attempt_id': value['attempt_id'],
        'started_at': _now(), 'registration_sha256': draft._sha(registration_raw),
        'composition_sha256': value['composition_sha256'], 'authority': authorization['identity'],
        'dispatch_limit': 1, 'dispatch_unit': 'native CLI process, not provider transactions',
        'profile': expected_profile, **UNASSESSED}
    started_raw = draft._encoded(started)
    durable_new(attempt/'started.json', started_raw)
    evidence.mkdir(mode=0o700)
    _sync_directory(evidence.parent)
    for name, body in authorization['raw'].items():
        durable_new(attempt/(name + '.json'), body)
    status = first_stop = prepared = first_error = None
    projections = {}
    signals = []
    observation = {'checked': False, 'passed': False, 'reason': 'native runtime not observed'}
    awake = {'passed': False, 'policy': value['runtime']['keep_awake'], 'state': 'not_acquired'}
    additional_path = evidence/'attribution-replay.json'
    results = {name: {'checked': False, 'passed': False, 'reason': 'capture unavailable'} for name in GATES}
    def stopped(message):
        nonlocal first_stop
        if first_stop is None:
            first_stop = str(message)
    from . import native_host_power as host_power
    host_power.start_run(attempt)
    with _signals(signals):
        proxy = controls['run_direct_canary'].NoProxy()
        guard = None
        try:
            try:
                for directory in outputs:
                    _mkdir_durable(directory)
                _mkdir_durable(attempt/'cli_config')
                if contract.kind == 'd4d_native_shared_attempt':
                    from .native_helper_cache import create_for_attempt
                    create_for_attempt(value)
                _unchanged(value, registration_raw, authorization)
                if value['runtime']['keep_awake']['policy'] == 'macos_iokit_ims_v1':
                    guard = controls['run_direct_canary_awake'].KeepAwake()
                    guard.__enter__()
                    awake.update(state='acquired', acquisition=guard.snapshot())
                else:
                    awake.update(state='explicitly_not_applicable', passed=True)
                observation = _probe_runtime(value)
                durable_new(attempt/'runtime-observation.json', draft._encoded(observation))
                def launch_check():
                    _unchanged(value, registration_raw, authorization)
                    _join_subscription_authority(launch_guard, registration_raw, value, authorization, current_launch=True)
                    if (_file(attempt/'registration.json', 'consumed registration') != registration_raw
                            or _file(attempt/'started.json', 'started identity') != started_raw
                            or _file(attempt/'runtime-observation.json', 'runtime observation') != draft._encoded(observation)
                            or proxy.closed or proxy.failed.is_set()):
                        raise ValueError('native admission is closed or consumed identity changed')
                    _admit_subscription_guard(launch_guard, attempt, _file, durable_new)
                    contract.activate_before_dispatch(adapter, started_raw)
                    _require_launch_profile(value['runtime'], expected_profile)
                observe = _guarded_observer(launch_guard, adapter, controls['run_native_canary'].BudgetStop)
                status = _execute_child(controls, value['argv'], proxy=proxy,
                    instruction=Path(selected['instruction_path']), attempt=attempt,
                    cwd=value['working_directory'], env=value['environment'],
                    deadline_seconds=value['runtime']['deadline_seconds'], verify_launch=launch_check,
                    record_stop=stopped, command_policy=adapter.policy, phase_spec=contract.transport_phase_spec(adapter),
                    command_classifier=_guarded_classifier(adapter, controls['run_native_canary'].BudgetStop),
                    event_observer=observe)
            except BaseException as exc:
                first_error = exc
                # Native auth command failures may contain credentials in captured
                # subprocess attributes. Record only the exception class here.
                stopped(f'launch or runtime failed: {type(exc).__name__}')
                if not (attempt/'runtime-observation.json').exists():
                    observation = {'checked': False, 'passed': False, 'reason': first_stop}
                    durable_new(attempt/'runtime-observation.json', draft._encoded(observation))
            try:
                if proxy.failed.is_set():
                    stopped(proxy.failure or 'native controller reported failure')
                if type(proxy.unfinished_handlers) is not int or proxy.unfinished_handlers != 0:
                    stopped('native controller has unresolved handler state')
                live = adapter.report(complete=True)
                authority_inputs = {**authorization['inputs'], 'system': value['system_path'],
                    'permission_probe': value['permission_probe']}
                for name in authorization['inputs']:
                    authority_inputs['consumed_' + name] = str(attempt/(name + '.json'))
                try:
                    prepared = replay.capture(value, controls, authority_inputs=authority_inputs,
                                             registration_raw=registration_raw)
                except Exception as exc:
                    if first_error is None:
                        first_error = exc
                    problem = f'capture: {type(exc).__name__}: {exc}'
                    stopped(problem)
                    prepared = shared.incomplete_capture(value['composition'], attempt, adapter, problem,
                        live_phase_report=live.get('phase_history'))
                projections = shared.project(prepared, evidence/'captured')
                if prepared.get('replay_complete'):
                    replay.write_report(prepared, additional_path)
                # Keep assertions through both bounded shutdown and evidence capture.
                if guard is not None:
                    guard.close()
                    awake.update(state='released', releases=guard.releases, released_at=guard.released_at,
                        passed=bool(awake.get('acquisition')) and len(guard.releases) == 3
                            and all(type(row.get('return_code')) is int and row['return_code'] == 0 for row in guard.releases))
                awake['signals_received'] = list(signals)
                if signals:
                    stopped('launcher interrupted by signal')
                if not awake['passed']:
                    stopped('keep-awake acquisition or release did not complete')
                durable_new(attempt/'keep-awake.json', draft._encoded(awake))
                results = gates.check(prepared, projections, {**value['runtime'], 'attempt_directory': str(attempt)},
                    controls.gate_members, exit_code=status, shutdown=getattr(proxy, 'control_shutdown', None),
                    live=live, first_stop=first_stop, runtime_authority=observation, keep_awake=awake,
                    runtime_authority_expected=runtime_identity,
                    keep_awake_raw=_file(attempt/'keep-awake.json', 'observed cleanup'))
                for name, label in (('runtime_authority', 'runtime observation'), ('keep_awake', 'cleanup evidence')):
                    if results[name].get('passed') is not True:
                        # Retain this failure and its byte pins even if the file
                        # is restored before final lifecycle collection.
                        stopped(label + ' validation failed before publication: '
                            + draft._encoded(results[name]).decode().strip())
                for path, copy in projections.items():
                    if copy.read_bytes() != prepared['snapshot'].raw[path]:
                        raise ValueError('captured projection changed during validation')
                prepared['snapshot'].verify_unchanged()
                _unchanged(value, registration_raw, authorization)
            except BaseException as exc:
                if first_error is None:
                    first_error = exc
                stopped(f'finalization failed: {type(exc).__name__}: {exc}')
        finally:
            # This boundary also covers observation/failure-evidence writes:
            # persistence errors must never bypass acquired assertion cleanup.
            with host_power.finishing_run(attempt):
                pending_error = sys.exc_info()[1]
                if guard is not None:
                    if guard.active:
                        guard.close()
                        awake.update(state='released_after_failure', passed=False)
                    awake.update(releases=guard.releases, released_at=guard.released_at,
                                 signals_received=list(signals))
                    try:
                        if not (attempt/'keep-awake.json').exists():
                            durable_new(attempt/'keep-awake.json', draft._encoded(awake))
                    except BaseException as cleanup_error:
                        original = pending_error if pending_error is not None else first_error
                        if original is None:
                            raise
                        # A link can exist even when its directory fsync failed;
                        # that first error remains authoritative after its handler.
                        note = 'keep-awake cleanup evidence failed: ' + type(cleanup_error).__name__
                        original.__notes__ = [*getattr(original, '__notes__', []), note]
                        if pending_error is None:
                            raise original from cleanup_error
        try:
            # Cleanup failure is sticky even if another gate or a previous pass succeeds.
            if first_stop is not None:
                results['first_stop'] = {'checked': True, 'passed': False, 'reason': first_stop}
            lifecycle_raw = {name: _file(attempt/name, 'lifecycle artifact')
                for name in ('runtime-observation.json', 'keep-awake.json') if (attempt/name).exists()}
            if 'runtime-observation.json' in lifecycle_raw:
                results['runtime_authority'] = lifecycle_checks.runtime_observation_result(
                    lifecycle_raw['runtime-observation.json'], observation, runtime_identity)
            else:
                results['runtime_authority'] = {'checked': False, 'passed': False, 'reason': 'runtime observation unavailable'}
            if 'keep-awake.json' in lifecycle_raw:
                results['keep_awake'] = lifecycle_checks.cleanup_result(
                    lifecycle_raw['keep-awake.json'], awake, value['runtime']['keep_awake'])
            else:
                results['keep_awake'] = {'checked': False, 'passed': False, 'reason': 'cleanup evidence unavailable'}
            if 'receipt_origin_reporting' in value:
                from .native_receipt_origin import attach_prepared
                results = attach_prepared(value, results, prepared)
            if launch_guard is not None and _file(
                    attempt/'subscription-guard.json', 'subscription guard') != launch_guard.raw:
                raise ValueError('consumed subscription guard changed before publication')
            completed = (set(results) == set(GATES)
                and all(row.get('checked') is True and row.get('passed') is True for row in results.values()))
            transcript_raw = (prepared['snapshot'].raw.get(str(attempt/'transcript.jsonl'))
                              if prepared is not None else None)
            guard_snapshot, subscription_observation_verification, validation_failure = _publication_subscription(
                launch_guard, registration_raw, value['runtime'], authorization, transcript_raw,
                completed=completed)
            if validation_failure is not None:
                stopped('publication validation failed at ' + validation_failure['stage'] + ': '
                        + validation_failure['reason'])
                results['first_stop'] = {'checked': True, 'passed': False, 'reason': first_stop}
                completed = False
            final = {'kind': KIND, 'version': VERSION, 'attempt_id': value['attempt_id'],
                'profile': expected_profile,
                'state': 'completed_pending_independent_review' if completed else 'failed',
                'runtime_gates_passed': completed, **UNASSESSED, 'first_stop': first_stop,
                'registration_sha256': draft._sha(registration_raw), 'started_sha256': draft._sha(started_raw),
                'composition_sha256': value['composition_sha256'], 'authority': authorization['identity'],
                'child_exit_code': status, 'shutdown': getattr(proxy, 'control_shutdown', None),
                'runtime_observation': observation, 'keep_awake': awake, 'gates': results,
                'lifecycle_artifacts': {name: {'path': str(attempt/name),
                    'sha256': draft._sha(body)} for name, body in lifecycle_raw.items()},
                'captured_files': prepared['snapshot'].identity() if prepared is not None else {},
                'captured_aliases': dict(prepared['snapshot'].aliases) if prepared is not None else {},
                'captured_metadata': dict(prepared['snapshot'].metadata) if prepared is not None else {},
                'captured_alias_metadata': dict(prepared['snapshot'].alias_metadata) if prepared is not None else {},
                'additional_report': {'path': str(additional_path), 'sha256': draft._sha(_file(additional_path, 'replay report'))}
                    if additional_path.exists() else None,
                'scope': 'Controller/runtime completion only. Saved authority is not authenticated; native permission observations do not prove production helpers, future permissions, billing or scientific support.'}
            if launch_guard is not None:
                final['subscription_guard'] = guard_snapshot
                final['subscription_observation_verification'] = subscription_observation_verification
            if validation_failure is not None:
                final['publication_validation_failure'] = validation_failure
                consumed = {**lifecycle_raw, 'registration.json': registration_raw,
                    'started.json': started_raw, 'subscription-guard.json': launch_guard.raw,
                    **{name + '.json': raw for name, raw in authorization['raw'].items()}}
                if prepared is not None:
                    for name in _FAILURE_MEMBERS:
                        body = prepared['snapshot'].raw.get(str(attempt / name))
                        if body is not None:
                            consumed.setdefault(name, body)
                final['failure_evidence'] = _failure_evidence(attempt, consumed=consumed)
            if prepared is not None and 'retained_artifacts' in prepared:
                final['retained_artifacts'] = shared.retention_manifest(prepared, projections)
                final['capture_problems'] = list(prepared['capture_problems'])
            final_raw = draft._encoded(final)
            from .native_receipt_origin import check_final_bytes
            if KIND == 'd4d_native_shared_attempt':
                from .native_shared_contract import HARD_LIMITS
                final_reader_bound = HARD_LIMITS['request_bytes']
            else:
                from .native_attempt_supervisor import MAX_BYTES
                final_reader_bound = MAX_BYTES
            check_final_bytes(value, final_raw, max_bytes=final_reader_bound)
            durable_new(evidence/'final.json', final_raw)
            durable_new(evidence/'published.json', draft._encoded({'final_sha256': draft._sha(final_raw),
                'started_sha256': draft._sha(started_raw), 'registration_sha256': draft._sha(registration_raw)}))
            return final
        except BaseException as publication_error:
            if first_error is not None and publication_error is not first_error:
                note = 'native lifecycle or publication failed after the original error: ' + type(publication_error).__name__
                first_error.__notes__ = [*getattr(first_error, '__notes__', []), note]
                raise first_error from publication_error
            raise



def _publication_subscription(guard, registration_raw, runtime, authorization, transcript_raw, *, completed):
    """A validation exception can produce diagnostics only, never completion.

    Keep the successful path's context and observation checks intact. Do not
    call the same failing runtime validator again to authorize a failure.
    """
    from .native_subscription_admission import context
    snapshot = guard.snapshot()
    stage = 'subscription_admission.context'
    try:
        module, extra = context(guard.raw, registration_raw=registration_raw,
            runtime=runtime, launch_word_raw=authorization['raw']['launch_word'],
            review_bundle_raw=authorization['raw']['review'])
        stage = 'subscription_guard.validate_saved_observations'
        verification = module.validate_saved_observations(guard.raw, snapshot,
            registration_raw=registration_raw, runtime=runtime,
            launch_word_raw=authorization['raw']['launch_word'],
            transcript_raw=transcript_raw, complete=completed, **extra)
        return snapshot, verification, None
    except (ValueError, OSError) as exc:
        failure = {'stage': stage, 'error_type': type(exc).__name__, 'reason': str(exc) or type(exc).__name__}
        return snapshot, {'checked': False, 'passed': False, 'complete': False,
            'basis': 'Failure diagnostic only; subscription observations not independently verified.'}, failure


_FAILURE_MEMBERS = ('registration.json', 'started.json', 'review.json', 'ci.json',
    'launch_word.json', 'subscription-guard.json', 'subscription-dispatched.json',
    'runtime-observation.json', 'keep-awake.json', 'transcript.jsonl', 'control.jsonl',
    'stderr.txt', 'native-shared-effect-stop.json')


def _failure_evidence(attempt, *, consumed=None):
    """Pin available early evidence without interpreting runtime authority."""
    from .native_shared_evidence import read_regular
    out = {}
    consumed = consumed or {}
    for name in _FAILURE_MEMBERS:
        path = str(Path(attempt) / name)
        try:
            item = read_regular(path, name, max_bytes=c.HARD_LIMITS['stream_bytes']).captured
            out[name] = {'path': path, 'bytes': item.pin.bytes, 'sha256': item.pin.sha256}
        except (OSError, ValueError) as exc:
            out[name] = {'path': path, 'not_kept': type(exc).__name__ + ': ' + str(exc)}
        if name in consumed:
            raw = consumed[name]
            pin = {'path': path, 'bytes': len(raw), 'sha256': c.sha(raw)}
            if out[name] != pin:
                pin['changed_after_consumption'] = (
                    out[name].get('not_kept') or 'disk bytes differ from consumed bytes')
            out[name] = pin
    return out


def _read_failure_diagnostic(registration_raw, *, contract, file, expected_runtime_observation):
    """Read historical failed bytes, expressly without verifying live authority.

    This route cannot return success. Its input is a structurally closed v2
    envelope, not a freshly validated RunSpec. Normal results return to the
    existing full semantic reader, including its fresh registration check.
    """
    envelope = c.strict_json(registration_raw, 'failure registration', admission.MAX_WIRE_BYTES)
    c.exact(envelope, {'authority_version', 'controller_sources_sha256', 'registration'}, 'failure envelope')
    if type(envelope['authority_version']) is not int or envelope['authority_version'] != 2:
        raise ValueError('failure diagnostic requires a v2 envelope')
    value = envelope['registration']
    admission._closed_execution(value)
    for name in ('attempt_directory', 'evidence_directory'):
        c.canonical_path(value[name], name)
    attempt, evidence = Path(value['attempt_directory']), Path(value['evidence_directory'])
    final_raw = file(evidence / 'final.json', 'final result')
    result = c.strict_json(final_raw, 'final result')
    if type(result) is not dict or 'publication_validation_failure' not in result:
        return None
    checks = result.get('gates')
    if (result.get('state') != 'failed' or result.get('runtime_gates_passed') is not False
            or type(result.get('first_stop')) is not str or not result['first_stop']
            or type(checks) is not dict or set(checks) != set(GATES)
            or any(type(row) is not dict or type(row.get('checked')) is not bool
                   or type(row.get('passed')) is not bool for row in checks.values())
            or checks['first_stop'].get('passed') is not False
            or any(result.get(name) != expected for name, expected in UNASSESSED.items())):
        raise ValueError('failure diagnostic cannot assert completion or acceptance')
    failure = c.exact(result['publication_validation_failure'], {'stage', 'error_type', 'reason'}, 'failure diagnostic')
    if (failure['stage'] not in ('subscription_admission.context', 'subscription_guard.validate_saved_observations')
            or any(type(failure[key]) is not str or not failure[key] for key in failure)):
        raise ValueError('failure diagnostic lacks its validation failure')
    verification = result.get('subscription_observation_verification')
    if (type(verification) is not dict
            or any(verification.get(key) is not False for key in ('checked', 'passed', 'complete'))):
        raise ValueError('failure diagnostic cannot claim subscription verification')
    started_raw = file(attempt / 'started.json', 'started identity')
    expected = {'final_sha256': c.sha(final_raw), 'started_sha256': c.sha(started_raw),
                'registration_sha256': c.sha(registration_raw)}
    if c.strict_json(file(evidence / 'published.json', 'publication marker')) != expected:
        raise ValueError('failure diagnostic publication is incomplete or changed')
    started = c.strict_json(started_raw, 'started identity')
    if (result.get('kind') != contract.kind or type(result.get('version')) is not int or result['version'] != 1
            or result.get('attempt_id') != value['attempt_id']
            or result.get('composition_sha256') != value['composition_sha256']
            or any(result.get(key) != expected[key] for key in ('started_sha256', 'registration_sha256'))
            or file(attempt / 'registration.json', 'consumed registration') != registration_raw
            or started.get('registration_sha256') != c.sha(registration_raw)
            or started.get('attempt_id') != value['attempt_id']
            or started.get('authority') != result.get('authority')):
        raise ValueError('failure diagnostic differs from consumed attempt identity')
    members = c.exact(result.get('failure_evidence'), set(_FAILURE_MEMBERS), 'failure evidence')
    from .native_shared_evidence import read_regular
    for name, pin in members.items():
        if type(pin) is not dict or pin.get('path') != str(attempt / name):
            raise ValueError('failure evidence path differs')
        if 'not_kept' in pin:
            c.exact(pin, {'path', 'not_kept'}, 'unavailable failure evidence')
            if type(pin['not_kept']) is not str or not pin['not_kept']:
                raise ValueError('failure evidence lacks unavailable reason')
            continue
        extra = {'changed_after_consumption'} if 'changed_after_consumption' in pin else set()
        c.exact(pin, {'path', 'bytes', 'sha256'} | extra, 'failure evidence pin')
        if extra and (type(pin['changed_after_consumption']) is not str or not pin['changed_after_consumption']):
            raise ValueError('failure evidence lacks its post-consumption change reason')
        if type(pin['bytes']) is not int or not 0 <= pin['bytes'] <= c.HARD_LIMITS['stream_bytes']:
            raise ValueError('failure evidence has invalid byte bound')
        try:
            item = read_regular(pin['path'], name, max_bytes=max(1, pin['bytes'])).captured
        except (OSError, ValueError) as exc:
            raise ValueError('failure evidence cannot be read: ' + str(exc)) from exc
        if item.pin.bytes != pin['bytes'] or item.pin.sha256 != pin['sha256']:
            raise ValueError('failure evidence differs from its published pin')
    for name in ('registration.json', 'started.json', 'review.json', 'ci.json', 'launch_word.json', 'subscription-guard.json'):
        if 'not_kept' in members[name]:
            raise ValueError('failure diagnostic lacks consumed identity evidence')
    for name in ('review', 'ci', 'launch_word'):
        if result['authority'][name]['sha256'] != members[name + '.json']['sha256']:
            raise ValueError('failure evidence differs from consumed authority bytes')
    guard = result.get('subscription_guard')
    if (type(guard) is not dict or guard.get('guard_sha256') != members['subscription-guard.json']['sha256']
            or guard.get('registration_sha256') != c.sha(registration_raw)):
        raise ValueError('failure evidence differs from guard snapshot identity')
    lifecycle = result.get('lifecycle_artifacts')
    if type(lifecycle) is not dict:
        raise ValueError('failure diagnostic lacks lifecycle identities')
    for name in ('runtime-observation.json', 'keep-awake.json'):
        pin = members[name]
        if ('not_kept' not in pin) != (name in lifecycle):
            raise ValueError('failure evidence and lifecycle membership disagree')
        if name in lifecycle and lifecycle[name] != {'path': pin['path'], 'sha256': pin['sha256']}:
            raise ValueError('failure evidence and lifecycle pins disagree')
    _check_lifecycle(value, result, attempt, file, expected_runtime_observation, completion=False)
    contract.replay.validate_file_basis(value, result)
    if 'retained_artifacts' in result:
        contract.replay.validate_retained_artifacts(value, result)
    additional = result.get('additional_report')
    if additional is not None:
        if (type(additional) is not dict or additional.get('path') != str(evidence / 'attribution-replay.json')
                or additional.get('sha256') != c.sha(file(evidence / 'attribution-replay.json', 'replay report'))):
            raise ValueError('failure evidence replay report differs')
    return result


def _subscription_transcript(result, attempt):
    """Replay only the fixed transcript member of the captured final basis.

    Failed v2 runs may retain diagnostics for buffered, undelivered events.
    Their captured bytes remain evidence, never proof of a delivered prefix.
    Selecting by the file catalog also preserves the no-capture fallback and
    avoids making an editable diagnostic marker decide whether replay occurs.
    """
    files = result.get('captured_files')
    if type(files) is not dict:
        raise ValueError('saved subscription transcript lacks a captured file map')
    path = str(Path(attempt) / 'transcript.jsonl')
    if path not in files:
        if result.get('runtime_gates_passed') is True:
            raise ValueError('completed subscription replay lacks a captured transcript')
        return None
    pin = c.exact(files[path], {'bytes', 'sha256', 'roles'}, 'saved subscription transcript pin')
    size = pin['bytes']
    if (type(size) is not int or not 0 <= size <= c.HARD_LIMITS['stream_bytes']
            or type(pin['roles']) is not list or not pin['roles']
            or any(type(role) is not str or not role for role in pin['roles'])
            or sorted(set(pin['roles'])) != pin['roles']):
        raise ValueError('saved subscription transcript pin is untyped or oversized')
    from .native_shared_evidence import read_regular
    artifact = read_regular(path, 'subscription_transcript', max_bytes=max(1, size)).captured
    if artifact.pin.bytes != size or artifact.pin.sha256 != pin['sha256']:
        raise ValueError('saved subscription transcript differs from its captured pin')
    return artifact.raw


def _check_lifecycle(value, result, attempt, _file, expected_runtime_observation, *, completion):
    """Apply identical byte-based lifecycle checks to ordinary and failed readback."""
    checks = result['gates']
    lifecycle = result.get('lifecycle_artifacts')
    if (type(lifecycle) is not dict or not set(lifecycle) <= {'runtime-observation.json', 'keep-awake.json'}
            or completion and set(lifecycle) != {'runtime-observation.json', 'keep-awake.json'}):
        raise ValueError('final result lacks its runtime and cleanup identities')
    lifecycle_raw = {}
    for name, pin in lifecycle.items():
        body = _file(attempt/name, 'lifecycle artifact')
        if (type(pin) is not dict or set(pin) != {'path', 'sha256'} or pin['path'] != str(attempt/name)
                or draft._sha(body) != pin['sha256']):
            raise ValueError('runtime or cleanup evidence differs from the final identity')
        lifecycle_raw[name] = body
    runtime_gate = checks['runtime_authority']
    if 'runtime-observation.json' in lifecycle_raw:
        body = lifecycle_raw.get('runtime-observation.json')
        recomputed = lifecycle_checks.runtime_observation_result(body, result.get('runtime_observation'),
                                                     expected_runtime_observation(value))
        if draft._encoded(runtime_gate) != draft._encoded(recomputed):
            raise ValueError('runtime observation, captured authority gate and lifecycle record disagree')
    elif (runtime_gate['checked'] is not False or runtime_gate['passed'] is not False or 'basis' in runtime_gate
            or (attempt/'runtime-observation.json').exists() or (attempt/'runtime-observation.json').is_symlink()):
        raise ValueError('runtime observation fallback requires an unchecked failed gate and no artifact')
    cleanup_gate = checks['keep_awake']
    if 'keep-awake.json' in lifecycle_raw:
        recomputed = lifecycle_checks.cleanup_result(lifecycle_raw.get('keep-awake.json'),
            result.get('keep_awake'), value['runtime']['keep_awake'])
        if draft._encoded(cleanup_gate) != draft._encoded(recomputed):
            raise ValueError('cleanup evidence, observed release outcome and gate disagree')
    elif (cleanup_gate['checked'] is not False or cleanup_gate['passed'] is not False or 'basis' in cleanup_gate
            or (attempt/'keep-awake.json').exists() or (attempt/'keep-awake.json').is_symlink()):
        raise ValueError('cleanup fallback requires an unchecked failed gate and no artifact')


def read_final(registration_raw, *, contract: ExecutionContract,
               effects: ExecutionEffects):
    """Check complete publication and immutable saved identities; never resume.

    RunSpec boundary: validated-caller

    RunSpec precondition: Caller supplies exact execution-registration bytes and the fixed shared-v2 execution contract. Ordinary results reconstruct and guard a fresh RunSpec. Explicit validation-failure diagnostics verify only failed historical bytes and cannot assert completion or authority.
    """
    contract.require_fixed()
    diagnostic = _read_failure_diagnostic(registration_raw, contract=contract, file=effects.file,
        expected_runtime_observation=effects.expected_runtime_observation)
    if diagnostic is not None:
        return diagnostic
    registration, composition, authority = contract.registration, contract.composition, contract.authority
    gates, replay, shared = contract.gates, contract.replay, contract.shared
    KIND, VERSION = contract.kind, 1
    _file, durable_new, _sync_directory = effects.file, effects.durable_new, effects.sync_directory
    _mkdir_durable, _signals, _now = effects.mkdir_durable, effects.signals, effects.now
    _probe_runtime, expected_runtime_observation = effects.probe_runtime, effects.expected_runtime_observation
    authorizations, _unchanged, sys = effects.authorizations, effects.unchanged, effects.sys
    value = registration.verified(registration_raw)
    evidence, attempt = Path(value['evidence_directory']), Path(value['attempt_directory'])
    final_raw = _file(evidence/'final.json', 'final result')
    marker = draft._json(_file(evidence/'published.json', 'publication marker'))
    started_raw = _file(attempt/'started.json', 'started identity')
    expected = {'final_sha256': draft._sha(final_raw),
        'started_sha256': draft._sha(started_raw),
        'registration_sha256': draft._sha(registration_raw)}
    if draft._encoded(marker) != draft._encoded(expected):
        raise ValueError('final publication is incomplete or changed')
    result = draft._json(final_raw)
    if (type(result) is not dict or result.get('kind') != KIND or type(result.get('version')) is not int
            or result['version'] != VERSION or result.get('attempt_id') != value['attempt_id']
            or result.get('composition_sha256') != value['composition_sha256']
            or result.get('registration_sha256') != expected['registration_sha256']
            or result.get('started_sha256') != expected['started_sha256']
            or _file(attempt/'registration.json', 'consumed registration') != registration_raw
            or any(result.get(k) != v for k, v in UNASSESSED.items())):
        raise ValueError('final identity or scope differs from this consumed native attempt')
    _saved_authorizations(registration_raw, value, started_raw, result, contract=contract, file=_file)
    if 'subscription_guard' not in result:
        raise ValueError('shared v2 result requires its saved subscription snapshot')
    if 'subscription_guard' in result:
        from .native_subscription_admission import context
        guard_reading = result['subscription_guard']
        guard_raw = _file(attempt/'subscription-guard.json', 'saved subscription guard')
        guard_module, guard_extra = context(guard_raw, registration_raw=registration_raw,
            runtime=value['runtime'], launch_word_raw=_file(attempt/'launch_word.json', 'consumed owner word'),
            review_bundle_raw=_file(attempt/'review.json', 'consumed review'))
        validate_saved_snapshot = guard_module.validate_saved_snapshot
        validate_saved_observations = guard_module.validate_saved_observations
        if (type(guard_reading) is not dict
                or guard_reading.get('guard_sha256') != draft._sha(guard_raw)
                or guard_reading.get('registration_sha256') != expected['registration_sha256']):
            raise ValueError('saved subscription guard identity differs')
        validate_saved_snapshot(guard_raw, guard_reading,
            registration_raw=registration_raw, runtime=value['runtime'],
            launch_word_raw=_file(attempt/'launch_word.json', 'consumed owner word'), **guard_extra)
        dispatch_path = attempt/'subscription-dispatched.json'
        if dispatch_path.exists() or dispatch_path.is_symlink():
            dispatch = draft._json(_file(dispatch_path, 'saved subscription dispatch'))
            if dispatch != {'guard_sha256': draft._sha(guard_raw), 'consumed': True}:
                raise ValueError('saved subscription dispatch differs')
            consumed = True
        else:
            consumed = False
        if guard_reading['dispatched'] is not consumed:
            raise ValueError('saved subscription dispatch state differs')
        if result.get('runtime_gates_passed') is True and guard_reading['dispatched'] is not True:
            raise ValueError('completed native attempt lacks consumed subscription dispatch')
        transcript_raw = _subscription_transcript(result, attempt)
        observation_verification = validate_saved_observations(guard_raw, guard_reading,
            registration_raw=registration_raw, runtime=value['runtime'],
            launch_word_raw=_file(attempt/'launch_word.json', 'consumed owner word'),
            transcript_raw=transcript_raw, complete=result.get('runtime_gates_passed') is True, **guard_extra)
        if result.get('subscription_observation_verification') != observation_verification:
            raise ValueError('saved subscription observation verification differs from replay')
    checks = result.get('gates')
    if (type(checks) is not dict or set(checks) != set(GATES)
            or any(type(row) is not dict or type(row.get('checked')) is not bool or type(row.get('passed')) is not bool
                   for row in checks.values())):
        raise ValueError('final result lacks all strict runtime gates')
    completion = all(row['checked'] and row['passed'] for row in checks.values())
    if (type(result.get('runtime_gates_passed')) is not bool or result['runtime_gates_passed'] != completion
            or result.get('state') != ('completed_pending_independent_review' if completion else 'failed')
            or (completion and result.get('first_stop') is not None)):
        raise ValueError('final completion contradicts required gates or sticky failure')
    files, aliases, metadata = result.get('captured_files'), result.get('captured_aliases'), result.get('captured_metadata')
    if not all(type(v) is dict for v in (files, aliases, metadata)) or not set(files) <= set(metadata) or not set(aliases.values()) <= set(metadata):
        raise ValueError('final evidence lacks complete captured metadata')
    origin_raw = {}
    origin_paths = ()
    if 'receipt_origin_reporting' in value:
        from .native_receipt_origin import required_paths
        origin_paths = required_paths(value, checks['receipts'], aliases)
    elif 'receipt_origin' in checks['receipts']:
        raise ValueError('undeclared receipt-origin gate extension')
    if KIND == 'd4d_native_shared_attempt':
        if origin_paths:
            origin_raw = replay.validate_file_basis(value, result, retain_paths=origin_paths)
        else:
            replay.validate_file_basis(value, result)
    elif origin_paths:
        for path, pin in files.items():
            body = Path(path).read_bytes()
            if draft._sha(body) != pin['sha256']:
                raise ValueError('saved evidence differs from the captured basis')
            if path in origin_paths:
                origin_raw[path] = body
    else:
        for path, pin in files.items():
            if draft._sha(Path(path).read_bytes()) != pin['sha256']:
                raise ValueError('saved evidence differs from the captured basis')
    for alias, target in aliases.items():
        if (str(Path(alias).resolve()) != target
                or result.get('captured_alias_metadata', {}).get(alias) != {'symlink': Path(alias).is_symlink()}):
            raise ValueError('saved evidence alias identity changed')
    for path, expected_meta in metadata.items():
        try:
            info = Path(path).stat()
            actual = {'exists': True, 'regular': stat.S_ISREG(info.st_mode), 'links': info.st_nlink,
                'device': info.st_dev, 'inode': info.st_ino, 'size': info.st_size, 'mtime_ns': info.st_mtime_ns}
        except FileNotFoundError:
            actual = {'exists': False, 'regular': False}
        if actual != expected_meta:
            raise ValueError('saved evidence file metadata changed')
    if 'receipt_origin_reporting' in value:
        from .native_receipt_origin import check_saved
        check_saved(value, checks['receipts'], raw=origin_raw, aliases=aliases, metadata=metadata)
    _check_lifecycle(value, result, attempt, _file, expected_runtime_observation, completion=completion)
    additional = result.get('additional_report')
    if additional is None:
        if completion:
            raise ValueError('completed native attempt lacks its generated replay report')
    else:
        path = evidence/'attribution-replay.json'
        if (type(additional) is not dict or set(additional) != {'path', 'sha256'} or additional['path'] != str(path)
                or draft._sha(_file(path, 'generated replay report')) != additional['sha256']):
            raise ValueError('generated replay report differs from its final identity')
    contract.check_additional_readback(value, result)
    return result
