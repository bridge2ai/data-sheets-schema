"""One captured basis for the distinct native execution consumer (#4334).

The neutral supervisor's fixed recipe and synthetic accounting stay unchanged.
This adapter uses the same receipt, schema, pair, evidence and observation
algorithms, with correction-capable history and actual runtime accounting.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from data_sheets_schema import native_attribution_registration as draft
from data_sheets_schema import native_attribution_results as replay
from data_sheets_schema import native_supervisor_gates as shared

GATES = ('terminal', 'shutdown', 'first_stop', 'live_attribution', 'saved_attribution',
         'phase_history', 'tool_history', 'schema', 'pair', 'receipts', 'evidence',
         'observation', 'accounting', 'runtime_authority', 'keep_awake')


def capture(value, controls, *, authority_inputs, registration_raw):
    """Capture selected native authority and outputs; never invent a recipe."""
    from data_sheets_schema import api_runner as api, receipts
    attempt = Path(value['attempt_directory'])
    prepared = replay.capture(value['composition'], attempt / 'transcript.jsonl',
                              attempt / 'control.jsonl', config_root=attempt / 'cli_config')
    snap, spec = prepared['snapshot'], prepared['state'].spec
    snap.sealed = False
    for role, path in authority_inputs.items():
        snap.read(path, 'native_execution_' + role)
    for name in ('registration.json', 'started.json', 'runtime-observation.json', 'stderr.txt'):
        snap.read(attempt / name, 'native_execution_' + name)
    if snap.read(attempt / 'registration.json', 'execution_registration') != registration_raw:
        raise ValueError('captured registration differs from the consumed native attempt')
    if draft._sha(snap.read(value['composition'], 'composition')) != value['composition_sha256']:
        raise ValueError('captured composition differs from the native registration')
    paths = spec._agentic_artifact_paths
    snap.read(paths['receipt'], 'coverage_receipt')
    record_path = prepared['policy']['post_final_recorder']['destination']
    record = shared._mapping(snap.read(record_path, 'provenance'), 'provenance')
    schemas = {'full': api.FULL_SCHEMA_PATH, 'core': api.CORE_SCHEMA_PATH}
    for kind, path in schemas.items():
        snap.read(path, kind + '_schema')
        declared = (record.get('schema') or {}).get(kind + '_path')
        if isinstance(declared, str):
            snap.path(declared)
    for item in [record.get('inputs', {}), (record.get('inputs') or {}).get('chunks', {})]:
        if isinstance(item, dict):
            for key in ('path', 'bundle_path'):
                if isinstance(item.get(key), str):
                    snap.path(item[key])
    directory = Path(paths['receipt']).parent
    for path in sorted((directory / 'intermediate').glob(f'{spec.project}_snapshot_index*.json')):
        snap.read(path, 'phase1_snapshot_index')
    phase1 = receipts.phase1_snapshot_read(Path(paths['receipt']), spec=spec, record=record)
    selected, original, state = None, None, 'absent'
    if phase1 is not None:
        selected, verified_raw = phase1
        captured_raw = snap.read(selected, 'phase1_snapshot')
        if captured_raw != verified_raw:
            raise ValueError('phase1 snapshot changed during capture')
        original = shared._mapping(captured_raw, 'phase1 snapshot')
        if not original:
            raise ValueError('phase1 snapshot is empty')
        state = 'usable'
    prepared.update(record=record, schema_paths=schemas, phase1_original=original,
                    replay_complete=True,
                    phase1_snapshot_identity={'state': state,
                        'path': str(selected) if selected is not None else None,
                        'sha256': draft._sha(snap.read(selected, 'phase1_snapshot')) if selected is not None else None})
    snap.verify_unchanged()
    snap.sealed = True
    return prepared


def tool_history(prepared):
    """Require settled, typed helper results while allowing usable corrections.

    The composed saved checker owns admission, lifecycle, mutation epochs and
    the exact preflight result. This additional check preserves explicit Bash
    result metadata; it does not replace that check or require a fixed recipe.
    """
    spec = prepared['state'].spec
    calls, pending, checks = {}, {}, []
    initialized = terminal = False
    for event in prepared['events']:
        if event.get('type') == 'system' and event.get('subtype') == 'init':
            if initialized or terminal or calls:
                raise ValueError('native initialization is out of order')
            initialized = True
        if event.get('type') == 'result':
            if not initialized or terminal or pending:
                raise ValueError('native terminal precedes settled tool history')
            terminal = True
        content = event.get('message', {}).get('content', [])
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict) or block.get('type') not in ('tool_use', 'tool_result'):
                continue
            if not initialized or terminal:
                raise ValueError('native tool history lies outside initialization and terminal')
            if block['type'] == 'tool_use':
                identity = block.get('id')
                if event.get('type') != 'assistant' or not isinstance(identity, str) or not identity or identity in calls:
                    raise ValueError('native call lacks a unique assistant identity')
                calls[identity] = block
                pending[identity] = block
                continue
            identity = block.get('tool_use_id')
            if event.get('type') != 'user' or identity not in pending:
                raise ValueError('native result lacks a unique pending call')
            call = pending.pop(identity)
            if call.get('name') != 'Bash':
                continue
            metadata = event.get('tool_use_result')
            if not isinstance(metadata, dict):
                raise ValueError('native Bash result lacks explicit exit metadata')
            codes = [metadata[k] for k in ('exitCode', 'exit_code') if k in metadata]
            if not codes or any(type(code) is not int or code != codes[0] for code in codes):
                raise ValueError('native Bash exit aliases are missing, untyped or contradictory')
            if (type(block.get('is_error')) is not bool or block['is_error'] is not bool(codes[0])
                    or any(metadata.get(k) for k in ('interrupted', 'backgroundTaskId', 'background_task_id'))):
                raise ValueError('native Bash result is contradictory, interrupted or pending')
            command = call.get('input', {}).get('command')
            kind = draft.command_kind(command, spec, expected=prepared['state'].commands)
            if kind == 'draft' and codes[0] not in (0, 1):
                raise ValueError('draft checker returned an unusable result')
            if kind in ('evidence', 'final_evidence', 'source_inventory') and codes[0] != 0:
                raise ValueError('terminal evidence or source inventory failed')
            if 'stdout' in metadata:
                content = block.get('content')
                if not isinstance(content, str) or type(metadata['stdout']) is not str:
                    raise ValueError('native Bash stdout/content is not explicit text')
                if kind == 'draft':
                    if draft._encoded(draft._json(content)) != draft._encoded(draft._json(metadata['stdout'])):
                        raise ValueError('draft stdout and tool content disagree')
                elif content != metadata['stdout']:
                    raise ValueError('native Bash stdout and tool content disagree')
            checks.append({'tool_use_id': identity, 'helper_kind': kind, 'exit_code': codes[0]})
    if not initialized or not terminal or pending:
        raise ValueError('native history is incomplete')
    return {'passed': True, 'bash_results': checks,
            'scope': 'Typed settled native results, including usable exit-one draft corrections; no fixed recipe.'}



RUNTIME_OBSERVATION_BASIS = 'captured_runtime_observation_v1'
CLEANUP_BASIS = 'captured_native_cleanup_v1'
# The v1 policy uses this exact set/order from its pinned KeepAwake producer.
IOKIT_ASSERTIONS = ('PreventUserIdleSystemSleep', 'PreventDiskIdle', 'PreventSystemSleep')


def runtime_observation_result(raw, admitted, selected_identity):
    """Bind approval to the exact admitted bytes, including failed drift evidence."""
    if (type(raw) is not bytes or type(admitted) is not dict
            or type(admitted.get('checked')) is not bool or type(admitted.get('passed')) is not bool
            or type(selected_identity) is not dict
            or set(selected_identity) != {'binary', 'version', 'auth', 'environment_sha256'}):
        raise ValueError('runtime observation lacks explicit captured bytes and typed admission')
    expected_raw = draft._encoded(admitted)
    matches = raw == expected_raw
    identity_matches = draft._encoded({key: admitted.get(key) for key in selected_identity}) == draft._encoded(selected_identity)
    return {'checked': True, 'passed': admitted['checked'] and admitted['passed'] and matches and identity_matches,
            'basis': RUNTIME_OBSERVATION_BASIS, 'admitted_observation': deepcopy(admitted),
            'admitted_sha256': draft._sha(expected_raw), 'captured_sha256': draft._sha(raw),
            'matches_admitted': matches, 'selected_runtime_identity': deepcopy(selected_identity),
            'matches_selected_identity': identity_matches}



def _released_assertions(observed, registered_policy):
    acquisition, releases = observed.get('acquisition'), observed.get('releases')
    if (type(acquisition) is not dict or acquisition.get('policy') != registered_policy['policy']
            or set(acquisition) != {'policy', 'pid', 'acquired_at', 'status', 'assertions', 'limitations', 'cleanup_receipt'}
            or acquisition.get('status') != 'acquired'
            or type(acquisition.get('pid')) is not int or acquisition['pid'] <= 0
            or type(acquisition.get('acquired_at')) is not str or not acquisition['acquired_at'].strip()
            or type(observed.get('released_at')) is not str or not observed['released_at'].strip()):
        return False
    assertions = acquisition.get('assertions')
    if (type(assertions) is not list or len(assertions) != len(IOKIT_ASSERTIONS)
            or any(type(row) is not dict or set(row) != {'type', 'id'}
                or type(row['id']) is not int or not 0 < row['id'] < 2**32 for row in assertions)
            or tuple(row['type'] for row in assertions) != IOKIT_ASSERTIONS
            or len({row['id'] for row in assertions}) != len(assertions)):
        return False
    if (type(releases) is not list or len(releases) != len(assertions)
            or any(type(row) is not dict or set(row) != {'type', 'id', 'return_code'}
                or type(row['id']) is not int or type(row['return_code']) is not int
                or row['return_code'] != 0 for row in releases)):
        return False
    return [(row['type'], row['id']) for row in releases] == [
        (row['type'], row['id']) for row in reversed(assertions)]


def cleanup_result(raw, observed, registered_policy):
    """Bind actual cleanup bytes, release outcome and the selected policy."""
    if (type(raw) is not bytes or type(observed) is not dict
            or type(observed.get('passed')) is not bool or type(registered_policy) is not dict):
        raise ValueError('cleanup lacks captured bytes, a typed outcome or selected policy')
    expected_raw = draft._encoded(observed)
    matches = raw == expected_raw
    policy_matches = draft._encoded(observed.get('policy')) == draft._encoded(registered_policy)
    releases = observed.get('releases', [])
    if registered_policy.get('policy') == 'not_applicable':
        outcome_matches = (observed.get('state') == 'explicitly_not_applicable' and releases == []
            and 'acquisition' not in observed and 'released_at' not in observed)
    else:
        outcome_matches = (registered_policy.get('policy') == 'macos_iokit_ims_v1'
            and observed.get('state') == 'released' and _released_assertions(observed, registered_policy))
    return {'checked': True, 'passed': observed['passed'] and matches and policy_matches and outcome_matches,
            'basis': CLEANUP_BASIS, 'observed_cleanup': deepcopy(observed),
            'registered_policy': deepcopy(registered_policy), 'policy_matches': policy_matches,
            'outcome_matches': outcome_matches, 'matches_observed': matches,
            'observed_sha256': draft._sha(expected_raw), 'captured_sha256': draft._sha(raw)}


def check(prepared, projections, runtime, controls, *, exit_code, shutdown, live,
          first_stop, runtime_authority, keep_awake, keep_awake_raw=None, runtime_authority_expected=None):
    """Run every safe independent completion gate from the same captured basis."""
    from data_sheets_schema import api_runner as api, agentic_observed, d4d_pair_consistency as pair
    from data_sheets_schema.duplicate_keys import duplicate_keys_in, describe
    snap, spec = prepared['snapshot'], prepared['state'].spec
    events, policy = prepared['events'], prepared['policy']
    direct = controls['run_direct_canary']
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
        own, auxiliary = direct.model_accounting(terminal, {'model': {
            'model': runtime['model'], 'auxiliary_models_permitted': runtime['auxiliary_models']}})
        usage = terminal.get('usage')
        keys = ('input_tokens', 'output_tokens', 'cache_read_input_tokens', 'cache_creation_input_tokens')
        if not isinstance(usage, dict) or any(type(usage.get(k)) is not int or usage[k] < 0 for k in keys):
            raise ValueError('terminal usage is incomplete or not nonnegative integers')
        for entry in [own, *auxiliary.values()]:
            if any(type(entry.get(k)) is not int or entry[k] < 0 for k in
                   ('inputTokens', 'outputTokens', 'cacheReadInputTokens', 'cacheCreationInputTokens')):
                raise ValueError('per-model usage is incomplete or not nonnegative integers')
        limits = {key: own.get(key) for key in direct.LIMIT_KEYS}
        if (any(type(v) is not int for v in limits.values())
                or draft._encoded(limits) != draft._encoded(runtime['limits'])):
            raise ValueError('observed runtime limits differ from the registered assertions')
        efforts = direct.observed_efforts(projected(Path(runtime['attempt_directory']) / 'control.jsonl'))
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
        problems = []
        for kind, cls in [('full', 'Dataset'), ('core', 'CoreDataset')]:
            path = projected(spec._agentic_artifact_paths[kind])
            duplicate = duplicate_keys_in(path)
            if duplicate:
                problems.append(describe(duplicate))
            lines, failure = api._validator_lines(path, str(projected(prepared['schema_paths'][kind])), cls)
            if failure is not None:
                raise ValueError(failure)
            problems.extend(lines)
        return {'passed': not problems, 'problems': problems}

    def paired():
        schema = pair.load_pair_schema(projected(prepared['schema_paths']['full']), projected(prepared['schema_paths']['core']))
        result = pair.validate_pair_data(shared._mapping(snap.read(spec._agentic_artifact_paths['full'], 'final_full'), 'full'),
            shared._mapping(snap.read(spec._agentic_artifact_paths['core'], 'final_core'), 'core'), schema, schema_moved=False)
        return {'passed': result.passed, 'schema_moved': False,
                'basis': 'fresh attempt, same captured schemas and exact records', 'diagnostic': str(result)}

    def observed():
        out = agentic_observed.observe([projected(Path(runtime['attempt_directory']) / 'transcript.jsonl')], projected(spec.bundle))
        problems = controls['run_native_canary'].observation_problems(out)
        return {'passed': not problems, 'observation': out, 'problems': problems}

    def phase():
        out = controls['native_phase_history'].phase_history(events, spec, complete=True,
            repository=prepared['state'].reg['working_directory'], command_policy=policy)
        return {'passed': not out['problems'], 'history': out}

    def saved():
        if not prepared.get('replay_complete'):
            raise ValueError('complete saved capture unavailable')
        out = replay.check_capture(prepared)
        return {'passed': out['additional_gate_passed'] and out['recorder_completed_in_trace'], 'result': out}

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
    run('tool_history', lambda: tool_history(prepared))
    run('schema', schemas)
    run('pair', paired)
    run('receipts', lambda: shared.receipt_gate(prepared, prepared['record'], prepared['schema_paths'], prepared['phase1_original'], controls))
    run('evidence', lambda: {'passed': prepared['final_result'].get('checked') is True
        and prepared['final_result'].get('findings') == [], 'result': deepcopy(prepared['final_result'])})
    run('observation', observed)
    run('accounting', accounting)
    run('runtime_authority', lambda: runtime_observation_result(
        snap.read(Path(runtime['attempt_directory']) / 'runtime-observation.json',
                  'runtime_observation_approval'), runtime_authority, runtime_authority_expected))
    run('keep_awake', lambda: cleanup_result(keep_awake_raw, keep_awake, runtime['keep_awake']))
    return results
