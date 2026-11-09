"""Host-side native capture, saved replay and publication orchestration.

The flat pool contains complete raw files. Its summary never substitutes saved
passing flags for stage, phase, permission, attribution or final evidence checks.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

from . import native_shared_contract as c
from . import native_shared_capture as capture_api
from . import native_shared_capture_orchestration as capture_host
from . import native_shared_evidence as evidence
from . import native_shared_observations as observed
from . import native_attribution_results as inherited
from . import native_supervisor_gates as shared

from .native_shared_results import (Snapshot, _member, _captured_selection, rebuild,
    validate_file_basis, _read_pool, POOL_NAME, REPORT_KIND)

def _capture_member(snapshot, path, role, limit, expected=None):
    member = evidence.read_regular(str(path), role, max_bytes=limit)
    if expected is not None and member.captured.raw != expected:
        raise ValueError('actual file differs from its captured selected authority: ' + role)
    snapshot.add(member)
    return member


def capture(value, controls, *, authority_inputs, registration_raw):
    """One actual bounded capture, followed by the same saved-only reconstruction.

    RunSpec boundary: validated-caller

    RunSpec precondition: Caller supplies verified execution and complete controls; _load reconstructs selected preparation before bounded capture and saved replay.
    """
    composition = c.strict_json(value['composition_raw_json'].encode(), 'captured C', c.HARD_LIMITS['request_bytes'])
    selected_doc = c.parse_selection(composition['selection_raw_json'].encode('utf-8'))
    controls.require_complete()
    live = capture_host._load(selected_doc['registration_path'])
    snapshot = Snapshot(value['working_directory'], live.pool.members)
    selection = live.selection
    for item in (selection.registration, selection.receipt_policy, *selection.authority,
                 *(a for schema in selection.schemas for a in schema.sources)):
        _capture_member(snapshot, item.pin.path, item.pin.role, max(1, item.pin.bytes), item.raw)
    for role, path in authority_inputs.items():
        limit = c.HARD_LIMITS['permission_wire_bytes'] if role == 'permission_probe' else c.HARD_LIMITS['request_bytes']
        _capture_member(snapshot, path, 'authority:' + role, limit)
    attempt = Path(value['attempt_directory'])
    for name in ('registration.json', 'started.json', 'runtime-observation.json', 'stderr.txt'):
        _capture_member(snapshot, attempt / name, 'attempt:' + name,
            c.HARD_LIMITS['stream_bytes'] if name == 'stderr.txt' else c.HARD_LIMITS['request_bytes'])
    if snapshot.read(attempt / 'registration.json', 'execution') != registration_raw:
        raise ValueError('captured actual attempt registration differs from supplied E')
    for path, role, expected in ((value['composition'], 'composition', value['composition_raw_json'].encode()),
            (live.composition['instruction_path'], 'instruction', None),
            (live.composition['runtime_path'], 'runtime_declaration', live.composition['runtime_raw_json'].encode())):
        _capture_member(snapshot, path, role, c.HARD_LIMITS['request_bytes'], expected)
    paths = live.spec._agentic_artifact_paths
    for key, role in (('full', 'final_full'), ('core', 'final_core'), ('report', 'final_report'),
                      ('receipt', 'original_receipt_output')):
        item = capture_api.current_artifact(live, role, paths[key])
        _capture_member(snapshot, item.pin.path, role, max(1, item.pin.bytes), item.raw)
    _capture_member(snapshot, live.composition['policy']['post_final_recorder']['destination'],
                    'provenance', c.HARD_LIMITS['request_bytes'])
    # Capture every explicit tool path before the frozen FileAccess replay.
    # Stage destinations are already part of the complete closed pool.
    inputs = set(live.composition['policy']['readonly_lookups']['inputs'])
    outputs = tuple(Path(p) for p in live.composition['policy']['readonly_lookups']['output_directories'])
    trace = live.trace()
    for _, _, call in trace.calls.values():
        if call['name'] in ('Read', 'Write'):
            literal = call['input'].get('file_path')
            c.canonical_path(literal, 'observed file target')
            if literal not in snapshot.raw:
                if literal not in inputs and not any(p in Path(literal).parents for p in outputs):
                    raise ValueError('completed observed file target is outside selected captured authority')
                _capture_member(snapshot, literal, 'observed_file', c.HARD_LIMITS['input_bytes'])
        elif call['name'] == 'Bash':
            lookups, grammar = controls['native_readonly'], controls['native_command_policy']
            for part in lookups.pipeline_parts(call['input']['command']):
                words, _ = grammar._simple_command(part)
                if words and words[0] in lookups.PROGRAMS:
                    for name in lookups._paths(words) or ():
                        if name == '-': continue
                        path = Path(name)
                        path = path if path.is_absolute() else Path(value['working_directory']) / path
                        c.canonical_path(str(path), 'lookup target')
                        if str(path) not in snapshot.raw:
                            if str(path) not in inputs and not any(p in path.parents for p in outputs):
                                raise ValueError('ordinary lookup names uncaptured selected authority')
                            _capture_member(snapshot, str(path), 'lookup_file', c.HARD_LIMITS['input_bytes'])
    pool = evidence.CapturePool(tuple(snapshot.members.values()), live.pool.stream_bindings)
    if sum(m.captured.pin.bytes for m in pool.members) > selection.bounds()['max_evidence_bytes']:
        raise ValueError('complete capture exceeds the selected evidence bound')
    snapshot.verify_unchanged()
    snapshot.sealed = True
    return prepare(pool, value, controls, snapshot=snapshot)


def _readonly(command, policy, snapshot, controls):
    """Frozen lookup grammar with captured path resolution, never live resolve."""
    lookups, grammar = controls['native_readonly'], controls['native_command_policy']
    if not lookups._literal_arguments(command):
        return False
    paths = policy['readonly_lookups']
    inputs, outputs = set(paths['inputs']), tuple(Path(p) for p in paths['output_directories'])
    try:
        for position, part in enumerate(lookups.pipeline_parts(command)):
            words, _ = grammar._simple_command(part)
            if not words or words[0] not in lookups.PROGRAMS:
                return False
            files = lookups._paths(words)
            if files is None or (position == 0 and (not files or '-' in files)):
                return False
            for name in files:
                if name == '-' and position:
                    continue
                target = snapshot.path(name)
                if str(target) not in inputs and not any(folder in target.parents for folder in outputs):
                    return False
        return True
    except (ValueError, TypeError, KeyError):
        return False


class _CapturedReadonly:
    """Frozen-reader compatibility surface; each lookup rechecks the grammar."""
    def __init__(self, policy, snapshot, controls):
        self.policy, self.snapshot, self.controls = policy, snapshot, controls

    def get(self, command, default=False):
        return _readonly(command, self.policy, self.snapshot, self.controls)


def _classify_saved(command, policy, snapshot, controls):
    """Classify one occurrence afresh, resolving paths only in captured bytes."""
    if command in policy['native_shared_helpers'].values():
        from .native_execution_authority_v2 import loaded_verified_package_module
        with controls.loaded_classifier() as classifier_projection, loaded_verified_package_module('data_sheets_schema.native_shared_policy',
                package_sources=controls.package_sources) as policy_consumer:
            return policy_consumer.classify_bash(command, policy['python'], set(), policy,
                                                classifier_projection=classifier_projection)
    if not _readonly(command, policy, snapshot, controls):
        raise ValueError('saved history has an unsupported ordinary Bash command')
    native = controls['run_native_canary']
    problem = native._too_complex(command) or (
        'an argument naming a process environment, which the runtime refuses'
        if any(native._PROC_ENVIRON.search(word)
            for part in controls['native_readonly'].pipeline_parts(command)
            for word in (controls['native_command_policy']._simple_command(part)[0] or ())) else None)
    if problem:
        return ('not_prescribed',
            'a registered read-only lookup, spelled so the runtime refuses it: '
            + problem + '. This refusal does not disqualify the attempt; quote each '
            'argument with single quotes and name literal paths, or use the Read tool')
    return ('prescribed', "a registered read-only lookup of this job's inputs or outputs")


def prepare(pool, value, controls, *, snapshot=None, _catalogs=None):
    """    RunSpec boundary: validated-caller

    RunSpec precondition: Caller supplies captured pool, verified execution and complete controls; rebuild validates the captured render spec before result assessment.
    """
    from . import native_shared_attribution as attribution
    from . import native_shared_gates as gates
    from .audit_omissions import _mapping
    controls.require_complete()
    run = rebuild(pool, value, _catalogs=_catalogs)
    if snapshot is None:
        snapshot = Snapshot(value['working_directory'], pool.members)
        snapshot.sealed = True
    paths = run.spec._agentic_artifact_paths
    attempt = Path(value['attempt_directory'])
    exact_raw = ((value['composition'], value['composition_raw_json'].encode()),
        (run.composition['runtime_path'], run.composition['runtime_raw_json'].encode()),
        (attempt / 'registration.json', run.binding.execution.raw),
        (attempt / 'started.json', run.binding.started.raw))
    for path, raw in exact_raw:
        if snapshot.read(path, 'selected_authority') != raw:
            raise ValueError('saved physical authority differs from the exact selected raw identity')
    if c.sha(snapshot.read(run.composition['instruction_path'], 'instruction')) != value['instruction_sha256']:
        raise ValueError('saved instruction differs from execution authority')
    state = attribution.saved(run.selection, execution_raw=run.binding.execution.raw,
        spec=run.spec, composition_raw=value['composition_raw_json'].encode(),
        captured_instruction=_member(pool, 'instruction', run.composition['instruction_path']).captured,
        final_full=capture_api.current_artifact(run, 'final_full', paths['full']),
        final_report=capture_api.current_artifact(run, 'final_report', paths['report']))
    events = [row for _, _, row in observed.rows(run.transcript)]
    records = [row for _, _, row in observed.rows(run.control)]
    policy = run.composition['policy']
    for _, _, call in run.trace().calls.values():
        if call['name'] != 'Bash':
            continue
        command = call['input'].get('command')
        _classify_saved(command, policy, snapshot, controls)
    final_result = gates.current_evidence(run)
    phase, _ = capture_api.phase_replay(run, complete=True)
    record = _mapping(snapshot.read(policy['post_final_recorder']['destination'], 'provenance'), 'native provenance')
    if (c.canonical(record.get('native_shared_generation')) != c.canonical(capture_api._provenance_block(run))
            or c.canonical(record.get('prompts', {}).get('request', {}).get('spec')) != c.canonical(run.composition['render_spec'])):
        raise ValueError('saved native provenance differs from exact selected stage/render authority')
    prepared = {'run': run, 'pool': pool, 'value': value, 'snapshot': snapshot, 'state': state,
        'composition_raw': value['composition_raw_json'].encode(), 'composition': run.composition,
        'events': events, 'records': records, 'policy': policy,
        'record': record, 'final_result': final_result, 'phase_report': phase,
        'replay_complete': True}
    prepared['saved_result'] = check_capture(prepared, controls=controls)
    return prepared


def check_capture(prepared, *, controls):
    """Recompute control, phase, immutable-stage and attribution obligations."""
    controls.require_complete()
    run, policy = prepared['run'], prepared['policy']
    def classify(command, python, programs, supplied):
        if python != policy['python'] or c.canonical(supplied) != c.canonical(policy):
            raise ValueError('saved classifier differs from exact selected policy')
        return _classify_saved(command, policy, prepared['snapshot'], controls)
    files = inherited.CapturedFiles(prepared['snapshot'], policy, controls)
    control = inherited._control_history(prepared['events'], prepared['records'], policy, classify, files, controls)
    lifecycle = inherited._control_lifecycle(prepared['events'], prepared['records'], controls)
    draft, final, recorder = inherited._saved_draft(
        {**prepared, 'readonly': _CapturedReadonly(policy, prepared['snapshot'], controls)}, classify)
    problems = [*control['problems'], *lifecycle['problems'], *draft['problems']]
    from . import native_shared_policy, native_shared_effects
    draft_seen = False
    for line, _, frame in observed.rows(run.transcript):
        for block in frame.get('message', {}).get('content', ()):
            if (type(block) is dict and block.get('type') == 'tool_use' and block.get('name') == 'Bash'
                    and block.get('input', {}).get('command') == policy['native_shared_helpers']['draft']):
                draft_seen = True
        if frame.get('type') != 'control_request':
            continue
        data = frame['request']['input']
        current = capture_api.at_callback(run, line)
        decision = current.decision()
        view = capture_api._effect_view_from_decision(current, decision, correction_window=draft_seen,
            exclude_pending=data['tool_use_id'])
        if native_shared_policy.stage_overlay_governs(view, tool_name=data['tool_name'],
                tool_input=data['tool_input'], policy=policy):
            classification, basis = native_shared_effects.classify_effect(view,
                tool_name=data['tool_name'], tool_input=data['tool_input'])
            if classification != 'prescribed':
                problems.append('saved callback violates the actual current stage effect: ' + basis)
    if c.canonical(final) != c.canonical(prepared['final_result']):
        problems.append('final evidence differs from freshly checked saved bytes')
    if not prepared['phase_report']['passed']:
        problems.append('complete native shared phase history did not pass')
    if final is None or final.get('checked') is not True or final.get('findings') != []:
        problems.append('actual final evidence did not pass')
    trace = run.trace()
    if trace.pending() or trace.terminal is None:
        problems.append('native saved tool history is not terminal and settled')
    terminals = [e for e in prepared['events'] if e.get('type') == 'result']
    if len(terminals) != 1 or terminals[0].get('permission_denials') != []:
        problems.append('completed selected history contains denials or lacks explicit empty denial accounting')
    return {'checked': True, 'passed': not problems and draft['draft_gate_passed'] and recorder,
        'additional_gate_passed': not problems and draft['draft_gate_passed'] and recorder,
        'recorder_completed_in_trace': recorder, 'problems': problems, 'draft': draft,
        'control': control, 'lifecycle': lifecycle, 'phase': prepared['phase_report'],
        'scope': 'Captured native stage/control completion, not scientific support or authenticated provider evidence.'}


def incomplete_capture(composition_path, attempt, adapter, reason):
    """Retain bounded partial evidence; never promote a stopped capture."""
    snapshot = Snapshot(adapter.value['working_directory'])
    problems = [reason]
    paths = [(str(Path(attempt) / name), name) for name in
             ('transcript.jsonl', 'control.jsonl', 'stderr.txt', 'runtime-observation.json')]
    paths += [(str(composition_path), 'composition')]
    for path, role in paths:
        try:
            _capture_member(snapshot, path, role, c.HARD_LIMITS['stream_bytes'])
        except (OSError, ValueError) as exc:
            problems.append(role + ': ' + str(exc))
    def rows(name):
        try:
            return inherited._rows(snapshot.read(Path(attempt) / name, name), name)
        except (OSError, ValueError, UnicodeError):
            return []
    snapshot.verify_unchanged(); snapshot.sealed = True
    return {'snapshot': snapshot, 'state': SimpleNamespace(spec=adapter.spec, reg=adapter.state.reg),
        'events': rows('transcript.jsonl'), 'records': rows('control.jsonl'), 'policy': adapter.policy,
        'replay_complete': False, 'capture_problems': problems, 'record': None, 'final_result': None}


project = shared.project


def write_report(prepared, destination):
    from .native_attempt_supervisor import durable_new
    value = prepared['value']
    expected = Path(value['evidence_directory']) / 'attribution-replay.json'
    if Path(destination) != expected:
        raise ValueError('native saved report must use its exact E evidence destination')
    pool_raw = prepared['pool'].encode()
    prepared['snapshot'].verify_unchanged()
    durable_new(expected.parent / POOL_NAME, pool_raw)
    summary = {'kind': REPORT_KIND, 'version': 1, 'execution_sha256': prepared['run'].binding.execution.pin.sha256,
        'pool': {'path': str(expected.parent / POOL_NAME), 'bytes': len(pool_raw), 'sha256': c.sha(pool_raw)},
        'result': prepared['saved_result']}
    durable_new(expected, c.canonical(summary))
    return summary


def require_saved_basis(value, result):
    """Additional fixed readback; failed attempts never gain success by omission.

    RunSpec boundary: validated-caller

    RunSpec precondition: Common reader has checked retained report bytes; saved reconstruction validates the captured render spec and never upgrades failed attempts to success.
    """
    # The common reader has already checked a declared report from the bytes
    # retained by its file validation loop, including an unavailable capture.
    if 'receipt_origin_reporting' not in value and 'receipt_origin' in result['gates']['receipts']:
        raise ValueError('undeclared receipt-origin gate extension')
    additional = result.get('additional_report')
    if additional is None:
        if result['runtime_gates_passed']:
            raise ValueError('complete native shared result lacks captured reconstruction')
        return
    path = Path(value['evidence_directory']) / 'attribution-replay.json'
    summary = c.strict_json(evidence.read_regular(str(path), 'saved_report',
        max_bytes=c.HARD_LIMITS['request_bytes']).captured.raw, 'saved report', c.HARD_LIMITS['request_bytes'])
    c.exact(summary, {'kind', 'version', 'execution_sha256', 'pool', 'result'}, 'saved report')
    if (summary['kind'] != REPORT_KIND or type(summary['version']) is not int or summary['version'] != 1
            or summary['execution_sha256'] != result['registration_sha256']):
        raise ValueError('native saved reconstruction belongs to another execution')
    pin = c.exact(summary['pool'], {'path', 'bytes', 'sha256'}, 'saved pool identity')
    if pin['path'] != str(path.parent / POOL_NAME):
        raise ValueError('native saved pool path differs from its fixed evidence role')
    c.positive_int(pin['bytes'], 'saved pool size', c.HARD_LIMITS['evidence_wire_bytes'])
    # Pool is read through the dedicated large-wire bound, not legacy 8MiB.
    raw = _read_pool(pin['path'], pin['bytes'])
    if len(raw) != pin['bytes'] or c.sha(raw) != pin['sha256']:
        raise ValueError('saved pool differs from its complete raw identity')
    from .native_execution_capabilities import loaded_capabilities
    from . import native_shared_gates as gates
    from .native_shared_execution_orchestration import expected_runtime_observation
    with loaded_capabilities(value['dependencies']) as controls:
        prepared = prepare(evidence.decode(raw), value, controls)
        if c.canonical(prepared['saved_result']) != c.canonical(summary['result']):
            raise ValueError('saved native result differs from fresh byte-only reconstruction')
        snapshot = prepared['snapshot']
        for actual, key in ((snapshot.identity(), 'captured_files'), (snapshot.metadata, 'captured_metadata'),
                (snapshot.aliases, 'captured_aliases'), (snapshot.alias_metadata, 'captured_alias_metadata')):
            if c.canonical(actual) != c.canonical(result[key]):
                raise ValueError('flat captured pool differs from final captured file identities or metadata')
        if result['runtime_gates_passed'] and not prepared['saved_result']['passed']:
            raise ValueError('native completion contradicts fresh saved stage/control reconstruction')
        # Re-run every original obligation. Existing exclusive projections are
        # checked against complete captured bytes before the unchanged file-based
        # observation/accounting consumers can open them.
        projections = {}
        for index, (original, body) in enumerate(sorted(snapshot.raw.items())):
            projected = path.parent / 'captured' / str(index) / Path(original).name
            actual = evidence.read_regular(str(projected), 'saved_projection', max_bytes=max(1, len(body)))
            if actual.captured.raw != body:
                raise ValueError('saved projection differs from its exact flat captured member')
            projections[original] = projected
        fresh_live = {**prepared['saved_result']['draft'],
            'recorder_completed': prepared['saved_result']['recorder_completed_in_trace'],
            'controller_stop': None if prepared['saved_result']['passed'] else 'saved reconstruction failed'}
        cleanup = result['lifecycle_artifacts'].get('keep-awake.json')
        cleanup_raw = (evidence.read_regular(cleanup['path'], 'cleanup',
            max_bytes=c.HARD_LIMITS['input_bytes']).captured.raw if cleanup is not None else None)
        fresh = gates.check(prepared, projections,
            {**value['runtime'], 'attempt_directory': value['attempt_directory']}, controls.gate_members,
            exit_code=result['child_exit_code'], shutdown=result['shutdown'], live=fresh_live,
            first_stop=result['first_stop'], runtime_authority=result['runtime_observation'],
            keep_awake=result['keep_awake'], keep_awake_raw=cleanup_raw,
            runtime_authority_expected=expected_runtime_observation(value))
        if 'receipt_origin_reporting' in value:
            from .native_receipt_origin import attach_prepared
            fresh = attach_prepared(value, fresh, prepared)
    for name, recomputed in fresh.items():
        old = result['gates'][name]
        if old['passed'] and (recomputed.get('checked') is not True or recomputed.get('passed') is not True):
            raise ValueError('saved passing native gate contradicts fresh reconstruction: ' + name)
        if name in ('saved_attribution', 'phase_history', 'tool_history', 'schema', 'pair', 'receipts', 'evidence'):
            if c.canonical(old) != c.canonical(recomputed):
                raise ValueError('saved native semantic gate differs from fresh captured reconstruction: ' + name)
    for original, projected in projections.items():
        if evidence.read_regular(str(projected), 'saved_projection',
                max_bytes=max(1, len(snapshot.raw[original]))).captured.raw != snapshot.raw[original]:
            raise ValueError('saved projection changed during independent gate reconstruction')
