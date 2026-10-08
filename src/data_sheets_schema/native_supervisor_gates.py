"""Captured-byte adapters for existing native completion algorithms.

Only fresh, explicitly neutral attempts are in scope. Historical recovery and
scientific acceptance are not implemented here. Old checker defaults stay put.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
from pathlib import Path
import types
from types import SimpleNamespace

import yaml

from data_sheets_schema import native_attribution_registration as draft
from data_sheets_schema import native_attribution_results as replay


def _mapping(raw, name):
    from data_sheets_schema.duplicate_keys import find_duplicate_keys
    problems = find_duplicate_keys(raw.decode('utf-8'))
    if problems:
        raise ValueError(f'{name} has duplicate YAML keys')
    value = yaml.safe_load(raw)
    if not isinstance(value, dict):
        raise ValueError(f'{name} must be a mapping')
    return value


class CapturedPath:
    """Only the three operations the frozen source-binding helper consumes."""
    def __init__(self, value, snapshot):
        self.snapshot = snapshot
        self.path = snapshot.path(value.path if isinstance(value, CapturedPath) else value)

    def resolve(self):
        return self.path

    def read_bytes(self):
        return self.snapshot.read(self.path, 'receipt_source_identity')


def receipt_binding(snapshot, spec, record, registered, helper):
    """Run the exact frozen binding algorithm with sealed-path reads.

    A private function-global dictionary substitutes only Path. No global
    module or filesystem monkeypatch is installed, and no live read survives.
    """
    globals_copy = {**helper.__globals__, 'Path': lambda path: CapturedPath(path, snapshot)}
    bound = types.FunctionType(helper.__code__, globals_copy, helper.__name__, helper.__defaults__)
    bound(spec, record, registered)


def _schema_basis(snapshot, record, paths):
    """A new attempt must name the exact captured schemas; no historical fallback."""
    schema = record.get('schema')
    if not isinstance(schema, dict):
        raise ValueError('fresh provenance has no schema identity')
    out = {}
    for kind, path in paths.items():
        raw = snapshot.read(path, kind+'_schema')
        recorded_path = schema.get(kind+'_path')
        if not isinstance(recorded_path, str) or snapshot.path(recorded_path) != snapshot.path(path):
            raise ValueError('fresh provenance schema path differs from registration')
        pins = {algorithm: schema.get(kind+'_'+algorithm) for algorithm in ('sha256', 'md5')}
        if not any(pins.values()) or any(value is not None and value != hashlib.new(algorithm, raw).hexdigest()
                                        for algorithm, value in pins.items()):
            raise ValueError('fresh provenance schema hash differs from registration')
        out[kind] = {'path': str(snapshot.path(path)), 'sha256': draft._sha(raw), 'source': 'captured registered schema'}
    return out


def receipt_gate(prepared, record, schema_paths, original, controls):
    """Same strict receipt floors, selected policy and validated source binding.

    The wrapper's historical Git recovery is deliberately unreachable: the
    frozen precondition requires this attempt's exact registered current bytes.
    The original phase snapshot was resolved/verified during capture, not by
    probing filenames again while checking the receipt.
    """
    from data_sheets_schema import canary, chunking, receipts, receipt_completion_policy as cp
    from data_sheets_schema.grounding import declared_bases_of
    from data_sheets_schema.schema_view import version_document
    snap, spec = prepared['snapshot'], prepared['state'].spec
    registration = prepared['state'].reg
    registered = {'bundle': registration['inputs']['bundle'], 'chunks': registration['inputs']['chunk_manifest']}
    receipt_binding(snap, spec, record, registered, controls['run_api_canary'].require_registered_receipt_inputs)
    # Rendering a spec rereads policy assets. Use the already captured exact
    # declaration so the semantic check has no live prompt dependency.
    policy = cp.select_policy(render_spec=registration['render_spec'], record=record)
    schema_basis = _schema_basis(snap, record, schema_paths)
    full = _mapping(snap.read(spec._agentic_artifact_paths['full'], 'final_full'), 'full record')
    path = spec._agentic_artifact_paths['receipt']
    rec = receipts.load_receipt(Path(path), raw=snap.read(path, 'coverage_receipt'))
    bundle = snap.read(spec.bundle, 'bundle')
    manifest = _mapping(snap.read(spec.chunk_manifest, 'chunk_manifest'), 'chunk manifest')
    # Name and every chunk span/digest must be canonical for these exact bytes.
    chunking.validate_manifest_mapping(manifest, bundle, record['inputs']['chunks']['bundle_name'])
    texts = dict(zip([row['id'] for row in manifest['chunks']],
                     chunking.chunk_texts(bundle.decode('utf-8'), manifest['chunks'])))
    bases = receipts._resolver_bases(receipts._validated_identifier_bases(tuple(declared_bases_of(
        version_document(snap.read(schema_paths['full'], 'full_schema'))))))
    block = receipts.check(rec, manifest, texts, full, record['inputs'].get('bundle_md5'), original,
        identifier_bases=bases, **({'instrument_version': 4} if policy is not None else {}))
    block['expected'] = spec.writes_receipt
    if policy is not None:
        block.update(expected=True, **{cp.BLOCK_KEY: cp.block_identity(policy)})
        block['coverage_floor'] = cp.evaluate_floor(block.get('slots'), policy)
    if block.get('checked') is not True:
        return {'passed': False, 'floors': None, 'receipts': block}
    floors = canary.receipt_floors(block)
    return {'passed': not any(floors.values()), 'floors': floors, 'receipts': block,
            'schema_basis': schema_basis, 'identifier_bases': [list(pair) for pair in bases],
            'snapshot_basis': prepared['phase1_snapshot_identity']}


def capture(composition_path, attempt, controls):
    """Extend the reviewed capture before sealing the supervisor's one basis."""
    from data_sheets_schema import api_runner as api, receipts
    prepared = replay.capture(composition_path, Path(attempt)/'transcript.jsonl', Path(attempt)/'control.jsonl')
    snap, spec = prepared['snapshot'], prepared['state'].spec
    snap.sealed = False
    snap.read(Path(attempt)/'stderr.txt', 'stderr')
    from data_sheets_schema import native_attempt_supervisor as supervisor
    selected = draft._json(snap.read(Path(attempt)/'registration.json', 'supervisor_registration'))
    fixture_raw = snap.read(selected['fixture'], 'neutral_recipe_fixture')
    if (selected['composition_sha256'] != draft._sha(snap.read(composition_path, 'composition'))
            or selected['fixture_sha256'] != draft._sha(fixture_raw)):
        raise ValueError('neutral recipe input binding differs from captured bytes')
    steps = supervisor.recipe_steps(spec, prepared['policy'], supervisor._fixture(fixture_raw))
    if selected['steps_sha256'] != draft._sha(draft._encoded(steps)):
        raise ValueError('neutral recipe steps differ from consumed registration')
    prepared['recipe_steps'] = steps
    paths = spec._agentic_artifact_paths
    snap.read(paths['receipt'], 'coverage_receipt')
    record_path = prepared['policy']['post_final_recorder']['destination']
    record = _mapping(snap.read(record_path, 'provenance'), 'provenance')
    schemas = {'full': api.FULL_SCHEMA_PATH, 'core': api.CORE_SCHEMA_PATH}
    for kind, path in schemas.items():
        snap.read(path, kind+'_schema')
        declared = (record.get('schema') or {}).get(kind+'_path')
        if isinstance(declared, str):
            snap.path(declared)
    for item in [record.get('inputs', {}), (record.get('inputs') or {}).get('chunks', {})]:
        if isinstance(item, dict):
            for key in ('path', 'bundle_path'):
                if isinstance(item.get(key), str):
                    snap.path(item[key])
    # Capture the resolver's authoritative index inputs before resolving once.
    directory = Path(paths['receipt']).parent
    index_dir = directory/'intermediate'
    for path in sorted(index_dir.glob(f'{spec.project}_snapshot_index*.json')):
        snap.read(path, 'phase1_snapshot_index')
    phase1 = receipts.phase1_snapshot_read(Path(paths['receipt']), spec=spec, record=record)
    selected, original, state = None, None, 'absent'
    if phase1 is not None:
        selected, verified_raw = phase1
        captured_raw = snap.read(selected, 'phase1_snapshot')
        if captured_raw != verified_raw:
            raise ValueError('phase1 snapshot changed during capture')
        original = _mapping(captured_raw, 'phase1 snapshot')
        if not original:
            raise ValueError('phase1 snapshot is empty')
        state = 'usable'
    prepared.update(record=record, schema_paths=schemas, phase1_original=original,
        replay_complete=True,
        phase1_snapshot_identity={'state': state, 'path': str(selected) if selected is not None else None,
            'sha256': draft._sha(snap.read(selected, 'phase1_snapshot')) if selected is not None else None})
    snap.verify_unchanged()
    snap.sealed = True
    return prepared


def incomplete_capture(composition_path, attempt, adapter, reason):
    """Retain safely readable stopped evidence and still check independent gates."""
    from data_sheets_schema import api_runner as api
    snap = replay.Capture(Path.cwd().resolve())
    spec = adapter.spec
    paths = {**spec._agentic_artifact_paths,
        'provenance': adapter.policy['post_final_recorder']['destination'],
        'bundle': spec.bundle, 'chunks': spec.chunk_manifest,
        'composition': composition_path, 'full_schema': api.FULL_SCHEMA_PATH, 'core_schema': api.CORE_SCHEMA_PATH,
        **{name: Path(attempt)/name for name in ('transcript.jsonl', 'control.jsonl', 'stderr.txt')}}
    problems = [reason]
    for role, path in paths.items():
        try:
            snap.read(path, role)
        except (OSError, ValueError) as exc:
            problems.append(f'{role}: {exc}')
    def rows(name):
        try:
            return replay._rows(snap.read(Path(attempt)/name, name), name)
        except (OSError, ValueError, UnicodeError):
            return []
    events, records = rows('transcript.jsonl'), rows('control.jsonl')
    snap.verify_unchanged()
    snap.sealed = True
    return {'snapshot': snap, 'state': SimpleNamespace(spec=spec, reg=adapter.state.reg),
        'events': events, 'records': records, 'policy': adapter.policy,
        'schema_paths': {'full': api.FULL_SCHEMA_PATH, 'core': api.CORE_SCHEMA_PATH},
        'replay_complete': False, 'capture_problems': problems, 'record': None,
        'phase1_original': None, 'phase1_snapshot_identity': {'state': 'unavailable'}, 'final_result': None}


def project(prepared, directory):
    """Exclusive retained projections; every file is byte-identical to capture."""
    root = Path(directory)
    root.mkdir(mode=0o700)
    out = {}
    for index, (path, raw) in enumerate(sorted(prepared['snapshot'].raw.items())):
        target = root/str(index)/Path(path).name
        target.parent.mkdir()
        with target.open('xb') as stream:
            stream.write(raw)
        target.chmod(0o400)
        out[path] = target
    return out



def recipe_history(prepared):
    """Check the closed neutral recipe, separate from released generic phase rules."""
    steps = prepared.get('recipe_steps')
    if not isinstance(steps, list) or not steps:
        raise ValueError('captured neutral recipe unavailable')
    position, pending, seen = 0, None, set()
    initialized, terminated = False, False
    for event in prepared['events']:
        if event.get('type') == 'system' and event.get('subtype') == 'init':
            if initialized or terminated or position or pending is not None:
                raise ValueError('neutral initialization is out of order')
            initialized = True
        if event.get('type') == 'result':
            if not initialized or terminated or pending is not None or position != len(steps):
                raise ValueError('neutral terminal precedes settled complete recipe')
            terminated = True
        content = event.get('message', {}).get('content', [])
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            kind = block.get('type')
            if kind not in ('tool_use', 'tool_result'):
                continue
            if not initialized or terminated:
                raise ValueError('neutral tool history lies outside initialization and terminal')
            if kind == 'tool_use':
                identity = block.get('id')
                if (event.get('type') != 'assistant' or pending is not None
                        or not isinstance(identity, str) or not identity or identity in seen
                        or position >= len(steps)):
                    raise ValueError('neutral recipe has duplicate, pending or extra tool calls')
                expected = steps[position]
                if draft._encoded({'tool': block.get('name'), 'input': block.get('input')}) != draft._encoded(expected):
                    raise ValueError('neutral tool call differs from exact ordered recipe')
                pending = identity
                seen.add(identity)
            else:
                if event.get('type') != 'user' or pending is None or block.get('tool_use_id') != pending:
                    raise ValueError('neutral result has no matching unique pending call')
                metadata = event.get('tool_use_result')
                if not isinstance(metadata, dict):
                    raise ValueError('neutral tool result lacks explicit exit metadata')
                codes = [metadata[k] for k in ('exitCode', 'exit_code') if k in metadata]
                if not codes or any(type(code) is not int or code != 0 for code in codes):
                    raise ValueError('neutral helper did not explicitly exit integer zero')
                text = block.get('content')
                if (block.get('is_error') is not False or not isinstance(text, str)
                        or type(metadata.get('stdout')) is not str or metadata['stdout'] != text):
                    raise ValueError('neutral result content or error metadata is inconsistent')
                expected = steps[position]
                if expected['tool'] == 'Read':
                    raw = prepared['snapshot'].read(expected['input']['file_path'], 'neutral_source_read')
                    if text != raw.decode('utf-8'):
                        raise ValueError('neutral source read differs from captured bytes')
                position += 1
                pending = None
    if not initialized or not terminated or pending is not None or position != len(steps):
        raise ValueError('neutral recipe lacks complete settled history')
    return {'passed': True, 'steps_completed': position, 'steps_sha256': draft._sha(draft._encoded(steps))}


def final_evidence_gate(prepared):
    """Keep an explicitly incomplete capture distinct from malformed evidence."""
    result = prepared['final_result']
    if result is None and prepared.get('replay_complete') is False:
        problems = prepared['capture_problems']
        if type(problems) is not list or any(type(problem) is not str for problem in problems):
            raise ValueError('incomplete capture problems must be a list of text')
        return {'checked': False, 'passed': False,
                'reason': 'final evidence unavailable: capture is explicitly incomplete',
                'result': None, 'capture_problems': deepcopy(problems)}
    return {'passed': result.get('checked') is True and result.get('findings') == [],
            'result': deepcopy(result)}


def check(prepared, projections, declaration, controls, *, exit_code, shutdown, live, first_stop):
    """Every required gate reports a result, including independent failures."""
    from data_sheets_schema import api_runner as api, agentic_observed, d4d_pair_consistency as pair
    from data_sheets_schema.duplicate_keys import duplicate_keys_in, describe
    snap, spec = prepared['snapshot'], prepared['state'].spec
    events, policy = prepared['events'], prepared['policy']
    direct = controls['run_direct_canary']
    gates = {}

    def projected(path):
        return projections[str(snap.path(path))]

    def run(name, function):
        try:
            result = function()
            if not isinstance(result, dict) or type(result.get('passed')) is not bool:
                raise ValueError('gate returned no explicit boolean verdict')
            gates[name] = {'checked': True, **result}
        except Exception as exc:
            gates[name] = {'checked': False, 'passed': False, 'reason': f'{type(exc).__name__}: {exc}'}

    def terminal_gate():
        init = [e for e in events if e.get('type') == 'system' and e.get('subtype') == 'init']
        final = [e for e in events if e.get('type') == 'result']
        if len(init) != 1 or len(final) != 1:
            raise ValueError('one exact initialization and terminal result are required')
        one, last = init[0], final[0]
        if (one.get('model') != declaration['model'] or one.get('apiKeySource') != 'neutral_fixture_no_auth'
                or one.get('claude_code_version') != declaration['runtime_version']
                or one.get('tools') != ['Read', 'Write', 'Bash']):
            raise ValueError('neutral initialization differs from explicit fixture identity')
        if (type(exit_code) is not int or exit_code != 0 or last.get('is_error') is not False
                or last.get('terminal_reason') != 'completed' or last.get('stop_reason') != 'end_turn'):
            raise ValueError('child did not complete with an explicit successful terminal')
        return {'passed': True, 'init': one, 'terminal': last}

    def accounting():
        finals = [e for e in events if e.get('type') == 'result']
        if len(finals) != 1:
            raise ValueError('model accounting requires one terminal result')
        terminal = finals[0]
        own, auxiliary = direct.model_accounting(terminal, {'model': {
            'model': declaration['model'], 'auxiliary_models_permitted': declaration['auxiliary_models']}})
        usage = terminal.get('usage')
        keys = ('input_tokens', 'output_tokens', 'cache_read_input_tokens', 'cache_creation_input_tokens')
        if not isinstance(usage, dict) or any(type(usage.get(k)) is not int or usage[k] < 0 for k in keys):
            raise ValueError('neutral terminal usage is incomplete or not nonnegative integers')
        limits = {key: own.get(key) for key in direct.LIMIT_KEYS}
        if draft._encoded(limits) != draft._encoded(declaration['limits']):
            raise ValueError('observed runtime limits differ from explicit fixture limits')
        efforts = direct.observed_efforts(projected(Path(declaration['attempt_directory'])/'control.jsonl'))
        if efforts != [declaration['effort']]:
            raise ValueError('observed effort differs from explicit fixture effort')
        cost = terminal.get('total_cost_usd')
        if type(cost) not in (int, float) or cost < 0 or cost != cost or cost == float('inf'):
            raise ValueError('synthetic runtime cost is missing or unusable')
        if (draft._encoded(usage) != draft._encoded(declaration['usage'])
                or draft._encoded(terminal['modelUsage']) != draft._encoded(declaration['model_usage'])
                or draft._encoded(cost) != draft._encoded(declaration['cost_usd'])):
            raise ValueError('synthetic accounting differs from the exact fixture declaration')
        return {'passed': True, 'basis': 'synthetic neutral fixture declarations, not provider metering',
                'usage': usage, 'registered_model': own, 'auxiliary_models': auxiliary,
                'runtime_cost_estimate_usd': cost, 'efforts': efforts, 'limits': limits}

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
        result = pair.validate_pair_data(_mapping(snap.read(spec._agentic_artifact_paths['full'], 'final_full'), 'full'),
            _mapping(snap.read(spec._agentic_artifact_paths['core'], 'final_core'), 'core'), schema, schema_moved=False)
        return {'passed': result.passed, 'schema_moved': False,
                'basis': 'fresh attempt, same captured schemas and exact records', 'diagnostic': str(result)}

    def observed():
        transcript = projected(Path(declaration['attempt_directory'])/'transcript.jsonl')
        out = agentic_observed.observe([transcript], projected(spec.bundle))
        problems = controls['run_native_canary'].observation_problems(out)
        return {'passed': not problems, 'observation': out, 'problems': problems}

    def phase():
        out = controls['native_phase_history'].phase_history(events, spec, complete=True,
            repository=prepared['state'].reg['working_directory'], command_policy=policy)
        return {'passed': not out['problems'], 'history': out}

    def saved():
        if not prepared.get('replay_complete'):
            raise ValueError('complete saved capture unavailable: '+'; '.join(prepared['capture_problems']))
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
    run('recipe_history', lambda: recipe_history(prepared))
    run('schema', schemas)
    run('pair', paired)
    run('receipts', lambda: receipt_gate(prepared, prepared['record'], prepared['schema_paths'], prepared['phase1_original'], controls))
    run('evidence', lambda: final_evidence_gate(prepared))
    run('observation', observed)
    run('accounting', accounting)
    return gates
