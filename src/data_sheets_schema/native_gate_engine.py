"""Private fixed gate orchestration for the shared v2 execution route.

Fixed neutral checks retain ordinary result/error fields. The fixed consumer
supplies captured S schema/receipt/stage
semantics; neither callers nor serialized evidence can choose Python hooks.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path


def receipt_observation(transcript, bundle, receipt, manifest):
    """Report original receipt claims against successful file-tool windows only.

    A permitted shell read is intentionally counted as unopened by this
    instrument. Neither its count nor that limitation is an acceptance floor.
    """
    from data_sheets_schema import agentic_observed
    out = agentic_observed.observe([transcript], bundle, receipt=receipt, manifest=manifest)
    out['receipt_chunks_unopened_basis'] = {
        'mode': 'reported_only', 'receipt': 'original_phase1_receipt',
        'reads': 'successful_file_tool_windows', 'permitted_shell_reads_count_as_unopened': True}
    return out


def audit_counts(prepared):
    """Compare captured report totals with a freshly reconstructed typed audit.

    This row never borrows a successful receipt, phase or evidence verdict.
    Missing inputs remain an explicit unchecked refusal, including when the
    shared report instrument merely reports that no total was stated.
    """
    from . import native_shared_contract as c
    from . import native_shared_gates as native
    from . import native_shared_stage as stage
    from .report_audit_totals import check_report_audit_totals
    row = {'checked': False, 'passed': False, 'compared_artifacts': {},
           'comparison': None, 'reason': None}
    try:
        final = prepared.get('final_result')
        if (type(final) is not dict or type(final.get('checked')) is not bool
                or type(final.get('findings')) is not list):
            raise ValueError('native final evidence is missing or malformed')
        run = native._run(prepared)
        if run.phase1 is None or run.phase1.core is None:
            raise ValueError('audit counts precede the sealed originals')
        if run.reader.pool is None:
            raise ValueError('audit counts require captured artifacts, not live fallback')
        assembly = run.reader.read('typed_assembly', run.selection.role('typed_assembly'))
        row['compared_artifacts']['typed_assembly'] = c.pin_dict(assembly.pin)
        completion = stage.check_assembly(run.selection, run.binding, run.phase1,
                                          run.history, assembly.raw)
        audit = run.reader.read('audit', run.selection.role('audit'))
        row['compared_artifacts']['derived_audit'] = c.pin_dict(completion.audit.pin)
        if audit != completion.audit:
            raise ValueError('captured audit differs from the freshly derived assembly audit')
        report = native._current(run, 'final_report')
        row['compared_artifacts']['final_report'] = c.pin_dict(report.pin)
        for item in (assembly, audit, report):
            if prepared['snapshot'].read(item.pin.path, item.pin.role) != item.raw:
                raise ValueError('audit-count artifacts differ between captured views')
        audit_document = c.strict_json(audit.raw, 'derived native audit',
                                       c.HARD_LIMITS['assembly_bytes'])
        # The shared instrument accepts strings or paths. A trailing newline
        # forces its text branch even if a one-line report spells a live path.
        compared = check_report_audit_totals(report.raw.decode('utf-8') + '\n', audit_document)
        row['comparison'] = compared
        typed_totals = (type(compared.get('stated_total')) is int
                        and type(compared.get('computed_total')) is int
                        and compared['stated_total'] >= 0 and compared['computed_total'] >= 0)
        row['checked'] = compared.get('checked') is True and typed_totals
        row['passed'] = (row['checked'] and compared.get('status') == 'consistent'
                         and compared['stated_total'] == compared['computed_total']
                         and compared.get('mismatches') == [] and compared.get('findings') == [])
        if not row['passed']:
            row['reason'] = (compared.get('reason') or
                             'report audit totals are missing, contradictory or unequal')
    except (ValueError, TypeError, KeyError, AttributeError, UnicodeError) as exc:
        row['checked'] = row['passed'] = False
        row['reason'] = type(exc).__name__ + ': ' + str(exc)
    return row


def evidence_gate(prepared):
    """Retain the evidence obligation and its independent audit-count row."""
    counts = audit_counts(prepared)
    final = prepared.get('final_result')
    checked = type(final) is dict and final.get('checked') is True and counts['checked'] is True
    return {'checked': checked,
            'passed': checked and final.get('findings') == [] and counts['passed'] is True,
            'result': deepcopy(final), 'audit_counts': counts}


def check(prepared, projections, runtime, controls, *, kind, exit_code, shutdown, live,
          first_stop, runtime_authority, keep_awake, keep_awake_raw=None, runtime_authority_expected=None):
    """Run the fixed obligations; only selected semantic readers differ."""
    from data_sheets_schema import native_shared_gate_primitives as neutral
    if kind != 'native_shared':
        raise ValueError('unknown private native gate contract')
    # This consumer gets only four reviewed accounting/observation members.
    # In particular no launcher module or execute_child carrier is admitted.
    if (type(controls) is not dict or set(controls) != {
            'model_accounting', 'LIMIT_KEYS', 'observed_efforts', 'observation_problems'}
            or any(not callable(controls[name]) for name in
                   ('model_accounting', 'observed_efforts', 'observation_problems'))
            or type(controls['LIMIT_KEYS']) is not tuple
            or not controls['LIMIT_KEYS']
            or any(type(key) is not str for key in controls['LIMIT_KEYS'])):
        raise ValueError('native gates require exactly their four pure helper members')
    if 'controls' in prepared or 'readonly' in prepared:
        raise ValueError('native gates refuse orchestration capability carriers')
    from data_sheets_schema import native_shared_gates as native
    runtime_observation_result = neutral.runtime_observation_result
    cleanup_result = neutral.cleanup_result
    from data_sheets_schema import agentic_observed
    snap, spec = prepared['snapshot'], prepared['state'].spec
    events, policy = prepared['events'], prepared['policy']
    results = {}

    def projected(path):
        return projections[str(snap.path(path))]

    def run(name, function):
        try:
            result = function()
            if not isinstance(result, dict) or type(result.get('passed')) is not bool:
                raise ValueError('gate returned no explicit boolean verdict')
            results[name] = {'checked': True, **result}
        except Exception as exc:
            results[name] = {'checked': False, 'passed': False, 'reason': f'{type(exc).__name__}: {exc}'}

    def terminal_gate():
        from .native_model_aliases import model_aliases, require_frame_models, require_model_usage
        aliases = model_aliases(runtime)
        init = [e for e in events if e.get('type') == 'system' and e.get('subtype') == 'init']
        final = [e for e in events if e.get('type') == 'result']
        if len(init) != 1 or len(final) != 1:
            raise ValueError('one exact initialization and terminal result are required')
        one, last = init[0], final[0]
        session = one.get('session_id')
        if (not isinstance(session, str) or not session or one.get('cwd') != prepared['state'].reg['working_directory']
                or any(e.get('session_id') != session for e in events if e.get('type') in ('assistant', 'user', 'result'))):
            raise ValueError('native stream session or initialization cwd differs from this selected attempt')
        if (one.get('model') != aliases['requested']
                or one.get('apiKeySource') != runtime['auth']['expected_api_key_source']
                or one.get('claude_code_version') != runtime['executable']['init_version']
                or not isinstance(one.get('tools'), list) or sorted(one['tools']) != ['Bash', 'Read', 'Write']):
            raise ValueError('native initialization differs from the supplied runtime identity')
        for event in events:
            if event.get('type') not in ('assistant', 'user', 'result'):
                continue
            if event.get('parent_tool_use_id') is not None:
                raise ValueError('child-agent frames cannot certify the selected native parent attempt')
            message = event.get('message')
            if isinstance(message, dict):
                if 'role' in message and message['role'] != event['type']:
                    raise ValueError('native message role contradicts its stream frame')
            require_frame_models(event, aliases)
        require_model_usage(last, aliases)
        if ('permissionMode' in one and one['permissionMode'] != 'dontAsk'):
            raise ValueError('native initialization permission mode contradicts the selected argv')
        if (type(exit_code) is not int or exit_code != 0 or last.get('is_error') is not False
                or last.get('terminal_reason') != 'completed' or last.get('stop_reason') != 'end_turn'
                or 'subtype' in last and last['subtype'] != 'success'
                or last.get('error') is not None):
            raise ValueError('native child did not explicitly complete successfully')
        return {'passed': True, 'init': one, 'terminal': last}

    def accounting():
        from decimal import Decimal
        from .native_model_aliases import model_aliases, require_model_usage
        aliases = model_aliases(runtime)
        finals = [e for e in events if e.get('type') == 'result']
        if len(finals) != 1:
            raise ValueError('native model accounting requires one terminal result')
        terminal = finals[0]
        require_model_usage(terminal, aliases)
        own, auxiliary = controls['model_accounting'](terminal, {'model': {
            'model': runtime['model'], 'auxiliary_models_permitted': runtime['auxiliary_models']}})
        usage = terminal.get('usage')
        keys = ('input_tokens', 'output_tokens', 'cache_read_input_tokens', 'cache_creation_input_tokens')
        if not isinstance(usage, dict) or any(type(usage.get(k)) is not int or usage[k] < 0 for k in keys):
            raise ValueError('terminal usage is incomplete or not nonnegative integers')
        for entry in [own, *auxiliary.values()]:
            if any(type(entry.get(k)) is not int or entry[k] < 0 for k in
                   ('inputTokens', 'outputTokens', 'cacheReadInputTokens', 'cacheCreationInputTokens')):
                raise ValueError('per-model usage is incomplete or not nonnegative integers')
        limits = {key: own.get(key) for key in controls['LIMIT_KEYS']}
        if (any(type(v) is not int for v in limits.values())
                or neutral._encoded(limits) != neutral._encoded(runtime['limits'])):
            raise ValueError('observed runtime limits differ from the registered assertions')
        efforts = controls['observed_efforts'](projected(Path(runtime['attempt_directory']) / 'control.jsonl'))
        if efforts != [runtime['effort']]:
            raise ValueError('observed effort differs from registration')
        cost = terminal.get('total_cost_usd')
        if type(cost) not in (int, float) or cost < 0 or cost != cost or cost == float('inf'):
            raise ValueError('runtime cost estimate is missing or unusable')
        if Decimal(str(cost)) > Decimal(runtime['budget_guard_usd']):
            raise ValueError('reported runtime cost exceeds the registered budget guard')
        model_tokens = sum(entry['outputTokens'] for entry in [own, *auxiliary.values()])
        return {'passed': True, 'basis': 'runtime-reported usage and cost estimates; not provider billing or proxy metering',
                'usage': usage, 'registered_model': own, 'auxiliary_models': auxiliary,
                'runtime_cost_estimate_usd': cost, 'efforts': efforts, 'limits': limits,
                'accounting_reconciliation': {'terminal_output_tokens': usage['output_tokens'],
                    'model_usage_output_tokens': model_tokens, 'difference': usage['output_tokens'] - model_tokens}}

    def schemas():
        return native.schema_gate(prepared, projections)

    def paired():
        return native.pair_gate(prepared, projections)

    def observed():
        out = receipt_observation(projected(Path(runtime['attempt_directory']) / 'transcript.jsonl'),
            projected(spec.bundle), projected(spec._agentic_artifact_paths['receipt']),
            projected(spec.chunk_manifest))
        problems = controls['observation_problems'](out)
        return {'passed': not problems, 'observation': out, 'problems': problems}

    def phase():
        return native.phase_gate(prepared)

    def saved():
        return native.saved_gate(prepared)

    run('terminal', terminal_gate)
    run('shutdown', lambda: {'passed': bool(shutdown) and shutdown.get('control_initialized') is True
        and shutdown.get('control_shutdown_complete') is True
        and type(shutdown.get('unfinished_control_workers')) is int and shutdown['unfinished_control_workers'] == 0,
        'state': shutdown})
    run('first_stop', lambda: {'passed': first_stop is None, 'reason': first_stop})
    run('live_attribution', lambda: {'passed': live.get('draft_gate_passed') is True
        and live.get('recorder_completed') is True and live.get('controller_stop') is None, 'result': live})
    run('saved_attribution', saved)
    run('phase_history', phase)
    run('tool_history', lambda: native.tool_history(prepared))
    run('schema', schemas)
    run('pair', paired)
    run('receipts', lambda: native.receipt_gate(prepared))
    run('evidence', lambda: evidence_gate(prepared))
    run('observation', observed)
    run('accounting', accounting)
    run('runtime_authority', lambda: runtime_observation_result(
        snap.read(Path(runtime['attempt_directory']) / 'runtime-observation.json',
                  'runtime_observation_approval'), runtime_authority, runtime_authority_expected))
    run('keep_awake', lambda: cleanup_result(keep_awake_raw, keep_awake, runtime['keep_awake']))
    return results
