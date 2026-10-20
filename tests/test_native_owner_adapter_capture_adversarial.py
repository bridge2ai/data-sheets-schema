"""Independent selected adapter controls; no provider or full-phase acceptance.

Real runner cases reach actual initialization and then the expected incomplete
phase refusal. Later observation cases below prove only saved codec/owner joins.
"""
from copy import copy, deepcopy
from dataclasses import replace
from pathlib import Path

import pytest

from data_sheets_schema import native_attempt_supervisor as supervisor
from data_sheets_schema import native_execution as execution_api
from data_sheets_schema import native_owner_profile_v1 as profile
from data_sheets_schema import native_shared_capture as capture
from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_evidence as evidence
from data_sheets_schema import native_shared_publication as publication
from data_sheets_schema import native_shared_results as results
from data_sheets_schema import native_shared_stage as stage
from data_sheets_schema import native_stream_coordination_v1 as coordination
from tests.test_native_owner_adapter_capture import (
    adapter_case, adapter_factory, bound, native_spec, declaration, fixed_clock,
    initialized_files, no_nested_loaders, run_to_terminal_refusal,
)
from tests.test_native_owner_initialized_capture import (
    initial_v1, started, execution, selected_case, artifact, member,
    replace_pool_member, pool_member,
)


def stage_bytes(case):
    root = Path(case['selection'].role('stage_root'))
    return {str(path.relative_to(root)): path.read_bytes()
            for path in root.rglob('*') if path.is_file()}


def stop_owner(case, change):
    """Only fixture-owned live attempt files; the runner must retain refusal."""
    if change == 'stop':
        (case['attempt'] / 'stream-owner-stop.json').write_bytes(c.canonical({
            'format': 'native_stream_owner_stop_v1',
            'owner_sha256': c.sha(case['runner'].owner_raw())}))
    elif change == 'owner':
        path = case['attempt'] / 'stream-owner.json'
        path.write_bytes(path.read_bytes() + b' ')
    else:
        raise AssertionError(change)


def forbidden(*args, **kwargs):
    pytest.fail('refused selected operation reached a downstream effect or phase')


def effect_calls(run):
    return (
        lambda: capture.seal_originals(run, 'seal_phase1'),
        lambda: capture.seal_originals(run, 'seal_core'),
        lambda: capture._persist_observation(run, 'phase1_sealed', {}),
        lambda: capture.observe_request_read(run, 'never-admitted'),
        lambda: capture.observe_response_intent(run, 'never-admitted'),
        lambda: capture.observe_response_written(run, 'never-admitted'),
        lambda: capture.observe_advance_settled(run, 'never-admitted'),
    )


def assert_effects_refused(run, monkeypatch):
    # Meaningful ordering traps: missing phase/request state is not the reason
    # these operations may refuse an escaped or mismatched selected context.
    with monkeypatch.context() as patch:
        patch.setattr(capture, 'phase_replay', forbidden)
        patch.setattr(capture, '_create', forbidden)
        patch.setattr(capture, '_append', forbidden)
        patch.setattr(run, 'decision', forbidden)
        patch.setattr(run, 'trace', forbidden)
        patch.setattr(evidence, 'read_regular', forbidden)
        for operation in effect_calls(run):
            with pytest.raises(ValueError):
                operation()


def current_closure_mutants(run):
    """#4735: retain genuine current authority, alter only captured run joins."""
    saved_reader = capture._Reader(run.selection, pool=run.pool, execution=run.binding.execution)
    saved_reader.owner_context = run._owner_context
    yield replace(run, reader=saved_reader)
    copied_reader = copy(run.reader)
    changed_e = artifact('execution_capture', run.binding.execution.pin.path,
                         run.binding.execution.raw + b' ')
    copied_reader._owner_execution = changed_e
    yield replace(run, reader=copied_reader)
    owner = pool_member(run.pool, 'owner')
    without_owner = evidence.CapturePool(tuple(row for row in run.pool.members if row is not owner),
                                        run.pool.stream_bindings)
    yield replace(run, pool=without_owner)
    metadata = c.strict_json(owner.metadata_json)
    metadata['inode'] += 1
    changed_owner = replace(owner, metadata_json=c.canonical(metadata))
    yield replace(run, pool=replace_pool_member(run.pool, owner, changed_owner))
    document = c.strict_json(run.binding.binding_artifact.raw)
    document['session_id'] = '99999999-2222-4333-8444-555555555555'
    changed_artifact = artifact('session_binding', run.binding.binding_artifact.pin.path,
                                c.canonical(document))
    changed_binding = replace(run.binding, binding_artifact=changed_artifact,
                              session_id=document['session_id'])
    yield replace(run, binding=changed_binding)
    for role in ('transcript', 'control'):
        prefix = getattr(run, role)
        raw = b'{}\n'
        changed = replace(prefix, raw=raw, bytes=len(raw), sha256=c.sha(raw), lines=1)
        yield replace(run, **{role: changed})


def accounting_padding(reader, streams, target_total):
    """Synthetic accounting only, with one shared 32 KiB immutable payload.

    Genuine S/E/owner/streams remain untouched. These explicitly invented
    captured observations are never published or claimed as a phase history.
    The real pool constructors and lower-S accounting gates remain in use.
    """
    unique = {row.member_id: row for row in (*reader.members.values(), *streams)}
    remaining = target_total - sum(row.captured.pin.bytes for row in unique.values())
    assert remaining > 0
    shared = b' ' * (32_768 - 2) + b'{}'
    rows = []
    while remaining:
        size = min(len(shared), remaining)
        raw = shared if size == len(shared) else (b'0' if size == 1 else b' ' * (size - 2) + b'{}')
        path = str(Path(reader.selection.role('observations_root')) / f'{10_000 + len(rows):06d}.json')
        assert len(raw) <= reader.destination('observation', path)
        item = artifact('observation', path, raw)
        row = evidence.PoolMember(item, c.canonical({'exists': True, 'regular': True,
            'symlink': False, 'links': 1, 'device': 9901, 'inode': 9902 + len(rows),
            'size': len(raw), 'mtime_ns': 1000}))
        reader._remember(row)
        rows.append(row)
        remaining -= len(raw)
    assert len({row.member_id for row in rows}) == len(rows)
    assert len({id(row.captured.raw) for row in rows}) <= 2
    assert reader.total <= reader.selection.bounds()['max_evidence_bytes']
    assert target_total < c.HARD_LIMITS['evidence_raw_total_bytes']
    return tuple(rows)


def test_unactivated_classifier_and_complete_report_never_fall_back(adapter_case, monkeypatch):
    case = adapter_case
    adapter = case['adapter']
    with monkeypatch.context() as patch:
        patch.setattr(adapter, '_owner_reader', forbidden)
        patch.setattr(adapter, '_classify', forbidden)
        patch.setattr(capture, '_load', forbidden)
        with pytest.raises(case['controls']['budgeted_cborg'].BudgetStop,
                           match='successful owner activation'):
            adapter.classify('cat never', 'python', (), adapter.policy)
        first = adapter.failure
        report = adapter.report(complete=True)
        assert report['controller_stop'] == first
        assert report['draft_gate_passed'] is False
    assert not case['runner'].report()
    assert case['dispatch_accounting']['dispatches'] == 0
    assert stage_bytes(case) == {}


def test_complete_report_without_prior_failure_refuses_without_live_context(adapter_case, monkeypatch):
    adapter = adapter_case['adapter']
    assert adapter.failure is None
    with monkeypatch.context() as patch:
        patch.setattr(adapter, '_owner_reader', forbidden)
        patch.setattr(capture, '_load', forbidden)
        patch.setattr(capture, '_load_live', forbidden)
        report = adapter.report(complete=True)
    assert 'stopped full-capture closure' in report['controller_stop']
    assert report['draft_gate_passed'] is False
    assert adapter_case['dispatch_accounting']['dispatches'] == 0


def test_activation_requires_exact_actual_owner_bytes_before_publication(adapter_case, monkeypatch):
    case = adapter_case
    original = case['adapter'].activate_before_dispatch
    owners = []
    def changed_owner(started_raw, *, owner_raw=None):
        assert owner_raw == case['runner'].owner_raw()
        assert owner_raw == (case['attempt'] / 'stream-owner.json').read_bytes()
        owners.append(owner_raw)
        # Equal parsed JSON is insufficient: this is not the actual retained
        # raw owner file. The genuine C/E verifier and launch recheck still run.
        return original(started_raw, owner_raw=owner_raw + b' ')
    monkeypatch.setattr(case['adapter'], 'activate_before_dispatch', changed_owner)
    with pytest.raises(ValueError):
        case['runner'].execute_child(**case['kwargs'])
    assert len(owners) == 1 and case['runner'].owner_raw() == owners[0]
    assert case['adapter']._activated and not case['adapter']._activation_ready
    assert case['dispatch_accounting']['dispatches'] == 0
    assert stage_bytes(case) == {}


def test_partial_activation_is_spent_and_runner_preserves_original_write_error(adapter_case, monkeypatch):
    case, calls = adapter_case, []
    adapter = case['adapter']
    failure = OSError('fixture started-capture write failed')
    real_write = supervisor.durable_new
    blocked = Path(case['selection'].role('started_capture'))

    def fail_selected_started(path, raw):
        if Path(path) == blocked:
            calls.append(Path(path))
            raise failure
        return real_write(path, raw)

    original_launch = case['kwargs']['verify_launch']
    def launch():
        try:
            original_launch()
        except OSError as caught:
            assert caught is failure
            assert adapter._activated and not adapter._activation_ready
            with pytest.raises(ValueError, match='already spent'):
                adapter.activate_before_dispatch(case['started_raw'], owner_raw=case['runner'].owner_raw())
            with pytest.raises(case['controls']['budgeted_cborg'].BudgetStop,
                               match='successful owner activation'):
                adapter.classify('cat never', 'python', (), adapter.policy)
            first = adapter.failure
            with pytest.raises(case['controls']['budgeted_cborg'].BudgetStop) as repeated:
                adapter.observe({'type': 'result'})
            assert str(repeated.value) == first
            raise
    case['kwargs']['verify_launch'] = launch
    monkeypatch.setattr(supervisor, 'durable_new', fail_selected_started)
    with pytest.raises(OSError) as caught:
        case['runner'].execute_child(**case['kwargs'])
    assert caught.value is failure and calls == [blocked]
    assert case['dispatch_accounting']['dispatches'] == 0
    assert Path(case['selection'].role('execution_capture')).read_bytes() == case['raw']
    assert not blocked.exists()
    assert not Path(case['selection'].role('journal')).exists()
    assert 'fixture started-capture write failed' in str(case['runner'].report()['primary_error'])


@pytest.mark.parametrize('change', ['stop', 'owner'])
def test_change_between_adapter_and_capture_reads_refuses_before_init_write(
        adapter_case, monkeypatch, change):
    case = adapter_case
    adapter = case['adapter']
    original = adapter._observed_endpoint
    crossed = []
    def observed(event, **kwargs):
        endpoints = original(event, **kwargs)
        if event.get('type') == 'system' and event.get('subtype') == 'init':
            crossed.append(kwargs['owner_context'])
            stop_owner(case, change)
        return endpoints
    monkeypatch.setattr(adapter, '_observed_endpoint', observed)
    with no_nested_loaders(monkeypatch, case['controls']):
        with pytest.raises(case['controls']['budgeted_cborg'].BudgetStop):
            case['runner'].execute_child(**case['kwargs'])
    assert len(crossed) == 1
    assert case['dispatch_accounting']['dispatches'] == 1
    assert not Path(case['selection'].role('session_binding')).exists()
    observations = Path(case['selection'].role('observations_root'))
    assert not observations.exists() or not list(observations.iterdir())
    journal = c.strict_json(Path(case['selection'].role('journal')).read_bytes())
    assert len(journal['records']) == 1
    assert adapter._initialized is False


@pytest.mark.parametrize('boundary', ['observation_create', 'journal_replace'])
def test_stop_at_actual_publication_boundary_keeps_prior_bytes_without_credit(
        adapter_case, monkeypatch, boundary):
    case = adapter_case
    events = []
    real_mkdir = execution_api._mkdir_durable
    real_create = capture._create
    real_replace = publication._replace_journal
    observation_parent = Path(case['selection'].role('observations_root'))

    def mkdir(path):
        result = real_mkdir(path)
        if boundary == 'observation_create' and Path(path) == observation_parent:
            events.append('mkdir before observation write')
            stop_owner(case, 'stop')
        return result

    def create(selection, role, raw, **kwargs):
        result = real_create(selection, role, raw, **kwargs)
        if boundary == 'journal_replace' and role == 'record' and kwargs.get('ordinal') == 1:
            events.append('second record before journal replacement')
            stop_owner(case, 'stop')
        return result

    replacements = []
    def replace_journal(*args, **kwargs):
        replacements.append(args)
        return real_replace(*args, **kwargs)

    monkeypatch.setattr(execution_api, '_mkdir_durable', mkdir)
    monkeypatch.setattr(capture, '_create', create)
    monkeypatch.setattr(publication, '_replace_journal', replace_journal)
    with pytest.raises(case['controls']['budgeted_cborg'].BudgetStop):
        case['runner'].execute_child(**case['kwargs'])
    assert len(events) == 1 and replacements == []
    journal = c.strict_json(Path(case['selection'].role('journal')).read_bytes())
    assert len(journal['records']) == 1
    assert not case['adapter']._initialized
    if boundary == 'observation_create':
        assert not list(observation_parent.iterdir())
        assert not Path(case['selection'].role('session_binding')).exists()
    else:
        assert len(list(observation_parent.iterdir())) == 1
        assert Path(case['selection'].role('session_binding')).exists()
        assert Path(stage._dynamic(case['selection'], 'record', 1)).exists()


def test_body_write_error_survives_secondary_stop_and_context_exit(adapter_case, monkeypatch):
    case = adapter_case
    first = OSError('primary selected observation write failed')
    real_write = supervisor.durable_new
    observed = []
    def fail_observation(path, raw):
        if Path(path).parent == Path(case['selection'].role('observations_root')):
            observed.append(Path(path))
            stop_owner(case, 'stop')
            raise first
        return real_write(path, raw)
    monkeypatch.setattr(supervisor, 'durable_new', fail_observation)
    with pytest.raises(case['controls']['budgeted_cborg'].BudgetStop,
                       match='primary selected observation write failed') as caught:
        case['runner'].execute_child(**case['kwargs'])
    assert len(observed) == 1 and not observed[0].exists()
    assert 'primary selected observation write failed' in case['adapter'].failure
    assert 'primary selected observation write failed' in str(caught.value)


def test_actual_initialized_run_cannot_escape_or_drop_its_budget_context(adapter_case, monkeypatch):
    case, retained = adapter_case, []
    original = case['adapter']._run
    def remember(endpoints=None, **kwargs):
        run = original(endpoints, **kwargs)
        if not retained:
            assert type(run) is capture._CapturedRun
            capture._require_run_effect(run)
            budget = coordination.current_reader_budget()
            assert run._owner_context.budget is budget
            before = stage_bytes(case)
            nested = coordination.ReaderBudget(budget.deadline_ns, budget.stop_events,
                                               clock_domain=budget.clock_domain())
            with coordination.reader_budget(nested):
                assert_effects_refused(run, monkeypatch)
            capture._require_run_effect(run)
            assert stage_bytes(case) == before
            # Mutable projections cannot silently convert an actual selected
            # run to the legacy path, even inside its genuine current context.
            for forged in (replace(run, _owner_context=None),
                           replace(run, value={**run.value, 'dependencies': {'version': 1}}),
                           replace(run, composition={**run.composition, 'policy': {}})):
                with pytest.raises(ValueError):
                    capture._require_run_effect(forged)
            mutants = tuple(current_closure_mutants(run))
            assert len(mutants) == 7
            for forged in mutants:
                with pytest.raises(ValueError):
                    capture._require_run_effect(forged)
                with monkeypatch.context() as patch:
                    patch.setattr(capture, '_create', forbidden)
                    with pytest.raises(ValueError):
                        capture._persist_observation(forged, 'phase1_sealed', {})
            capture._require_run_effect(run)
            assert stage_bytes(case) == before
            retained.append(run)
        return run
    monkeypatch.setattr(case['adapter'], '_run', remember)
    run_to_terminal_refusal(case)
    assert len(retained) == 1
    run = retained[0]
    actual = initialized_files(case)
    assert actual['observation']['version'] == 2 and len(actual['records']) == 2
    before = stage_bytes(case)
    assert_effects_refused(run, monkeypatch)
    assert_effects_refused(replace(run, _owner_context=None), monkeypatch)
    with pytest.raises(ValueError):
        run.reader.read('execution_capture', run.selection.role('execution_capture'))
    with pytest.raises(ValueError):
        capture._append(run.selection, run.binding, run.history, 'session_bound', {})
    with pytest.raises(ValueError):
        capture._create(run.selection, 'phase1_full', b'fixture', owner_context=run._owner_context)
    assert stage_bytes(case) == before
    # Report-only calls do not replace the real terminal refusal with a fresh
    # stopped read or renew the escaped scope.
    failure = case['adapter'].failure
    with monkeypatch.context() as patch:
        patch.setattr(case['adapter'], '_owner_reader', forbidden)
        patch.setattr(capture, '_load', forbidden)
        patch.setattr(capture, '_load_live', forbidden)
        assert case['adapter'].report(complete=True)['controller_stop'] == failure


def test_genuine_lower_selection_counts_unique_full_pool_at_exact_boundary(adapter_factory, monkeypatch):
    """Unit accounting at the actual live pool seam, not a 33 MB stream run."""
    bound = 33_000_000  # Valid above the unchanged 32 MB finalization reserve.
    case = adapter_factory(max_evidence_bytes=bound)
    assert case['selection'].bounds()['max_evidence_bytes'] == bound
    original, checked = case['adapter']._run, []
    def check(endpoints=None, **kwargs):
        run = original(endpoints, **kwargs)
        if not checked:
            streams = tuple(run.pool.member(identity) for _, identity in run.pool.stream_bindings)
            assert {row.captured.pin.role for row in streams} == {'transcript', 'control'}
            padded = copy(run.reader)
            padded.members = dict(run.reader.members)
            # The same genuine stream appears in the reader and stream input;
            # the complete pool must count this member identity only once.
            padded._remember(streams[0])
            rows = accounting_padding(padded, streams, bound)
            exact = capture._pool(padded, streams)
            assert sum(row.captured.pin.bytes for row in exact.members) == bound
            assert len({row.member_id for row in exact.members}) == len(exact.members)
            assert exact.stream_bindings == run.pool.stream_bindings
            capture._require_run_effect(replace(run, reader=padded, pool=exact))
            last = artifact('observation', str(Path(run.selection.role('observations_root')) / '020000.json'), b'0')
            extra = member(last)
            padded._remember(extra)
            with pytest.raises(ValueError, match='bound|exceeds|total'):
                capture._pool(padded, streams)
            over = evidence.CapturePool((*exact.members, extra), exact.stream_bindings)
            assert sum(row.captured.pin.bytes for row in over.members) == bound + 1
            with monkeypatch.context() as patch:
                patch.setattr(capture, '_create', forbidden)
                with pytest.raises(ValueError, match='bound|exceeds|total'):
                    capture._persist_observation(replace(run, reader=padded, pool=over), 'phase1_sealed', {})
            capture._require_run_effect(run)
            checked.append(len(rows))
        return run
    monkeypatch.setattr(case['adapter'], '_run', check)
    run_to_terminal_refusal(case)
    assert len(checked) == 1 and 1 < checked[0] < 1100
    assert len(initialized_files(case)['records']) == 2


def test_complete_pool_over_lower_selection_refuses_before_first_init_write(adapter_factory, monkeypatch):
    """Inject only accounting members; real streams/owner/C/E remain exact."""
    bound = 33_000_000
    case = adapter_factory(max_evidence_bytes=bound)
    real_pool, checked = capture._pool, []
    def pool(reader, streams):
        assert not checked, 'initialization must refuse at its first complete pool'
        assert reader.owner_context is not None
        assert reader.selection == case['selection']
        assert {row.captured.pin.role for row in streams} == {'transcript', 'control'}
        actual_streams = tuple((row.captured, row.metadata_json) for row in streams)
        original = {key: row for key, row in reader.members.items()}
        rows = accounting_padding(reader, streams, bound + 1)
        assert all(reader.members[key] is row for key, row in original.items())
        assert tuple((row.captured, row.metadata_json) for row in streams) == actual_streams
        checked.append(len(rows))
        return real_pool(reader, streams)
    monkeypatch.setattr(capture, '_pool', pool)
    with pytest.raises(case['controls']['budgeted_cborg'].BudgetStop, match='bound|exceeds|total'):
        case['runner'].execute_child(**case['kwargs'])
    assert len(checked) == 1
    assert not Path(case['selection'].role('session_binding')).exists()
    root = Path(case['selection'].role('observations_root'))
    assert not root.exists() or not list(root.iterdir())
    journal = c.strict_json(Path(case['selection'].role('journal')).read_bytes())
    assert len(journal['records']) == 1
    assert not case['adapter']._initialized


def test_saved_profile_is_optional_only_for_historical_limited_carrier(initial_v1):
    baseline = initial_v1
    original = baseline['pool'].encode()
    declared = baseline['selected_dependencies']['stream_snapshot_profile']
    for present in (False, True):
        mutations = None if not present else {'composition': lambda value: value.update(
            stream_snapshot_profile=deepcopy(declared))}
        case = selected_case(baseline, mutations=mutations)
        result = results.rebuild(case['pool'], case['value'])
        assert type(result) is results._OwnerInitializationEvidence
        assert result.as_dict()['counts']['observations'] == 1
        assert result.as_dict()['counts']['history_records'] == 2
    bad_version = deepcopy(declared); bad_version['profile'] = True
    bad_role = deepcopy(declared)
    role = next(iter(bad_role['implementations']))
    bad_role['implementations'][role]['sha256'] = '0' * 64
    for invalid in (None, {}, bad_version, bad_role):
        case = selected_case(baseline, mutations={'composition': lambda value, bad=invalid:
            value.update(stream_snapshot_profile=deepcopy(bad))})
        assert case['value']['composition_sha256'] == c.sha(c.canonical(case['composition']))
        assert case['owner']['execution_sha256'] == case['artifacts']['execution'].pin.sha256
        with pytest.raises(ValueError, match='profile'):
            results.rebuild(case['pool'], case['value'])
    assert baseline['pool'].encode() == original


def test_later_v1_codec_requires_same_selected_initialized_v2_only(initial_v1):
    """Explicit saved protocol fixture, not a live phase-seal/helper run."""
    case = selected_case(initial_v1, mutations={'composition': lambda value: value.update(
        stream_snapshot_profile=deepcopy(initial_v1['selected_dependencies']['stream_snapshot_profile']))})
    reader = capture._Reader(case['selection'], pool=case['pool'], execution=case['artifacts']['execution'])
    binding = capture._binding(case['selection'], case['value'], case['composition'], reader, case['pool'])
    payload = {'full': c.pin_dict(artifact('phase1_full', case['selection'].role('phase1_full'), b'{}').pin),
               'original_receipt': c.pin_dict(artifact('phase1_receipt',
                    case['selection'].role('phase1_receipt'), b'{}').pin), 'helper_calls': []}
    raw = capture.observation_bytes('phase1_sealed', case['selection'], binding.execution.pin.sha256,
        binding.attempt_id, binding.session_id, case['prefixes']['transcript'], case['prefixes']['control'], payload)
    later = artifact('observation', Path(case['selection'].role('observations_root')) / '000001.json', raw)
    doc, transcript, control = capture.observation(later, case['selection'], binding, case['pool'])
    assert doc['version'] == 1 and doc['observation_type'] == 'phase1_sealed'
    assert transcript == case['prefixes']['transcript'] and control == case['prefixes']['control']
    for change in ('missing_init', 'changed_init', 'missing_owner', 'v2_later'):
        pool, item = case['pool'], later
        if change.startswith('missing_'):
            role = 'observation' if change == 'missing_init' else 'owner'
            pool = evidence.CapturePool(tuple(row for row in pool.members if row.captured.pin.role != role), pool.stream_bindings)
        elif change == 'changed_init':
            target = pool_member(pool, 'observation')
            value = c.strict_json(target.captured.raw); value['version'] = 1
            replacement = artifact('observation', target.captured.pin.path, c.canonical(value))
            pool = replace_pool_member(pool, target, member(replacement, target))
        else:
            value = c.strict_json(raw); value['version'] = 2
            item = artifact('observation', later.pin.path, c.canonical(value))
        with pytest.raises(ValueError):
            capture.observation(item, case['selection'], binding, pool)
    # A later codec-positive row cannot expand the intentionally narrow saved
    # carrier denominator into full selected history/decision authority.
    extended = evidence.CapturePool((*case['pool'].members, member(later)), case['pool'].stream_bindings)
    with pytest.raises(ValueError):
        results.rebuild(extended, case['value'])
    historical = selected_case(initial_v1)
    legacy_reader = capture._Reader(historical['selection'], pool=historical['pool'],
                                    execution=historical['artifacts']['execution'])
    legacy_binding = capture._binding(historical['selection'], historical['value'],
        historical['composition'], legacy_reader, historical['pool'])
    legacy_raw = capture.observation_bytes('phase1_sealed', historical['selection'],
        legacy_binding.execution.pin.sha256, legacy_binding.attempt_id, legacy_binding.session_id,
        historical['prefixes']['transcript'], historical['prefixes']['control'], payload)
    legacy_later = artifact('observation', later.pin.path, legacy_raw)
    with pytest.raises(ValueError, match='initialization-only'):
        capture.observation(legacy_later, historical['selection'], legacy_binding, historical['pool'])


def test_noninitialized_binding_refuses_before_recursive_observation_resolution(initial_v1, monkeypatch):
    """#4734: real immutable carriers with honestly rehashed malformed joins."""
    case = selected_case(initial_v1, mutations={'composition': lambda value: value.update(
        stream_snapshot_profile=deepcopy(initial_v1['selected_dependencies']['stream_snapshot_profile']))})
    reader = capture._Reader(case['selection'], pool=case['pool'], execution=case['artifacts']['execution'])
    binding = capture._binding(case['selection'], case['value'], case['composition'], reader, case['pool'])
    payload = {'full': c.pin_dict(artifact('phase1_full', case['selection'].role('phase1_full'), b'{}').pin),
               'original_receipt': c.pin_dict(artifact('phase1_receipt',
                    case['selection'].role('phase1_receipt'), b'{}').pin), 'helper_calls': []}
    raw = capture.observation_bytes('phase1_sealed', case['selection'], binding.execution.pin.sha256,
        binding.attempt_id, binding.session_id, case['prefixes']['transcript'], case['prefixes']['control'], payload)
    real_observation = capture.observation
    for same_path in (True, False):
        later = artifact('observation', Path(case['selection'].role('observations_root')) / '000001.json', raw)
        named = later if same_path else artifact('observation',
            Path(case['selection'].role('observations_root')) / '000002.json', raw)
        document = c.strict_json(binding.binding_artifact.raw)
        document['init_observation'] = c.pin_dict(named.pin)
        changed_binding = artifact('session_binding', binding.binding_artifact.pin.path, c.canonical(document))
        forged = replace(binding, binding_artifact=changed_binding, init_observation=named)
        target = pool_member(case['pool'], 'session_binding')
        pool = replace_pool_member(case['pool'], target, member(changed_binding, target))
        additions = (member(later),) if same_path else (member(later), member(named))
        pool = evidence.CapturePool((*pool.members, *additions), pool.stream_bindings)
        assert c.strict_json(forged.binding_artifact.raw)['init_observation'] == c.pin_dict(named.pin)
        assert pool_member(pool, 'observation', named.pin.path).captured == named
        calls = []
        def checked(*args, **kwargs):
            calls.append(args[0].pin.path)
            assert len(calls) == 1, 'malformed initialization recursed before checking kind/version'
            return real_observation(*args, **kwargs)
        with monkeypatch.context() as patch:
            patch.setattr(capture, 'observation', checked)
            with pytest.raises(ValueError):
                capture.observation(later, case['selection'], forged, pool)
        assert calls == [later.pin.path]
