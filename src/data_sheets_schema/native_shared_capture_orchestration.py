"""Live C capture verification and durable publication orchestration.

Moved from native_shared_capture by the reviewed round-four split. Pure replay
classes/helpers remain defined once in that consumer module. Every live base
freshly verifies outer E with an explicit active classifier projection; no
successful replay verdict is cached as authority.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from pathlib import Path, PurePosixPath
import shlex
import threading

from . import native_shared_contract as c
from . import native_shared_evidence as evidence
from . import native_shared_streams as live_streams
from . import native_shared_observations as observed
from . import native_shared_stage as stage
from .native_shared_callback_capture import Admission
from .native_shared_callback_io import durable_new, _mkdir_durable, _replace_journal
from .native_shared_capture import (
    _Reader,
    _binding,
    _binding_document,
    _call,
    _captured,
    _check_advance_acknowledgement,
    _declared_stream_files,
    _document,
    _live_streams,
    _loaded,
    _observation_paths,
    _pool,
    _provenance_block,
    _receipt_assessment,
    _require_completed_read_before_write,
    _streams,
    _through,
    call_document,
    current_effect_view,
    observation,
    observation_bytes,
    phase_replay,
)


def _create(selection, role, raw, *, ordinal=None):
    """Sole parent/helper create-once primitive for explicitly derived S roles."""
    if role == 'observation':
        paths = _observation_paths(selection)
        if ordinal is not None and ordinal != len(paths):
            raise ValueError('observation ordinal changed before publication')
        path = str(PurePosixPath(selection.role('observations_root')) / f'{len(paths):06d}.json')
    elif role == 'record':
        path = stage._dynamic(selection, role, ordinal)
    else:
        path = selection.role(role)
    limit = _Reader(selection).destination(role, path)
    if type(raw) is not bytes or not raw or len(raw) > limit:
        raise ValueError('selected publication exceeds its complete role bound')
    target = Path(path)
    root = Path(selection.role('stage_root'))
    if (root not in target.parents or target.resolve() != target or target.exists() or target.is_symlink()
            or not root.is_dir() or root.is_symlink() or root.resolve() != root):
        raise ValueError('native publication is not one new physical S-owned destination')
    _mkdir_durable(target.parent)
    durable_new(target, raw)
    item = evidence.read_regular(path, role, max_bytes=limit).captured
    if item.raw != raw:
        raise ValueError('published native artifact differs from its intended bytes')
    return item


def _append(selection, execution, history, kind, payload):
    """Parent record publication shares C's exact serializer and journal CAS."""
    records, journal = stage.append_records(selection, execution, history, ((kind, c.canonical(payload)),))
    for record in records:
        _create(selection, 'record', record.raw, ordinal=len(history.records))
    _replace_journal(Path(selection.role('journal')), history.journal, journal)
    _host_stage_clock(execution, journal.pin.sha256)


def _host_stage_clock(execution, journal_sha256):
    from .native_shared_controller import captured_execution_body
    from .native_host_power import checkpoint, observe
    value = captured_execution_body(execution.execution.raw)
    observe(value['attempt_directory'], 'stage-' + journal_sha256,
            checkpoint, value['attempt_directory'], 'stage-' + journal_sha256)


def activate(selection, execution_raw, started_raw):
    """Called only by the fixed lifetime immediately before its single dispatch.

    This writes no session declaration. The later session binding must come
    from actual initialized native/control streams.

    RunSpec boundary: validated-caller

    RunSpec precondition: Fixed lifetime supplies selected execution bytes; registration.verified and reconstruct_composition rederive preparation before activation effects.
    """
    from . import native_execution_registration_v2 as registration
    from . import native_shared_controls_orchestration as controls_orchestration
    from .native_shared_controller_orchestration import reconstruct_composition
    with controls_orchestration.loaded_controls() as controls:
        value = registration.verified(execution_raw, classifier_projection=controls)
    composition, _, captured_selection = reconstruct_composition(
        value['composition_raw_json'].encode('utf-8'))
    if (captured_selection != selection
            or composition['selection_raw_json'].encode('utf-8') != selection.registration.raw):
        raise ValueError('activation E does not capture this exact selected S')
    return _activate_bound(selection, value, execution_raw, started_raw)


def activate_admitted(admission, started_raw):
    if threading.current_thread() is not threading.main_thread():
        raise ValueError('native callback activation requires main-thread admission')
    if type(admission) is not Admission:
        raise ValueError('callback activation requires its fixed admitted interface')
    value = admission.reconstruct()
    return _activate_bound(admission.selection, value, admission.registration_raw, started_raw)


def _activate_bound(selection, value, execution_raw, started_raw):
    started = _document(started_raw, 'started identity')
    if (started.get('state') != 'started' or started.get('attempt_id') != value['attempt_id']
            or started.get('registration_sha256') != c.sha(execution_raw)
            or started.get('composition_sha256') != value['composition_sha256']
            or type(started.get('dispatch_limit')) is not int or started['dispatch_limit'] != 1):
        raise ValueError('activation lacks its actual single-use started identity')
    attempt = Path(value['attempt_directory'])
    for name, expected in (('registration.json', execution_raw), ('started.json', started_raw)):
        if evidence.read_regular(str(attempt / name), 'attempt_identity', max_bytes=c.HARD_LIMITS['request_bytes']).captured.raw != expected:
            raise ValueError('activation differs from actual reserved attempt evidence')
    destinations = ('execution_capture', 'started_capture', 'journal')
    if any(Path(selection.role(role)).exists() or Path(selection.role(role)).is_symlink() for role in destinations):
        raise ValueError('native stage activation is spent and cannot be resumed')
    e = _create(selection, 'execution_capture', execution_raw)
    s = _create(selection, 'started_capture', started_raw)
    raw = stage.record_bytes(record_type='genesis', sequence=0, previous_record_sha256=None,
        selection_sha256=selection.registration.pin.sha256, execution_sha256=e.pin.sha256,
        attempt_id=value['attempt_id'], session_id=None,
        payload={'execution': c.pin_dict(e.pin), 'started': c.pin_dict(s.pin)})
    record = _create(selection, 'record', raw, ordinal=0)
    _create(selection, 'journal', stage.journal_bytes(selection_sha256=selection.registration.pin.sha256,
        execution_sha256=e.pin.sha256, attempt_id=value['attempt_id'], records=(record.pin,)))


def _base(selection_path, *, _catalogs=None, _admission=None):
    if _admission is not None:
        if type(_admission) is not Admission:
            raise ValueError('callback capture requires its fixed admitted interface')
        return _admission.base(selection_path)
    if threading.current_thread() is not threading.main_thread():
        raise ValueError('native callback cannot load captures; preload on the main thread at admission')
    from . import native_shared_selection as selected
    from . import native_execution_registration_v2 as registration
    from . import native_shared_controls_orchestration as controls_orchestration
    from .native_shared_controller_orchestration import reconstruct_composition
    selection = selected.capture(selection_path)
    reader = _Reader(selection)
    e = reader.read('execution_capture', selection.role('execution_capture'))
    # Never turn an earlier successful E/C check into current admission. The
    # fixed U3-D consumer must exist and freshly reconstruct every execution.
    with controls_orchestration.loaded_controls() as controls:
        value = registration.verified(e.raw, classifier_projection=controls)
    composition, spec, captured_selection = reconstruct_composition(
        value['composition_raw_json'].encode('utf-8'))
    doc = captured_selection.document()
    if (captured_selection != selection or doc['registration_path'] != selection_path
            or composition['selection_raw_json'].encode('utf-8') != selection.registration.raw
            or value['selection_sha256'] != selection.registration.pin.sha256):
        raise ValueError('actual E/C/S binding differs from the caller-selected registration')
    for filename, role in (('registration.json', 'execution_capture'), ('started.json', 'started_capture')):
        actual = evidence.read_regular(str(Path(value['attempt_directory']) / filename), role,
            max_bytes=c.HARD_LIMITS['request_bytes']).captured
        saved = reader.read(role, selection.role(role))
        if actual.raw != saved.raw:
            raise ValueError('stage binding differs from actual one-use attempt records')
    started = _document(reader.read('started_capture', selection.role('started_capture')).raw, 'started identity')
    if (started.get('state') != 'started' or started.get('attempt_id') != value['attempt_id']
            or started.get('registration_sha256') != e.pin.sha256
            or started.get('composition_sha256') != value['composition_sha256']
            or type(started.get('dispatch_limit')) is not int or started['dispatch_limit'] != 1):
        raise ValueError('selected stage does not have its actual one-use started identity')
    return selection, reader, value, composition, spec


def initialize(selection_path, *, transcript_bytes, control_bytes, stream_files, observed_prefixes, _admission=None):
    """Bind the actual parent-observed initialization, never owner summary flags.

    RunSpec boundary: validated-caller

    RunSpec precondition: Caller supplies actual observed initialization; _base reconstructs the active execution and its guarded preparation before stream binding.
    """
    selection, reader, value, composition, _ = _base(selection_path, _admission=_admission)
    streams, (transcript, control) = _live_streams(value, stream_files=stream_files, transcript_bytes=transcript_bytes, control_bytes=control_bytes)
    c.exact(observed_prefixes, {'transcript', 'control'}, 'parent observed prefixes')
    if observed_prefixes != {'transcript': transcript, 'control': control}:
        raise ValueError('initialization differs from the exact parent-observed prefixes')
    session, sent, ack, init = observed.initialization(transcript, control,
        policy=composition['policy'], runtime=value['runtime'])
    if Path(selection.role('session_binding')).exists() or _observation_paths(selection):
        raise ValueError('native initialization binding is spent or repeated')
    execution = reader.read('execution_capture', selection.role('execution_capture'))
    started = reader.read('started_capture', selection.role('started_capture'))
    item = _create(selection, 'observation', observation_bytes('initialized', selection, execution.pin.sha256,
        value['attempt_id'], session, transcript, control,
        {'initialize_sent': asdict(sent), 'initialize_ack': asdict(ack), 'native_init': asdict(init), 'stream_files': live_streams.stream_files(streams)}))
    _create(selection, 'session_binding', c.canonical(_binding_document(selection, value, composition,
        execution, started, item, session)))
    reader = _Reader(selection)
    binding = _binding(selection, value, composition, reader, _pool(reader, streams))
    history = reader.history(binding)
    if len(history.records) != 1:
        raise ValueError('native session binding requires the sole prior genesis')
    _append(selection, binding, history, 'session_bound',
        {'binding': c.pin_dict(binding.binding_artifact.pin), 'init_observation': c.pin_dict(item.pin)})


def _load(selection_path, *, transcript_bytes=None, control_bytes=None, _catalogs=None, _admission=None):
    """Strict complete-file route for final and recorded consumers."""
    base = _base(selection_path, _catalogs=_catalogs, _admission=_admission)
    streams, prefixes = _streams(base[2], transcript_bytes=transcript_bytes, control_bytes=control_bytes)
    return _loaded(base, streams, prefixes, _catalogs=_catalogs)


def _load_live(selection_path, *, transcript_bytes=None, control_bytes=None, stream_files=None, _catalogs=None, _admission=None):
    """Fresh live authority, optionally with owner-reused pure catalog storage."""
    base = _base(selection_path, _catalogs=_catalogs, _admission=_admission)
    anchors = _declared_stream_files(base[0], base[1])
    if stream_files is not None and live_streams.identities(stream_files) != anchors:
        raise ValueError('observed stream identities differ from initialized authority')
    streams, prefixes = _live_streams(base[2], stream_files=anchors,
        transcript_bytes=transcript_bytes, control_bytes=control_bytes)
    return _loaded(base, streams, prefixes, _catalogs=_catalogs)


def _persist_observation(run, kind, payload):
    return _create(run.selection, 'observation', observation_bytes(kind, run.selection,
        run.binding.execution.pin.sha256, run.binding.attempt_id, run.binding.session_id,
        run.transcript, run.control, payload), ordinal=len(run.observations))


def capture_stage(selection_registration_path, *, _catalogs=None):
    """Capture the sole pending, actually admitted fixed advance invocation.

    RunSpec boundary: validated-caller

    RunSpec precondition: Caller supplies the selected registration path; _load_live reconstructs active execution and preparation before returning the pending invocation.
    """
    run = _load_live(str(selection_registration_path), _catalogs=_catalogs)
    if run.phase1 is None:
        raise ValueError('advance precedes actual sealed originals')
    phase, _ = phase_replay(run)
    if not phase['passed']:
        raise ValueError('advance current phase history did not pass')
    trace = run.trace()
    pending = trace.pending()
    if len(pending) != 1:
        raise ValueError('stage helper requires one actual pending call')
    command = run.composition['policy']['native_shared_helpers']['advance']
    call = trace.current_advance(pending[0], command)
    # A helper cannot use bytes prefetched after its own actual callback.
    transcript = _through(run.transcript, call.callback.line)
    control = _through(run.control, call.admission.line)
    obs_docs = [(item, c.strict_json(item.raw)) for item in run.observations]
    candidates = [item for item, doc in obs_docs if doc['observation_type'] == 'advance_admitted'
                  and doc['payload']['call']['tool_use_id'] == call.tool_use_id]
    if not candidates:
        if sum(doc['observation_type'] == 'advance_admitted' for _, doc in obs_docs) >= c.HARD_LIMITS['advance_invocations']:
            raise ValueError('stage helper invocation count exceeds its complete bound')
        admission = _persist_observation(replace(run, transcript=transcript, control=control), 'advance_admitted',
            {'call': call_document(call), 'before_history_sha256': run.history.journal.pin.sha256})
    elif len(candidates) == 1:
        admission = candidates[0]
        doc, actual_transcript, actual_control = observation(admission, run.selection, run.binding, run.pool)
        if (actual_transcript != transcript or actual_control != control
                or doc['payload'] != {'call': call_document(call), 'before_history_sha256': run.history.journal.pin.sha256}):
            raise ValueError('spent advance admission cannot publish against a different journal')
    else:
        raise ValueError('duplicate advance admission identity')
    return c.StageInvocationCapture(selection=run.selection, execution=run.binding, phase1=run.phase1,
        history=run.history, current_advance=c.CurrentAdvance(admission_observation=admission,
            argv=tuple(shlex.split(command)), call=call, command=command, control_prefix=control,
            predecessor_history_sha256=run.history.journal.pin.sha256, transcript_prefix=transcript,
            working_directory=run.binding.working_directory))


def publish_stage(invocation, proposal, *, _catalogs=None):
    """Recheck the same current invocation, then perform only derived effects.

    RunSpec boundary: validated-caller

    RunSpec precondition: Caller supplies a captured invocation; capture_stage rechecks its live execution and guarded preparation before publication.
    """
    from .native_shared_publication_orchestration import publish_derived
    if type(invocation) is not c.StageInvocationCapture:
        raise ValueError('publication requires the actual selected captured invocation')
    fresh = capture_stage(invocation.selection.registration.pin.path, _catalogs=_catalogs)
    # A newly persisted admission is an external observation, not part of the
    # journal predecessor; include it consistently in the freshly read history.
    old = replace(invocation, history=replace(invocation.history,
        observations=fresh.history.observations))
    if old != fresh:
        raise ValueError('selected capture changed before stage publication')
    result, _ = publish_derived(fresh, proposal, _catalogs=_catalogs)
    _host_stage_clock(invocation.execution, result['after_history_sha256'])
    return result


def seal_originals(run, kind):
    """Parent-only observation effect after genuine settled helper results."""
    if kind not in ('seal_phase1', 'seal_core'):
        raise ValueError('unknown native seal action')
    report, actions = phase_replay(run)
    if kind not in actions.get(run.transcript.lines, ((), None))[0]:
        raise ValueError('seal does not follow this exact observed helper boundary')
    paths = run.spec._agentic_artifact_paths
    if kind == 'seal_phase1':
        if run.phase1 is not None:
            raise ValueError('original full/receipt seal is spent')
        inputs = [('full', 'phase1_full'), ('receipt', 'phase1_receipt')]
        helpers = {'chunk_check', 'source_scope', 'full_schema', 'full_terms', 'phase1_receipts'}
    else:
        if run.phase1 is None or run.phase1.core is not None:
            raise ValueError('original core seal is absent, premature or spent')
        decision = run.decision()
        if decision.state != 'await_core':
            raise ValueError('genuine original core is not at the current receipt boundary')
        inputs = [('core', 'phase1_core')]
        helpers = {'derive_core', 'core_schema', 'pair'}
    captured = {source: evidence.read_regular(paths[source], role,
        max_bytes=min(c.HARD_LIMITS['original_full_bytes'], run.selection.bounds()['max_input_bytes'])).captured for source, role in inputs}
    for source, role in inputs:
        _create(run.selection, role, captured[source].raw)
    sealed = {source: _captured(role, run.selection.role(role), captured[source].raw) for source, role in inputs}
    calls = [row['tool_use_id'] for row in report['checks'] if row['helper'] in helpers]
    if kind == 'seal_phase1':
        payload = {'full': c.pin_dict(sealed['full'].pin), 'original_receipt': c.pin_dict(sealed['receipt'].pin), 'helper_calls': calls}
        obs = _persist_observation(run, 'phase1_sealed', payload)
        body = {'kind': 'd4d_native_shared_phase1_seal', 'version': 1,
            'selection_sha256': run.selection.registration.pin.sha256, 'execution_sha256': run.binding.execution.pin.sha256,
            'session_id': run.binding.session_id, 'full': payload['full'], 'original_receipt': payload['original_receipt'],
            'observation': c.pin_dict(obs.pin)}
        seal = _create(run.selection, 'phase1_seal', c.canonical(body))
        record_payload = {'seal': c.pin_dict(seal.pin), 'full': payload['full'],
            'original_receipt': payload['original_receipt'], 'observation': c.pin_dict(obs.pin)}
        _append(run.selection, run.binding, run.history, 'phase1_sealed', record_payload)
    else:
        payload = {'core': c.pin_dict(sealed['core'].pin), 'helper_calls': calls}
        obs = _persist_observation(run, 'core_sealed', payload)
        body = {'kind': 'd4d_native_shared_core_seal', 'version': 1,
            'selection_sha256': run.selection.registration.pin.sha256, 'execution_sha256': run.binding.execution.pin.sha256,
            'session_id': run.binding.session_id, 'phase1_seal_sha256': run.phase1.seal.pin.sha256,
            'core': payload['core'], 'observation': c.pin_dict(obs.pin)}
        seal = _create(run.selection, 'core_seal', c.canonical(body))
        _append(run.selection, run.binding, run.history, 'core_sealed',
            {'seal': c.pin_dict(seal.pin), 'core': payload['core'], 'observation': c.pin_dict(obs.pin)})
    # A mutating host cannot make a result certify different bytes between
    # actual helper settlement and the original-copy publication.
    for source, role in inputs:
        if evidence.read_regular(paths[source], role, max_bytes=c.HARD_LIMITS['original_full_bytes']).captured != captured[source]:
            raise ValueError('original output changed during its exact observed seal')


def observe_request_read(run, identity):
    current = run.decision()
    if current is None or current.state != 'awaiting_response' or current.request is None:
        raise ValueError('request delivery has no current admitted outer request')
    trace = run.trace(); actual = trace.settled(identity)
    observed.complete_request_read(trace, actual, current.request)
    # An additional correct Read grants no new response identity. Retain the
    # first complete current Read rather than inventing independent deliveries.
    for item in run.observations:
        prior = _document(item.raw, 'current read observation')
        if (prior['observation_type'] == 'request_read'
                and prior['payload']['request'] == c.pin_dict(current.request.pin)):
            return
    _persist_observation(run, 'request_read', {'call': call_document(actual.call),
        'result': asdict(actual.result), 'result_event': asdict(actual.result_event),
        'request': c.pin_dict(current.request.pin), 'history_sha256': run.history.journal.pin.sha256})


def observe_response_intent(run, identity):
    from .native_shared_effects import classify_effect
    trace = run.trace(); request = trace.request(identity)
    inputs = _document(request.input_json, 'response Write')
    view = current_effect_view(run, exclude_pending=identity)
    if classify_effect(view, tool_name=request.tool_name, tool_input=inputs)[0] != 'prescribed':
        raise ValueError('current response Write is not permitted by actual captured effects')
    path = Path(view.response.path)
    if path.exists() or path.is_symlink():
        raise ValueError('first response destination already exists; no overwrite or retry')
    matches = [item for item in run.observations if item.pin.sha256 == view.request_read_observation_sha256]
    if len(matches) != 1:
        raise ValueError('response Write lacks one durable whole request observation')
    read_call = _call(_document(matches[0].raw, 'request Read observation')['payload']['call'])
    _require_completed_read_before_write(request, trace.settled(read_call.tool_use_id))
    _persist_observation(run, 'response_intent', {'request': c.pin_dict(view.request), 'response': asdict(view.response),
        'call': asdict(request.call), 'callback': asdict(request.callback), 'tool_use_id': identity,
        'input_json': request.input_json.decode('utf-8'), 'history_sha256': run.history.journal.pin.sha256,
        'read_observation': c.pin_dict(matches[0].pin)})


def observe_response_written(run, identity):
    current = run.decision(); trace = run.trace(); actual = trace.settled(identity)
    if current is None or current.state != 'awaiting_response' or current.response is None:
        raise ValueError('response settlement has no current selected destination')
    matches = [(item, doc['payload']) for item, doc in (
        (item, _document(item.raw, 'response intent')) for item in run.observations
    ) if doc['observation_type'] == 'response_intent' and doc['payload']['tool_use_id'] == identity]
    if len(matches) != 1:
        raise ValueError('response settlement lacks one preceding exact pre-grant intent')
    intent, payload = matches[0]
    response = run.reader.read('response', current.response.path)
    observed.first_response_write(trace, actual, response, intent_input_json=payload['input_json'].encode('utf-8'))
    obs = _persist_observation(run, 'response_written', {'call': call_document(actual.call),
        'result': asdict(actual.result), 'result_event': asdict(actual.result_event), 'response': c.pin_dict(response.pin),
        'intent_observation': c.pin_dict(intent.pin), 'history_sha256': run.history.journal.pin.sha256})
    request_hash = c.strict_json(current.request.raw, max_bytes=run.selection.bounds()['max_request_bytes'])['request_sha256']
    _append(run.selection, run.binding, run.history, 'response_consumed', {'cursor': asdict(current.cursor),
        'request_sha256': request_hash, 'response': c.pin_dict(response.pin),
        'read_observation': payload['read_observation'], 'response_observation': c.pin_dict(obs.pin)})


def observe_advance_settled(run, identity):
    trace = run.trace(); actual = trace.settled(identity)
    frame = evidence.event(run.transcript, actual.result_event)
    result = _document(frame.get('tool_use_result', {}).get('stdout', '').encode('utf-8'), 'advance stdout')
    observed.helper_result(trace, actual, result)
    admissions = [doc['payload'] for item in run.observations
        for doc in (_document(item.raw, 'advance admission'),)
        if doc['observation_type'] == 'advance_admitted'
        and doc['payload']['call']['tool_use_id'] == identity]
    if len(admissions) != 1:
        raise ValueError('advance settlement lacks one actual selected admission')
    _check_advance_acknowledgement(run, actual, result,
        before_history_sha256=admissions[0]['before_history_sha256'])
    if result['after_history_sha256'] != run.history.journal.pin.sha256:
        raise ValueError('advance result differs from actual current selected publication')
    _persist_observation(run, 'advance_settled', {'call': call_document(actual.call),
        'result': asdict(actual.result), 'result_event': asdict(actual.result_event), 'advance_result': result})


def selected_receipt_paths(selection_registration_path):
    """Explicit live S reaches only the paths captured in its already active E.

    RunSpec boundary: validated-caller

    RunSpec precondition: Caller supplies explicit active selection; _base reconstructs the execution and its guarded preparation before returning paths.
    """
    _, _, _, composition, spec = _base(str(selection_registration_path))
    paths = spec._agentic_artifact_paths
    return {'full': Path(paths['full']), 'receipt': Path(paths['receipt']),
            'provenance': Path(composition['policy']['post_final_recorder']['destination']),
            'core_dir': Path(paths['core']).parent}


def live_receipt_block(selection_registration_path, *, full_path, receipt_path):
    """    RunSpec boundary: validated-caller

    RunSpec precondition: Caller supplies explicit active selection and output paths; _load_live reconstructs the selected preparation before receipt assessment.
    """
    run = _load_live(str(selection_registration_path))
    phase_replay(run)
    block = _receipt_assessment(run, full_path=full_path, receipt_path=receipt_path)[0]
    return block


def live_provenance_block(selection_registration_path):
    """    RunSpec boundary: validated-caller

    RunSpec precondition: Caller supplies explicit active selection; _load_live reconstructs preparation and current final obligations before provenance assessment.
    """
    run = _load_live(str(selection_registration_path))
    phase, _ = phase_replay(run)
    required = {'draft', 'final_evidence', 'final_source_inventory', 'final_receipts', 'final_scope',
                'derive_final_core', 'core_schema', 'pair', 'full_schema', 'full_terms', 'audit_evidence'}
    if not required <= set(phase['current_checks']) or not phase['passed']:
        raise ValueError('recorder precedes actual current final helper obligations')
    from .native_shared_gates import current_evidence
    checked = current_evidence(run)
    if checked.get('checked') is not True or checked.get('findings') != []:
        raise ValueError('recorder current captured evidence did not pass')
    paths = run.spec._agentic_artifact_paths
    block, _, _ = _receipt_assessment(run, full_path=paths['full'], receipt_path=paths['receipt'])
    from .native_shared_receipts import final_receipt_floors
    if any(final_receipt_floors(block, run.selection).values()):
        raise ValueError('recorder current selected receipt floors did not pass')
    result = _provenance_block(run)
    return result


def _recorded_run(spec, record):
    from .native_shared_render import validate_metadata
    if type(record) is not dict:
        raise ValueError('native recorded reader requires one explicit provenance mapping')
    try:
        render_spec = record['prompts']['request']['spec']
        document = validate_metadata(render_spec)
    except (KeyError, TypeError) as exc:
        raise ValueError('native record lacks its complete selected render authority') from exc
    # An independent recorded read owns fresh derivations, not a process-global
    # catalog inherited from an earlier live receipt or provenance success.
    run = _load(document['registration_path'])
    if c.canonical(render_spec) != c.canonical(run.composition['render_spec']):
        raise ValueError('native record rendering differs from its observed execution composition')
    if spec is not None and c.canonical(spec.render_spec()) != c.canonical(render_spec):
        raise ValueError('caller spec differs from the explicit native record')
    if c.canonical(record.get('native_shared_generation')) != c.canonical(_provenance_block(run)):
        raise ValueError('native record stage/session identity differs from actual reconstructed evidence')
    phase, _ = phase_replay(run)
    if not phase['passed']:
        raise ValueError('native recorded stage chronology did not pass')
    return run


@dataclass(frozen=True)
class _NativeReceiptAssessment:
    """One reconstruction's assessment and selection, never a stored verdict."""
    raw: bytes
    selection: c.NativeSelectionCapture

    def block(self):
        import json
        return json.loads(self.raw)


def _selected_receipt_assessment(run, *, full_path, receipt_path):
    if type(run.selection) is not c.NativeSelectionCapture:
        raise ValueError('native receipt assessment requires its reconstructed selection')
    block = _receipt_assessment(run, full_path=full_path, receipt_path=receipt_path)[0]
    return _NativeReceiptAssessment(c.canonical(block), run.selection)


def _recorded_receipt_assessment(*, record, full_path, receipt_path):
    """Carry the selection from the same fresh recorded reconstruction to its gate.

    The saved receipt block is not authority. _recorded_run validates the saved
    selection and observed execution before either result is returned.
    """
    run = _recorded_run(None, record)
    return _selected_receipt_assessment(run, full_path=full_path, receipt_path=receipt_path)


def recorded_receipt_block(spec, *, record, full_path, receipt_path):
    """    RunSpec boundary: validated-caller

    RunSpec precondition: Caller supplies a validated spec or None plus explicit recorded provenance; _recorded_run reconstructs the recorded selection and compares render_spec before assessment.
    """
    run = _recorded_run(spec, record)
    return _selected_receipt_assessment(run, full_path=full_path, receipt_path=receipt_path).block()


def recorded_receipt_claims(spec, *, record, full_path, receipt_path, expected_block):
    """Claim sidecar from the same captured effective bytes as the checked block.

    RunSpec boundary: validated-caller

    RunSpec precondition: Caller supplies a validated spec or None and a checked receipt block; _recorded_run reconstructs selection and compares the recorded render_spec before deriving claims.
    """
    from . import native_shared_receipts as receipts
    from . import receipts as rc
    from .audit_omissions import _mapping
    run = _recorded_run(spec, record)
    block, full, effective = _receipt_assessment(run, full_path=full_path, receipt_path=receipt_path)
    if (block.get('native_receipt_stage') != 'final' or block.get('final_stage_complete') is not True
            or c.canonical(expected_block) != c.canonical(block)):
        raise ValueError('claim sidecar expected block differs from the same freshly captured final receipt assessment')
    _, _, _, _, _, bases, _, _ = receipts._inputs(run.selection, run.phase1, _catalogs=run._catalogs)
    return rc.claim_receipts(_mapping(effective.raw, 'native effective receipt'),
        _mapping(full.raw, 'native final full'), _mapping(run.phase1.full.raw, 'native original full'),
        identifier_bases=bases)
