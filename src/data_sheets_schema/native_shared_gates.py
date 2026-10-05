"""Fixed native-shared consumers of all fifteen native completion obligations.

Actual capture, callback admission and saved replay belong to the fixed
native_shared_results boundary. These adapters never select Python hooks or
substitute rendered/projection files for that captured evidence.
"""
from __future__ import annotations

from copy import deepcopy

from . import native_shared_contract as c
from .native_execution_gates import GATES


def _run(prepared):
    from .native_shared_capture import _CapturedRun
    run = prepared['run']
    if type(run) is not _CapturedRun or type(run.selection) is not c.NativeSelectionCapture:
        raise ValueError('native gates require the fixed captured selected run')
    return run


def _bytes(raw, limit, label):
    if type(raw) is not bytes or not raw or len(raw) > limit:
        raise ValueError(label + ' exceeds its nonempty captured byte bound')
    return raw


def _current(run, role):
    from .native_shared_current import current_artifact
    kind = {'final_full': 'full', 'final_core': 'core', 'final_report': 'report',
            'original_receipt_output': 'receipt'}[role]
    path = str(run.spec._agentic_artifact_paths[kind])
    item = current_artifact(run, role, path)
    if type(item) is not c.CapturedArtifact or item.pin.role != role or item.pin.path != path:
        raise ValueError('current native artifact differs from its fixed selected role')
    ceiling = 'original_full_bytes' if role == 'original_receipt_output' else 'input_bytes'
    _bytes(item.raw, min(run.selection.bounds()['max_input_bytes'], c.HARD_LIMITS[ceiling]), role)
    return item


def _final(prepared, role):
    run = _run(prepared)
    item = _current(run, role)
    # Both views must name the same captured bytes; projections are only for
    # unchanged consumers that still require real temporary file paths.
    raw = prepared['snapshot'].read(item.pin.path, role)
    if raw != item.raw:
        raise ValueError('native gate snapshot differs from selected current artifact')
    return raw


def current_evidence(run):
    """Byte-equivalent protocol-seven final_evidence over the selected capture.

    This is also usable at a live helper boundary through the fixed bounded
    current_artifact reader. Saved runs supply only immutable captured members.
    No declared success flag or ambient original/audit discovery is consulted.
    """
    from . import evidence_assertions as evidence
    from .api_runner import _audit_shape_problem
    from .native_shared_capture import _CapturedRun
    if type(run) is not _CapturedRun or type(run.selection) is not c.NativeSelectionCapture:
        raise ValueError('final evidence requires the fixed captured selected run')
    if run.phase1 is None or run.phase1.core is None:
        raise ValueError('final evidence precedes both actual original seals')
    selected = run.selection
    original_limit = min(selected.bounds()['max_input_bytes'], c.HARD_LIMITS['original_full_bytes'])
    raws = {'original_full': _bytes(run.phase1.full.raw, original_limit, 'original full'),
            'original_core': _bytes(run.phase1.core.raw, original_limit, 'original core'),
            'final_full': _current(run, 'final_full').raw,
            'final_core': _current(run, 'final_core').raw}
    texts = {name: raw.decode('utf-8') for name, raw in raws.items()}
    document = selected.document()
    if document['inputs']['source_manifest'] is None:
        raise ValueError('native final evidence requires its selected source manifest')
    source_raw = selected.raw('source_manifest')
    authority = {'source_manifest_raw': source_raw, 'project': document['run']['project']}
    chunks, pins = evidence.source_chunks_from_bytes(selected.raw('bundle'), selected.raw('chunk_manifest'))
    audit_raw = run.reader.read('audit', selected.role('audit')).raw
    audit = evidence.load_json(audit_raw)
    shape = _audit_shape_problem(audit) if isinstance(audit, dict) else 'audit must be an object'
    if shape:
        raise ValueError(shape)
    out = evidence.check_audit(audit, artifacts={k: v for k, v in texts.items() if k.startswith('original_')},
                               chunks=chunks, protocol_version=7, **authority)
    pins['source_manifest'] = c.sha(source_raw)
    pins['audit'] = c.sha(audit_raw)
    pins.update({key: c.sha(raw) for key, raw in raws.items()})
    out['findings'] += evidence.check_relationship_removals(audit, evidence.load_record(texts['original_full']),
        evidence.load_record(texts['final_full']), protocol_version=7, original_raw=raws['original_full'])
    report_raw = _current(run, 'final_report').raw
    pins['report'] = c.sha(report_raw)
    try:
        checked = evidence.check_report(report_raw.decode('utf-8'), artifacts=texts, chunks=chunks,
                                         protocol_version=7, **authority)
        out['assertions_checked'] += checked['assertions_checked']
        out['findings'] += checked['findings']
        if 'source_review_final' in checked:
            out['source_review_final'] = checked['source_review_final']
    except (ValueError, UnicodeError) as exc:
        out['findings'].append(evidence._problem('evidence_contract', str(exc)))
    out['artifact_sha256'] = pins
    out['scope'] = 'Declared evidence only; semantic support and omitted claims require independent review.'
    return out


def schema_gate(prepared, projections):
    from .native_shared_schema_gates import check_schemas
    return check_schemas(_run(prepared).selection, _final(prepared, 'final_full'), _final(prepared, 'final_core'))


def pair_gate(prepared, projections):
    from .native_shared_schema_gates import check_pair
    return check_pair(_run(prepared).selection, _final(prepared, 'final_full'), _final(prepared, 'final_core'))


def phase_gate(prepared):
    out = prepared['phase_report']
    if type(out) is not dict:
        raise ValueError('native phase report is not a freshly derived object')
    passed = (all(out.get(key) is True for key in ('checked', 'passed', 'complete', 'phase1_sealed',
              'core_sealed', 'assembly_complete', 'native_terminal'))
              and out.get('problems') == [] and out.get('pending_tool_ids') == [])
    return {'passed': passed, 'history': deepcopy(out)}


def saved_gate(prepared):
    if prepared.get('replay_complete') is not True:
        raise ValueError('complete native saved capture is unavailable')
    out = prepared['saved_result']
    if type(out) is not dict:
        raise ValueError('native saved result is not a freshly derived object')
    passed = (all(out.get(key) is True for key in ('checked', 'passed', 'additional_gate_passed',
              'recorder_completed_in_trace')) and out.get('problems') == [])
    return {'passed': passed, 'result': deepcopy(out)}


def tool_history(prepared):
    from .native_execution_gates import tool_history as settled_results
    phase = phase_gate(prepared)
    if phase['passed'] is not True:
        return {'passed': False, 'phase': phase, 'reason': 'native ordered helper obligations are incomplete'}
    # This fixed old reader accepts the exact new state's helper command map,
    # retaining strict unique calls, outcomes and exit-one draft corrections.
    result = settled_results(prepared)
    return {**result, 'phase': phase}


def receipt_gate(prepared):
    from . import canary, native_shared_receipts as receipts, native_shared_stage as stage
    run = _run(prepared)
    if run.phase1 is None or run.phase1.core is None:
        raise ValueError('native final receipts precede actual original seals')
    original = _current(run, 'original_receipt_output')
    if original.raw != run.phase1.original_receipt.raw:
        raise ValueError('ordinary native receipt differs from its sealed original')
    if prepared['snapshot'].read(original.pin.path, original.pin.role) != original.raw:
        raise ValueError('ordinary native receipt differs between captured views')
    assembly = run.reader.read('typed_assembly', run.selection.role('typed_assembly'))
    completion = stage.check_assembly(run.selection, run.binding, run.phase1, run.history, assembly.raw)
    effective = run.reader.read('effective_receipt', run.selection.role('effective_receipt'))
    if effective != completion.effective_receipt:
        raise ValueError('effective native receipt differs from reconstructed stage completion')
    block = receipts.check_final(run.selection, run.binding, run.phase1, completion,
        final_full=_final(prepared, 'final_full'), final_receipt=effective.raw)
    if block.get('checked') is not True or block.get('final_stage_complete') is not True:
        raise ValueError('native final receipt instrument did not complete')
    floors = canary.receipt_floors(block)
    return {'passed': not any(floors.values()), 'floors': floors, 'receipts': block,
            'original_receipt': c.pin_dict(original.pin), 'effective_receipt': c.pin_dict(effective.pin),
            'snapshot_basis': {'state': 'usable', 'path': run.phase1.full.pin.path,
                               'sha256': run.phase1.full.pin.sha256}}


def capture(value, controls, *, authority_inputs, registration_raw):
    from .native_shared_results import capture as selected_capture
    return selected_capture(value, controls, authority_inputs=authority_inputs, registration_raw=registration_raw)


def check(prepared, projections, runtime, controls, *, exit_code, shutdown, live,
          first_stop, runtime_authority, keep_awake, keep_awake_raw=None, runtime_authority_expected=None):
    from .native_gate_engine import check as common_check
    return common_check(prepared, projections, runtime, controls, kind='native_shared',
        exit_code=exit_code, shutdown=shutdown, live=live, first_stop=first_stop,
        runtime_authority=runtime_authority, keep_awake=keep_awake,
        keep_awake_raw=keep_awake_raw, runtime_authority_expected=runtime_authority_expected)
