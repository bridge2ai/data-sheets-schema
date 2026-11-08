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
        init = [e for e in events if e.get('type') == 'system' and e.get('subtype') == 'init']
        final = [e for e in events if e.get('type') == 'result']
        if len(init) != 1 or len(final) != 1:
            raise ValueError('one exact initialization and terminal result are required')
        one, last = init[0], final[0]
        session = one.get('session_id')
        if (not isinstance(session, str) or not session or one.get('cwd') != prepared['state'].reg['working_directory']
                or any(e.get('session_id') != session for e in events if e.get('type') in ('assistant', 'user', 'result'))):
            raise ValueError('native stream session or initialization cwd differs from this selected attempt')
        if (one.get('model') != runtime['model']
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
                if 'model' in message and message['model'] != runtime['model']:
                    raise ValueError('native assistant model contradicts the selected primary')
            if 'model' in event and event['model'] != runtime['model']:
                raise ValueError('native stream model contradicts the selected primary')
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
        finals = [e for e in events if e.get('type') == 'result']
        if len(finals) != 1:
            raise ValueError('native model accounting requires one terminal result')
        terminal = finals[0]
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
    run('evidence', lambda: {'passed': prepared['final_result'].get('checked') is True
        and prepared['final_result'].get('findings') == [], 'result': deepcopy(prepared['final_result'])})
    run('observation', observed)
    run('accounting', accounting)
    run('runtime_authority', lambda: runtime_observation_result(
        snap.read(Path(runtime['attempt_directory']) / 'runtime-observation.json',
                  'runtime_observation_approval'), runtime_authority, runtime_authority_expected))
    run('keep_awake', lambda: cleanup_result(keep_awake_raw, keep_awake, runtime['keep_awake']))
    return results
