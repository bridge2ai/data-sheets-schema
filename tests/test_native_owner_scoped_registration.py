"""Complete offline C/E reconstruction in actual original/borrowed scopes.

Permission observations and the clock backend are explicit software fixtures.
No registration, permission verifier, capture or committed-source proof is
substituted. Only local Git subprocesses are allowed; no attempt is launched.
"""
from contextlib import contextmanager
from contextvars import copy_context
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import subprocess
import sys
import threading
import time
from types import SimpleNamespace

import pytest

from data_sheets_schema import native_attribution_controller as inherited
from data_sheets_schema import native_clock_domain_v1 as clocks
from data_sheets_schema import native_execution_authority as authority
from data_sheets_schema import native_owner_profile_v1 as profile
from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_controller as composition
from data_sheets_schema import native_shared_execution as execution
from data_sheets_schema import native_shared_policy as policy
from data_sheets_schema import native_shared_registration as registration
from data_sheets_schema import native_subscription_guard as subscription_guard
from data_sheets_schema import native_stream_coordination_v1 as coordination
from tests.test_native_shared_controller import bound, native_spec, declaration
from tests.test_native_shared_permissions import fabricated_manifest
from tests.test_native_owner_runner import fixed_clock, selected_controls


_SUBPROCESS = {name: getattr(subprocess, name) for name in ('run', 'Popen', 'check_output')}


@pytest.fixture
def offline_bound(bound, monkeypatch):
    """Use real selected S/R/rendering, with local Git as the sole process."""
    bound_spec, bound_runtime_path, bound_instruction = bound
    # #4731: bound has already rendered its cached instruction. A new runtime
    # needs a fresh spec and separate files, preserving the original fixture.
    spec = replace(bound_spec)
    assert 'instruction' not in spec.__dict__
    original_runtime = bound_runtime_path.read_bytes()
    original_instruction = bound_instruction.read_bytes()
    runtime_path = bound_runtime_path.with_name('scoped-runtime.json')
    instruction = bound_instruction.with_name('scoped-instruction.md')
    calls = []
    for name, real in _SUBPROCESS.items():
        def git_only(argv, *args, _real=real, **kwargs):
            assert isinstance(argv, (list, tuple)) and argv[0] == 'git', (
                'native/auth/provider subprocess forbidden', argv)
            calls.append(tuple(argv))
            return _real(argv, *args, **kwargs)
        monkeypatch.setattr(subprocess, name, git_only)
    # _unchanged_in_scope checks the actual host declaration. This is still a
    # never-invoked executable, not a native observation or keep-awake request.
    runtime = c.strict_json(original_runtime)
    runtime['keep_awake'] = {'policy': 'not_applicable', 'host_platform': sys.platform,
                            'basis': 'Explicit offline source/byte-recheck fixture only.'}
    runtime_path.write_bytes(c.canonical(runtime))
    composition.bind_runtime(spec, runtime_path, 3)
    instruction.write_bytes(spec.instruction.encode('utf-8'))
    assert bound_runtime_path.read_bytes() == original_runtime
    assert bound_instruction.read_bytes() == original_instruction
    return {'spec': spec, 'runtime_path': runtime_path, 'instruction_path': instruction,
            'max_draft_checks': 3, 'git_calls': calls}


def compose_args(case):
    return {key: case[key] for key in ('runtime_path', 'instruction_path', 'max_draft_checks')}


def prepare_execution(case, root, selected, dependencies):
    """Saved fabricated observations pass the real complete permission proof."""
    root.mkdir()
    comp = root / 'composition.json'
    comp.write_bytes(c.canonical(selected))
    system = root / 'system.txt'
    system.write_bytes(b'Explicit software reconstruction fixture only.\n')
    attempt, output = root / 'attempt', root / 'evidence'
    expected = registration.permission_expectation(
        c.strict_json(case['runtime_path'].read_bytes()), selected, case['spec'],
        system.read_text() + policy.command_guidance(selected['policy']),
        attempt / 'cli_config', dependencies)
    saved = fabricated_manifest(expected,
        case['spec']._native_shared_generation_capture.document(),
        root / 'fabricated-permission-records', case['spec'].bundle.read_bytes())
    probe = root / 'fabricated-permission.json'
    probe.write_bytes(c.canonical(saved))
    args = {'composition_path': comp, 'system_path': system, 'permission_probe_path': probe,
            'attempt_id': 'attempt', 'attempt_directory': attempt,
            'evidence_directory': output, 'max_draft_checks': 3}
    # This is only the existing _unchanged byte-recheck input shape. These
    # invented bytes are never passed off as actual review/CI/launch approvals.
    inputs, raw = {}, {}
    for name in ('review', 'ci', 'launch'):
        inputs[name] = root / (name + '-byte-precondition.json')
        raw[name] = c.canonical({'fixture': name, 'execution_authorized': False})
        inputs[name].write_bytes(raw[name])
    return {**case, 'composition': selected, 'composition_raw': comp.read_bytes(),
            'dependencies': dependencies, 'expected_permission': expected,
            'args': args, 'authorization': {'inputs': inputs, 'raw': raw}}


@pytest.fixture
def scoped_case(offline_bound, fixed_clock, tmp_path):
    dependencies = authority.dependency_identity(stream_snapshot_profile=1)
    with authority.loaded_dependencies(dependencies) as controls:
        selected = composition._compose_in_scope(offline_bound['spec'],
            **compose_args(offline_bound), profile=dependencies['stream_snapshot_profile'])
        case = prepare_execution(offline_bound, tmp_path.resolve() / 'selected-execution',
                                 selected, dependencies)
        case.update(controls=controls, parent=profile._ACTIVE.get(),
                    profile=deepcopy(dependencies['stream_snapshot_profile']))
        value = registration._registration_in_scope(**case['args'])
        case.update(value=value, raw=c.canonical(value))
        yield case


@contextmanager
def no_nested_loaders(monkeypatch, controls):
    """Trap the real global loader seams; do not replace reconstruction."""
    original_path = list(sys.path)
    original_modules = {name: sys.modules.get(name) for name in controls}
    def forbidden(*args, **kwargs):
        pytest.fail('selected reconstruction entered a global loader')
    with monkeypatch.context() as patch:
        patch.setattr(authority, 'loaded_dependencies', forbidden)
        patch.setattr(inherited, 'load_controls', forbidden)
        yield
    assert list(sys.path) == original_path
    assert all(sys.modules.get(name) is member for name, member in original_modules.items())


def in_thread(operation, *, context=None):
    values, errors = [], []
    def run():
        try:
            values.append(operation() if context is None else context.run(operation))
        except BaseException as error:
            errors.append(error)
    worker = threading.Thread(target=run)
    worker.start()
    worker.join(90)
    assert not worker.is_alive(), 'bounded offline reconstruction worker did not finish'
    if errors:
        raise errors[0]
    assert len(values) == 1
    return values[0]


def require_no_reservation(case):
    assert not case['args']['attempt_directory'].exists()
    assert not case['args']['evidence_directory'].exists()
    selection = c.parse_selection(case['composition']['selection_raw_json'].encode())
    assert not Path(selection['stage_root']).exists()


def test_default_omitted_and_exact_zero_keep_real_composition_and_execution(offline_bound, tmp_path):
    case = offline_bound
    omitted = composition.compose(case['spec'], **compose_args(case))
    zero = composition.compose(case['spec'], **compose_args(case), stream_snapshot_profile=0)
    assert c.canonical(omitted) == c.canonical(zero)
    assert 'stream_snapshot_profile' not in omitted
    assert composition.verified_composition(c.canonical(omitted)) == omitted
    for invalid in (False, True, 0.0, 1, 2, None, '0'):
        with pytest.raises(ValueError):
            composition.compose(case['spec'], **compose_args(case), stream_snapshot_profile=invalid)
    prepared = prepare_execution(case, tmp_path.resolve() / 'default-execution',
                                 omitted, authority.dependency_identity())
    value = registration.registration(**prepared['args'])
    assert value['dependencies']['version'] == 1
    assert 'stream_snapshot_profile' not in value['dependencies']
    assert registration.verified(c.canonical(value)) == value
    require_no_reservation(prepared)


def test_complete_selected_reconstruction_in_original_and_real_borrowed_scope(
        scoped_case, fixed_clock, monkeypatch):
    case = scoped_case
    parent = case['parent']
    assert parent._parent is None and coordination.current_reader_budget() is None
    with no_nested_loaders(monkeypatch, case['controls']):
        assert composition._verified_composition_in_scope(case['composition_raw']) == case['composition']
        assert registration._verified_in_scope(case['raw']) == case['value']
        before = len(case['git_calls'])
        assert execution._unchanged_in_scope(case['value'], case['raw'], case['authorization']) is None
        proof_calls = case['git_calls'][before:]
        assert any('--no-replace-objects' in argv and 'ls-tree' in argv for argv in proof_calls)
        assert any('--no-replace-objects' in argv and 'cat-file' in argv for argv in proof_calls)
    assert case['value']['dependencies'] == case['dependencies']
    assert case['value']['dependencies']['stream_snapshot_profile'] == case['profile']
    assert case['value']['runtime_declaration_sha256'] == case['composition']['runtime_sha256']
    assert case['value']['permission_expected_sha256'] == c.sha(c.canonical(case['expected_permission']))
    assert case['value']['permission_observations']['checked'] is True
    assert case['value']['permission_observations']['passed'] is True
    # This is a bounded offline reconstruction worker, not a claim that a
    # real two-second classifier callback has completed this whole operation.
    owner = coordination.ReaderBudget(time.monotonic_ns() + 120_000_000_000,
        (threading.Event(), threading.Event()), clock_domain=fixed_clock)
    def borrowed():
        assert profile._ACTIVE.get() is None
        budget = coordination.ReaderBudget(owner.deadline_ns - 30_000_000_000,
            owner.stop_events, clock_domain=owner.clock_domain())
        with coordination.reader_budget(budget) as reader_scope:
            with profile._worker_scope(parent, owner) as worker:
                with no_nested_loaders(monkeypatch, case['controls']):
                    # #4732: require_current must reobserve the domain through
                    # temporary leases; the worker's retained scope stays fixed.
                    retained_lease = reader_scope._lease
                    deadline, events = budget.deadline_ns, budget.stop_events
                    real_capture = clocks.capture_domain
                    observations = []
                    def observe_domain():
                        lease = real_capture()
                        observations.append(lease)
                        return lease
                    def no_new_reader_scope(*args, **kwargs):
                        pytest.fail('reconstruction renewed the reader budget scope')
                    def assert_retained():
                        assert coordination._SCOPE.get() is reader_scope
                        assert coordination.current_reader_budget() is budget
                        assert reader_scope.budget is budget
                        assert reader_scope._lease is retained_lease
                        assert not retained_lease._closed
                        assert budget.deadline_ns == deadline
                        assert budget.stop_events is events
                        assert all(a is b for a, b in zip(events, owner.stop_events))
                    assert_retained()
                    with monkeypatch.context() as patch:
                        patch.setattr(clocks, 'capture_domain', observe_domain)
                        patch.setattr(coordination, 'reader_budget', no_new_reader_scope)
                        patch.setattr(coordination._ReaderScope, '__enter__', no_new_reader_scope)
                        assert composition._verified_composition_in_scope(case['composition_raw']) == case['composition']
                        assert_retained()
                        assert registration._verified_in_scope(case['raw']) == case['value']
                        assert_retained()
                    assert observations
                    assert all(lease is not retained_lease and lease._closed for lease in observations)
                assert worker is profile._ACTIVE.get() and worker._parent is parent
                assert worker.controls is case['controls'] and worker._budget is budget
                assert budget.deadline_ns < owner.deadline_ns
                assert all(a is b for a, b in zip(budget.stop_events, owner.stop_events))
                for factory in (profile.bind_control, profile.bind_runner):
                    with pytest.raises(ValueError):
                        factory(case['profile'], case['controls'])
            assert not worker.live and profile._ACTIVE.get() is None
        return worker
    worker = in_thread(borrowed)
    assert worker._creator is not threading.current_thread()
    assert profile._ACTIVE.get() is parent
    parent.require()
    require_no_reservation(case)


def test_complete_selected_mutants_recheck_real_inputs_and_authorization(scoped_case, monkeypatch):
    case = scoped_case
    def default_composition_in_selected_execution(value):
        document = c.strict_json(value['composition_raw_json'].encode())
        document.pop('stream_snapshot_profile')
        raw = c.canonical(document)
        value.update(composition_raw_json=raw.decode(), composition_sha256=c.sha(raw))
    c_mutants = {
        'extra composition field': lambda v: v.update(unreviewed=True),
        'boolean version': lambda v: v.update(version=True),
        'float allowance': lambda v: v.update(max_draft_checks=3.0),
        'missing profile': lambda v: v.pop('stream_snapshot_profile'),
        'null profile': lambda v: v.update(stream_snapshot_profile=None),
        'foreign profile': lambda v: v['stream_snapshot_profile']['implementations']['control'].update(sha256='0' * 64),
        'runtime byte pin': lambda v: v.update(runtime_sha256='0' * 64),
        'altered policy with new pin': lambda v: (
            v['policy']['native_shared_helpers'].update(draft=v['policy']['native_shared_helpers']['draft']+' --foreign'),
            v.update(policy_sha256=c.sha(c.canonical(v['policy'])))),
    }
    e_mutants = {
        'extra execution field': lambda v: v.update(unreviewed=True),
        'boolean execution version': lambda v: v.update(version=True),
        'float execution allowance': lambda v: v.update(max_draft_checks=3.0),
        'default dependencies in selected E': lambda v: (
            v['dependencies'].update(version=1), v['dependencies'].pop('stream_snapshot_profile')),
        'default C embedded in selected E': default_composition_in_selected_execution,
        'runtime declaration join': lambda v: v.update(runtime_declaration_sha256='0' * 64),
        'embedded runtime differs': lambda v: v['runtime'].update(deadline_seconds=v['runtime']['deadline_seconds']+1),
        'permission expectation pin': lambda v: v.update(permission_expected_sha256='0' * 64),
        'false permission conclusion': lambda v: v['permission_observations'].update(passed=False),
        'changed argv': lambda v: v['argv'].append('--unregistered'),
    }
    with no_nested_loaders(monkeypatch, case['controls']):
        assert registration._verified_in_scope(case['raw']) == case['value']
        supplied = deepcopy(case['profile'])
        original_policy = policy.command_policy
        def mutating_policy(*args, **kwargs):
            result = original_policy(*args, **kwargs)
            supplied['implementations']['control']['sha256'] = '0' * 64
            return result
        # #4730: the real constructor has already admitted its profile when
        # actual policy composition mutates the same caller-owned declaration.
        with monkeypatch.context() as patch:
            patch.setattr(policy, 'command_policy', mutating_policy)
            with pytest.raises(ValueError):
                composition._compose_in_scope(case['spec'], **compose_args(case), profile=supplied)
        assert c.canonical(supplied) != c.canonical(case['profile'])
        assert composition._verified_composition_in_scope(case['composition_raw']) == case['composition']
        for label, mutate in c_mutants.items():
            value = deepcopy(case['composition']); mutate(value)
            raw = c.canonical(value)
            assert raw != case['composition_raw'], label
            with pytest.raises(ValueError):
                composition._verified_composition_in_scope(raw)
        for label, mutate in e_mutants.items():
            value = deepcopy(case['value']); mutate(value)
            raw = c.canonical(value)
            assert raw != case['raw'], label
            with pytest.raises(ValueError):
                registration._verified_in_scope(raw)
        # Changed on-disk authorities are actual files, not substituted readers.
        for label, path in (
                ('composition', case['args']['composition_path']),
                ('runtime', case['runtime_path']),
                ('system', case['args']['system_path']),
                ('saved permissions', case['args']['permission_probe_path'])):
            raw = path.read_bytes()
            try:
                if label == 'composition':
                    doc = c.strict_json(raw); doc.pop('stream_snapshot_profile')
                elif label == 'runtime':
                    doc = c.strict_json(raw); doc['deadline_seconds'] += 1
                elif label == 'saved permissions':
                    doc = c.strict_json(raw, max_bytes=c.HARD_LIMITS['permission_wire_bytes'])
                    doc['binding']['commands']['draft'] += ' --unregistered'
                else:
                    doc = None
                changed = c.canonical(doc) if doc is not None else raw + b'Changed fixture instructions.\n'
                assert changed != raw
                path.write_bytes(changed)
                with pytest.raises(ValueError):
                    registration._verified_in_scope(case['raw'])
            finally:
                path.write_bytes(raw)
        for name, path in case['authorization']['inputs'].items():
            raw = path.read_bytes()
            try:
                path.write_bytes(raw + b'Changed authority bytes.\n')
                with pytest.raises(ValueError, match='launch authority changed'):
                    execution._unchanged_in_scope(case['value'], case['raw'], case['authorization'])
            finally:
                path.write_bytes(raw)
    require_no_reservation(case)


def test_public_selected_discriminators_and_mixed_routes_refuse_before_dispatch(scoped_case, monkeypatch):
    case = scoped_case
    def forbidden(*args, **kwargs):
        pytest.fail('selected registration reached public launch effects')
    with no_nested_loaders(monkeypatch, case['controls']):
        with monkeypatch.context() as patch:
            patch.setattr(execution, '_probe_runtime', forbidden)
            patch.setattr(execution, 'authorizations', forbidden)
            patch.setattr(subscription_guard, 'load_guard', forbidden)
            for profile_value in (case['profile'], None, False, {}, {'version': 1}):
                value = deepcopy(case['composition'])
                value['stream_snapshot_profile'] = deepcopy(profile_value)
                with pytest.raises(ValueError):
                    composition.verified_composition(c.canonical(value))
            mixed = deepcopy(case['value'])
            mixed['dependencies'].update(version=1)
            mixed['dependencies'].pop('stream_snapshot_profile')
            assert c.canonical(mixed) != case['raw']
            for value in (case['value'], mixed, {**case['value'], 'dependencies': {
                    **case['dependencies'], 'version': True}}):
                with pytest.raises(ValueError):
                    registration.verified(c.canonical(value))
            with pytest.raises(ValueError):
                execution._unchanged(case['value'], case['raw'], case['authorization'])
            with pytest.raises(ValueError):
                execution.launch(case['raw'], review_path=case['authorization']['inputs']['review'],
                    ci_path=case['authorization']['inputs']['ci'],
                    launch_word_path=case['authorization']['inputs']['launch'],
                    subscription_guard_path=case['args']['attempt_directory'] / 'unread-guard.json',
                    subscription_guard_sha256='0' * 64)
            with pytest.raises(ValueError):
                registration.registration(**case['args'])
        # A copied map is not an accepted caller extension to these fixed APIs.
        with pytest.raises(TypeError):
            composition._compose_in_scope(case['spec'], **compose_args(case),
                profile=case['profile'], controls=dict(case['controls']))
        with pytest.raises(TypeError):
            registration._registration_in_scope(**case['args'], controls=dict(case['controls']))
        # Even the shared implementation seam admits only the map yielded by
        # its own fixed current-scope check, not an equal copied dictionary.
        with pytest.raises(ValueError, match='exact current controls'):
            registration._registration(**case['args'], receipt_origin_version=0,
                                       controls=dict(case['controls']))
    require_no_reservation(case)


def test_fresh_verified_capture_keeps_value_api_and_reconstructs_composition_once(scoped_case, monkeypatch):
    case = scoped_case
    original = registration._selection_in_scope
    calls = []

    def selection(raw):
        calls.append(raw)
        return original(raw)

    monkeypatch.setattr(registration, '_selection_in_scope', selection)
    value, selected, spec, doc, runtime = registration._verified_capture_in_scope(case['raw'])
    assert calls == [case['composition_raw']]
    assert value == case['value'] and selected == case['composition']
    assert doc == c.parse_selection(selected['selection_raw_json'].encode())
    assert spec.render_spec() == selected['render_spec']
    assert runtime == value['runtime']
    registration._recheck_selected_capture(selected, spec, doc, runtime)
    assert calls == [case['composition_raw']]
    assert registration._verified_in_scope(case['raw']) == value
    require_no_reservation(case)


def test_same_capture_endpoint_recheck_reads_current_bundle_runtime_binary_and_instruction(scoped_case):
    case = scoped_case
    _, selected, spec, doc, runtime = registration._verified_capture_in_scope(case['raw'])
    paths = [Path(spec.bundle), case['runtime_path'], case['instruction_path'],
             Path(runtime['executable']['path'])]
    for path in paths:
        raw = path.read_bytes()
        try:
            path.write_bytes(raw + b'\nchanged after verified reconstruction\n')
            with pytest.raises(ValueError):
                registration._recheck_selected_capture(selected, spec, doc, runtime)
        finally:
            path.write_bytes(raw)
        registration._recheck_selected_capture(selected, spec, doc, runtime)
    require_no_reservation(case)


def test_same_capture_endpoint_recheck_keeps_current_toolchain_and_controller(scoped_case, monkeypatch):
    case = scoped_case
    from data_sheets_schema import agentic_runtime
    _, selected, spec, doc, runtime = registration._verified_capture_in_scope(case['raw'])
    current = agentic_runtime.toolchain()
    with monkeypatch.context() as patch:
        patch.setattr(agentic_runtime, 'toolchain', lambda: {**current, 'python': '/different/python'})
        with pytest.raises(ValueError, match='toolchain'):
            registration._recheck_selected_capture(selected, spec, doc, runtime)
    with monkeypatch.context() as patch:
        patch.setattr(composition.inherited, 'controller_sources', lambda: {})
        with pytest.raises(ValueError):
            registration._recheck_selected_capture(selected, spec, doc, runtime)
    registration._recheck_selected_capture(selected, spec, doc, runtime)
    require_no_reservation(case)


def test_same_capture_endpoint_recheck_refuses_output_parent_replaced_with_symlink(scoped_case, tmp_path):
    case = scoped_case
    _, selected, spec, doc, runtime = registration._verified_capture_in_scope(case['raw'])
    parent = Path(spec._agentic_artifact_paths['full']).parent
    assert parent.is_relative_to(tmp_path.resolve())
    assert not parent.exists() and not parent.is_symlink()
    other = tmp_path / 'changed-output-parent'
    other.mkdir()
    parent.parent.mkdir(parents=True, exist_ok=True)
    parent.symlink_to(other, target_is_directory=True)
    try:
        with pytest.raises(ValueError):
            registration._selection_in_scope(case['composition_raw'])
        with pytest.raises(ValueError, match='output parents changed'):
            registration._recheck_selected_capture(selected, spec, doc, runtime)
    finally:
        parent.unlink()
    registration._recheck_selected_capture(selected, spec, doc, runtime)
    require_no_reservation(case)


def test_reconstruction_context_requires_actual_scope_and_preserves_body_errors(
        selected_controls, fixed_clock, monkeypatch):
    parent = profile._ACTIVE.get()
    declaration = c.strict_json(parent.profile)
    with profile._reconstruction_controls(declaration) as controls:
        assert controls is selected_controls
    with pytest.raises(ValueError):
        with profile._reconstruction_controls(None):
            pytest.fail('explicit null profile reached body')
    changed = deepcopy(declaration)
    changed['implementations']['control']['sha256'] = '0' * 64
    with pytest.raises(ValueError):
        with profile._reconstruction_controls(changed):
            pytest.fail('stale profile reached body')
    copied = copy_context()
    def foreign():
        with pytest.raises(ValueError):
            with profile._reconstruction_controls(declaration):
                pytest.fail('copied parent scope reached foreign-thread body')
    in_thread(foreign, context=copied)
    in_thread(foreign)
    # A genuine nested loader is unnecessary: replacing the selected scope
    # ContextVar directly is sufficient to test the captured entry identity.
    entry = profile._reconstruction_controls(declaration)
    assert entry.__enter__() is selected_controls
    token = profile._ACTIVE.set(None)
    try:
        with pytest.raises(ValueError):
            entry.__exit__(None, None, None)
    finally:
        profile._ACTIVE.reset(token)
    parent.require()
    now = time.monotonic_ns()
    stop = threading.Event()
    budget = coordination.ReaderBudget(now + 60_000_000_000, (stop,), clock_domain=fixed_clock)
    unbound = coordination.ReaderBudget(budget.deadline_ns, (stop,))
    with coordination.reader_budget(unbound):
        with pytest.raises(ValueError):
            with profile._reconstruction_controls(declaration):
                pytest.fail('unbound reader budget granted reconstruction')
    entry = profile._reconstruction_controls(declaration)
    assert entry.__enter__() is selected_controls
    with coordination.reader_budget(budget):
        with pytest.raises(ValueError):
            entry.__exit__(None, None, None)
    error = OSError('original reconstruction body failure')
    with coordination.reader_budget(budget):
        with pytest.raises(OSError) as caught:
            with profile._reconstruction_controls(declaration):
                stop.set()
                raise error
        assert caught.value is error
    parent.require()


@pytest.mark.parametrize('cause', ['stop', 'deadline', 'nested_budget'])
def test_success_exit_rechecks_original_budget_without_new_allowance(
        selected_controls, fixed_clock, monkeypatch, cause):
    parent = profile._ACTIVE.get()
    declaration = c.strict_json(parent.profile)
    now = [time.monotonic_ns()]
    monkeypatch.setattr(coordination, 'time', SimpleNamespace(
        monotonic_ns=lambda: now[0], sleep=time.sleep))
    stop = threading.Event()
    budget = coordination.ReaderBudget(now[0] + 60_000_000_000, (stop,), clock_domain=fixed_clock)
    with coordination.reader_budget(budget):
        entry = profile._reconstruction_controls(declaration)
        assert entry.__enter__() is selected_controls
        if cause == 'stop':
            stop.set()
            with pytest.raises(ValueError):
                entry.__exit__(None, None, None)
        elif cause == 'deadline':
            now[0] = budget.deadline_ns
            with pytest.raises(ValueError):
                entry.__exit__(None, None, None)
        else:
            other = coordination.ReaderBudget(budget.deadline_ns, budget.stop_events,
                                              clock_domain=budget.clock_domain())
            with coordination.reader_budget(other):
                with pytest.raises(ValueError):
                    entry.__exit__(None, None, None)
    assert (budget.deadline_ns == now[0] if cause == 'deadline' else budget.deadline_ns > now[0])
    parent.require()


def test_expired_original_and_borrowed_reconstruction_entries_cannot_revive(fixed_clock):
    identity = authority.dependency_identity(stream_snapshot_profile=1)
    with authority.loaded_dependencies(identity) as controls:
        parent = profile._ACTIVE.get()
        declaration = deepcopy(identity['stream_snapshot_profile'])
        stale_original = copy_context()
        owner = coordination.ReaderBudget(time.monotonic_ns() + 60_000_000_000,
            (threading.Event(),), clock_domain=fixed_clock)
        def work():
            budget = coordination.ReaderBudget(owner.deadline_ns - 1, owner.stop_events,
                                              clock_domain=owner.clock_domain())
            with coordination.reader_budget(budget):
                with profile._worker_scope(parent, owner):
                    with profile._reconstruction_controls(declaration) as borrowed:
                        assert borrowed is controls
                    stale = copy_context()
                with pytest.raises(ValueError):
                    stale.run(lambda: profile._reconstruction_controls(declaration).__enter__())
            return True
        assert in_thread(work)
    assert not parent.live
    with pytest.raises(ValueError):
        with profile._reconstruction_controls(declaration):
            pytest.fail('outside loader body entered')
    with authority.loaded_dependencies(identity) as fresh:
        assert fresh is not controls
        with pytest.raises(ValueError):
            stale_original.run(lambda: profile._reconstruction_controls(declaration).__enter__())
        with profile._reconstruction_controls(declaration) as current:
            assert current is fresh
