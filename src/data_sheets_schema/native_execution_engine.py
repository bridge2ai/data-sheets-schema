"""Private single-attempt lifetime shared by two fixed native facades.

Contracts are package-owned Python bindings, never selected by serialized import
names. This module owns reservation, signals, cleanup, sticky failure, strict
aggregation and publication; selected adapters supply semantic reconstruction.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import stat
import threading
from types import ModuleType
from typing import Callable

from data_sheets_schema import native_attribution_registration as draft
from data_sheets_schema import native_execution_gates as lifecycle_checks

GATES = ('terminal', 'shutdown', 'first_stop', 'live_attribution', 'saved_attribution',
         'phase_history', 'tool_history', 'schema', 'pair', 'receipts', 'evidence',
         'observation', 'accounting', 'runtime_authority', 'keep_awake')
UNASSESSED = {'scientific_acceptance': 'not_assessed', 'provider_billing': 'not_verified',
              'evidence_authentication': 'not_cryptographically_authenticated'}


REQUIRED_CHECKS = tuple(f'Python 3.12 / shard {n}' for n in range(1, 7)) + (
    'Python 3.12 / offline audit and finalization', 'Python 3.12 / offline evaluation', 'test', 'large-files')

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
            'd4d_native_attribution_attempt': (
                'native_execution_registration', 'native_attribution_controller',
                'native_execution_authority', 'native_execution_gates',
                'native_attribution_results', 'native_supervisor_gates'),
            'd4d_native_shared_attempt': (
                'native_shared_registration', 'native_shared_controller',
                'native_execution_authority', 'native_shared_gates',
                'native_shared_results', 'native_shared_results'),
        }.get(self.kind)
        modules = (self.registration, self.composition, self.authority,
                   self.gates, self.replay, self.shared)
        if names is None or any(type(module) is not ModuleType or
                module.__name__ != 'data_sheets_schema.' + name
                for module, name in zip(modules, names)):
            raise ValueError('native engine requires a fixed package execution contract')
        if tuple(self.gates.GATES) != GATES:
            raise ValueError('native execution contract must retain all original runtime obligations')

    def make_controller(self, value, registration_raw):
        raw = value['composition_raw_json'].encode()
        if self.kind == 'd4d_native_attribution_attempt':
            return self.composition.CallbackAdapter(raw)
        return self.composition.CallbackAdapter(raw, execution=value,
                                                registration_raw=registration_raw)

    def transport_phase_spec(self, adapter):
        if self.kind == 'd4d_native_attribution_attempt':
            return adapter.spec
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


def authorizations(raw, value, *, review_path, ci_path, launch_word_path, contract, file):
    """Check exact saved external declarations; this performs no web discovery.

    The artifacts are caller-supplied review/CI/owner evidence, not signatures.
    A matching hash does not authenticate their author or GitHub's service.
    """
    contract.require_fixed()
    registration, composition = contract.registration, contract.composition
    _file = file
    inputs = {name: str(Path(path).absolute()) for name, path in {
        'review': review_path, 'ci': ci_path, 'launch_word': launch_word_path}.items()}
    captured = {name: _file(path, name + ' evidence') for name, path in inputs.items()}
    records = {name: draft._json(body) for name, body in captured.items()}
    binding = {'registration_sha256': draft._sha(raw), 'attempt_id': value['attempt_id'],
               'source_commit': value['dependencies']['base']['source_commit'],
               'dependencies_sha256': draft._sha(draft._encoded(value['dependencies']))}
    for name, item in records.items():
        if not isinstance(item, dict) or any(item.get(key) != val for key, val in binding.items()):
            raise ValueError(f'{name} is not bound to this exact registration, attempt and source closure')
        if type(item.get('version')) is not int or item['version'] != 1:
            raise ValueError(f'{name} has no supported exact version')
    review = records['review']
    registration._closed(review, set(binding) | {'kind', 'version', 'reviewer', 'author',
        'independent', 'decision', 'reviewed_at', 'evidence'}, 'independent review')
    if (review['kind'] != 'd4d_native_execution_review' or review['independent'] is not True
            or review['decision'] != 'approved' or review['reviewer'] == review['author']):
        raise ValueError('explicit independent approval is required')
    for key in ('reviewer', 'author', 'reviewed_at', 'evidence'):
        registration._text(review[key], 'review ' + key)
    ci = records['ci']
    registration._closed(ci, set(binding) | {'kind', 'version', 'checks'}, 'CI evidence')
    if ci['kind'] != 'd4d_native_execution_ci' or type(ci['checks']) is not dict or set(ci['checks']) != set(REQUIRED_CHECKS):
        raise ValueError('exact full required CI evidence is missing')
    for name, row in ci['checks'].items():
        registration._closed(row, {'head_sha', 'status', 'conclusion', 'details_url'}, 'CI check')
        if (row['head_sha'] != binding['source_commit'] or row['status'] != 'completed'
                or row['conclusion'] != 'success'):
            raise ValueError(f'required CI check is not successful at the exact source: {name}')
        if not isinstance(row['details_url'], str) or not row['details_url'].startswith('https://github.com/bridge2ai/data-sheets-schema/actions/'):
            raise ValueError('CI evidence requires its explicit repository check URL')
    launch = records['launch_word']
    registration._closed(launch, set(binding) | {'kind', 'version', 'owner', 'authorized_at',
        'word', 'review_sha256', 'ci_sha256', 'permission_probe_sha256'}, 'owner launch evidence')
    if (launch['kind'] != 'd4d_native_execution_launch_authorization'
            or launch['word'] != 'AUTHORIZE_ONE_NATIVE_ATTEMPT'
            or launch['review_sha256'] != draft._sha(captured['review'])
            or launch['ci_sha256'] != draft._sha(captured['ci'])
            or launch['permission_probe_sha256'] != value['permission_probe_sha256']):
        raise ValueError('owner launch evidence does not authorize this exact one-use attempt')
    registration._text(launch['owner'], 'authorizing owner')
    registration._text(launch['authorized_at'], 'owner authorization time')
    selected = composition.verified_composition(value['composition_raw_json'].encode())
    registration._paths(value, selected, fresh=False, extra_protected=list(inputs.values()))
    return {'inputs': inputs, 'raw': captured, 'records': records, 'binding': binding,
            'identity': {name: {'path': inputs[name], 'sha256': draft._sha(body)} for name, body in captured.items()}}


def launch(registration_raw, *, review_path, ci_path, launch_word_path,
           contract: ExecutionContract, effects: ExecutionEffects):
    """Consume one explicitly authorized native attempt, never retry or resume.

    This method can invoke the selected native executable. Calling it is a
    separate action from preparation; there is no inferred model or live value.
    """
    contract.require_fixed()
    registration, composition, authority = contract.registration, contract.composition, contract.authority
    gates, replay, shared = contract.gates, contract.replay, contract.shared
    KIND, VERSION = contract.kind, 1
    _file, durable_new, _sync_directory = effects.file, effects.durable_new, effects.sync_directory
    _mkdir_durable, _signals, _now = effects.mkdir_durable, effects.signals, effects.now
    _probe_runtime, expected_runtime_observation = effects.probe_runtime, effects.expected_runtime_observation
    authorizations, _unchanged, sys = effects.authorizations, effects.unchanged, effects.sys
    value = registration.verified(registration_raw)
    authorization = authorizations(registration_raw, value, review_path=review_path,
                                  ci_path=ci_path, launch_word_path=launch_word_path)
    _unchanged(value, registration_raw, authorization)
    runtime_identity = expected_runtime_observation(value)
    selected = composition.verified_composition(value['composition_raw_json'].encode())
    attempt, evidence, *outputs = registration._paths(value, selected, fresh=True,
        extra_protected=list(authorization['inputs'].values()))
    if threading.current_thread() is not threading.main_thread():
        raise ValueError('native launch requires the main thread')
    attempt.mkdir(mode=0o700)  # Even a partial reservation consumes the identity.
    _sync_directory(attempt.parent)
    durable_new(attempt/'registration.json', registration_raw)
    started = {'kind': KIND, 'version': VERSION, 'state': 'started', 'attempt_id': value['attempt_id'],
        'started_at': _now(), 'registration_sha256': draft._sha(registration_raw),
        'composition_sha256': value['composition_sha256'], 'authority': authorization['identity'],
        'dispatch_limit': 1, 'dispatch_unit': 'native CLI process, not provider transactions', **UNASSESSED}
    started_raw = draft._encoded(started)
    durable_new(attempt/'started.json', started_raw)
    evidence.mkdir(mode=0o700)
    _sync_directory(evidence.parent)
    for name, body in authorization['raw'].items():
        durable_new(attempt/(name + '.json'), body)
    status = first_stop = prepared = first_error = None
    signals = []
    observation = {'checked': False, 'passed': False, 'reason': 'native runtime not observed'}
    awake = {'passed': False, 'policy': value['runtime']['keep_awake'], 'state': 'not_acquired'}
    adapter = contract.make_controller(value, registration_raw)
    additional_path = evidence/'attribution-replay.json'
    results = {name: {'checked': False, 'passed': False, 'reason': 'capture unavailable'} for name in GATES}
    def stopped(message):
        nonlocal first_stop
        if first_stop is None:
            first_stop = str(message)
    with authority.loaded_dependencies(value['dependencies']) as controls, _signals(signals):
        proxy = controls['run_direct_canary'].NoProxy()
        guard = None
        try:
            try:
                for directory in outputs:
                    _mkdir_durable(directory)
                _mkdir_durable(attempt/'cli_config')
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
                    if (_file(attempt/'registration.json', 'consumed registration') != registration_raw
                            or _file(attempt/'started.json', 'started identity') != started_raw
                            or _file(attempt/'runtime-observation.json', 'runtime observation') != draft._encoded(observation)
                            or proxy.closed or proxy.failed.is_set()):
                        raise ValueError('native admission is closed or consumed identity changed')
                    contract.activate_before_dispatch(adapter, started_raw)
                status = controls['run_native_canary'].execute_child(value['argv'], proxy=proxy,
                    instruction=Path(selected['instruction_path']), attempt=attempt,
                    cwd=value['working_directory'], env=value['environment'],
                    deadline_seconds=value['runtime']['deadline_seconds'], verify_launch=launch_check,
                    record_stop=stopped, command_policy=adapter.policy, phase_spec=contract.transport_phase_spec(adapter),
                    command_classifier=adapter.classify, event_observer=adapter.observe)
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
                    prepared = gates.capture(value, controls, authority_inputs=authority_inputs,
                                             registration_raw=registration_raw)
                except Exception as exc:
                    if first_error is None:
                        first_error = exc
                    problem = f'capture: {type(exc).__name__}: {exc}'
                    stopped(problem)
                    prepared = shared.incomplete_capture(value['composition'], attempt, adapter, problem)
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
                    controls, exit_code=status, shutdown=getattr(proxy, 'control_shutdown', None),
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
            completed = (set(results) == set(GATES)
                and all(row.get('checked') is True and row.get('passed') is True for row in results.values()))
            final = {'kind': KIND, 'version': VERSION, 'attempt_id': value['attempt_id'],
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
            final_raw = draft._encoded(final)
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



def read_final(registration_raw, *, contract: ExecutionContract,
               effects: ExecutionEffects):
    """Check complete publication and immutable saved identities; never resume."""
    contract.require_fixed()
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
    expected = {'final_sha256': draft._sha(final_raw),
        'started_sha256': draft._sha(_file(attempt/'started.json', 'started identity')),
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
    if KIND == 'd4d_native_shared_attempt':
        replay.validate_file_basis(value, result)
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
