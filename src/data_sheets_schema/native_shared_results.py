"""Bounded native shared capture, byte-only reconstruction and saved readback.

The flat pool contains complete raw files. Its summary never substitutes saved
passing flags for stage, phase, permission, attribution or final evidence checks.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

from . import native_shared_contract as c
from . import native_shared_capture as capture_api
from . import native_shared_evidence as evidence
from . import native_shared_selection as selection_api
from . import native_shared_observations as observed
from . import native_attribution_results as inherited
from . import native_supervisor_gates as shared

POOL_NAME = 'native-shared-capture.json'
REPORT_KIND = 'native_shared_saved_reconstruction'


class Snapshot:
    """Old engine's fixed snapshot surface, backed by bounded immutable members."""
    def __init__(self, root, members=()):
        self.root = Path(root)
        self.raw, self.roles, self.metadata = {}, {}, {}
        self.aliases, self.alias_metadata = {}, {}
        self.members = {}
        self.sealed = False
        for member in members:
            self.add(member)

    def add(self, member):
        if self.sealed:
            raise ValueError('cannot extend a sealed native snapshot')
        item = member.captured
        path = item.pin.path
        metadata = c.strict_json(member.metadata_json)
        metadata.pop('symlink')
        if path in self.raw and (self.raw[path] != item.raw or self.metadata[path] != metadata):
            raise ValueError('current capture contains contradictory versions of one physical path')
        self.raw[path], self.metadata[path] = item.raw, metadata
        self.roles.setdefault(path, set()).add(item.pin.role)
        self.aliases[path], self.alias_metadata[path] = path, {'symlink': False}
        self.members[member.member_id] = member
        if (len(self.members) > c.HARD_LIMITS['captured_members'] or
                sum(len(raw) for raw in self.raw.values()) > c.HARD_LIMITS['evidence_raw_total_bytes']):
            raise ValueError('complete native snapshot exceeds its bounded collection')

    def path(self, value):
        path = Path(value)
        key = str(path if path.is_absolute() else self.root / path)
        if key not in self.aliases:
            raise ValueError('saved consumer requested an uncaptured path identity')
        return Path(self.aliases[key])

    def read(self, value, role):
        key = str(self.path(value))
        if key not in self.raw:
            raise ValueError('saved consumer requested uncaptured bytes')
        return self.raw[key]

    def identity(self):
        return {path: {'sha256': c.sha(raw), 'bytes': len(raw), 'roles': sorted(self.roles[path])}
                for path, raw in sorted(self.raw.items())}

    def verify_unchanged(self):
        for member in self.members.values():
            pin = member.captured.pin
            current = evidence.read_regular(pin.path, pin.role, max_bytes=max(1, pin.bytes))
            if current != member:
                raise ValueError('native captured bytes or opened file identity changed before publication')


def _member(pool, role, path):
    found = [m for m in pool.members if m.captured.pin.role == role and m.captured.pin.path == str(path)]
    if len(found) != 1:
        raise ValueError('saved pool lacks exactly one ' + role + ' at its selected path')
    return found[0]


def _captured_selection(pool, value):
    composition = c.strict_json(value['composition_raw_json'].encode(), 'captured C', c.HARD_LIMITS['request_bytes'])
    raw = composition['selection_raw_json'].encode('utf-8')
    doc = c.parse_selection(raw)
    registration = _member(pool, 'selection', doc['registration_path']).captured
    if registration.raw != raw:
        raise ValueError('saved selection differs from the execution declaration')
    artifacts = {role: _member(pool, role, pin['path']).captured
                 for role, pin in selection_api._declarations(doc)}
    schemas = selection_api._schemas(doc, artifacts)
    authority = tuple(a for role, a in artifacts.items()
        if role != 'receipt_policy' and not role.startswith(('full_schema:', 'core_schema:')))
    return selection_api.rebuild(registration, authority, schemas, artifacts['receipt_policy'])


def rebuild(pool, value):
    """Reconstruct the captured run; this function performs no filesystem reads."""
    from .api_runner import RunSpec
    selected = _captured_selection(pool, value)
    if sum(member.captured.pin.bytes for member in pool.members) > selected.bounds()['max_evidence_bytes']:
        raise ValueError('complete capture exceeds the selected evidence bound')
    reader = capture_api._Reader(selected, pool=pool)
    composition = c.strict_json(value['composition_raw_json'].encode(), 'captured composition', c.HARD_LIMITS['request_bytes'])
    if (composition['selection_raw_json'].encode() != selected.registration.raw
            or c.sha(value['composition_raw_json'].encode()) != value['composition_sha256']):
        raise ValueError('saved E/C/S raw identities disagree')
    run = selected.document()['run']
    spec = RunSpec.from_render_spec(composition['render_spec'], project=run['project'], method=run['method'], label=run['label'])
    spec._native_shared_generation_capture = selected
    streams = tuple(_member(pool, role, Path(value['attempt_directory']) / (role + '.jsonl'))
                    for role in ('transcript', 'control'))
    transcript, control = (capture_api._prefix(member, None) for member in streams)
    binding = capture_api._binding(selected, value, composition, reader, pool)
    if c.canonical(c.strict_json(binding.execution.raw, 'saved E', c.HARD_LIMITS['request_bytes'])) != c.canonical(value):
        raise ValueError('saved binding differs from the exact supplied execution')
    started = c.strict_json(binding.started.raw, 'saved started identity', c.HARD_LIMITS['metadata_record_bytes'])
    if (started.get('state') != 'started' or started.get('attempt_id') != value['attempt_id']
            or started.get('registration_sha256') != binding.execution.pin.sha256
            or started.get('composition_sha256') != value['composition_sha256']
            or type(started.get('dispatch_limit')) is not int or started['dispatch_limit'] != 1):
        raise ValueError('saved binding lacks its exact one-use consumed identity')
    observations = sorted((m.captured for m in pool.members if m.captured.pin.role == 'observation'),
                          key=lambda item: item.pin.path)
    if len(observations) > c.HARD_LIMITS['observation_records']:
        raise ValueError('saved observation collection exceeds its bound')
    for number, item in enumerate(observations):
        expected = str(Path(selected.role('observations_root')) / f'{number:06d}.json')
        if item.pin.path != expected:
            raise ValueError('saved observation collection is not the complete ordered selected catalog')
        reader.read('observation', item.pin.path, item.pin)
    history = replace(reader.history(binding), observations=tuple(observations))
    phase1 = capture_api._phase1(selected, binding, history, reader)
    result = capture_api._CapturedRun(selected, value, composition, spec, reader, pool,
        transcript, control, binding, history, tuple(observations), phase1)
    capture_api._checked_observations(result)
    return result


def _capture_member(snapshot, path, role, limit, expected=None):
    member = evidence.read_regular(str(path), role, max_bytes=limit)
    if expected is not None and member.captured.raw != expected:
        raise ValueError('actual file differs from its captured selected authority: ' + role)
    snapshot.add(member)
    return member


def capture(value, controls, *, authority_inputs, registration_raw):
    """One actual bounded capture, followed by the same saved-only reconstruction."""
    composition = c.strict_json(value['composition_raw_json'].encode(), 'captured C', c.HARD_LIMITS['request_bytes'])
    selected_doc = c.parse_selection(composition['selection_raw_json'].encode('utf-8'))
    live = capture_api._load(selected_doc['registration_path'])
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


def prepare(pool, value, controls, *, snapshot=None):
    from . import native_shared_attribution as attribution
    from . import native_shared_gates as gates
    from .audit_omissions import _mapping
    run = rebuild(pool, value)
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
        final_full=capture_api.current_artifact(run, 'final_full', paths['full']),
        final_report=capture_api.current_artifact(run, 'final_report', paths['report']))
    events = [row for _, _, row in observed.rows(run.transcript)]
    records = [row for _, _, row in observed.rows(run.control)]
    policy = run.composition['policy']
    classifications, readonly = {}, {}
    from . import native_shared_policy
    for _, _, call in run.trace().calls.values():
        if call['name'] != 'Bash':
            continue
        command = call['input'].get('command')
        readonly[command] = _readonly(command, policy, snapshot, controls)
        if command in policy['native_shared_helpers'].values():
            classifications[command] = native_shared_policy.classify_bash(command, policy['python'], set(), policy, controls)
        elif readonly[command]:
            # Retain the frozen literal-admission check as well as its exact
            # reason. The sole replaced operation is path resolution above.
            native = controls['run_native_canary']
            problem = native._too_complex(command) or (
                'an argument naming a process environment, which the runtime refuses'
                if any(native._PROC_ENVIRON.search(word)
                    for part in controls['native_readonly'].pipeline_parts(command)
                    for word in (controls['native_command_policy']._simple_command(part)[0] or ())) else None)
            if problem:
                classifications[command] = ('not_prescribed',
                    'a registered read-only lookup, spelled so the runtime refuses it: '
                    + problem + '. This refusal does not disqualify the attempt; quote each '
                    'argument with single quotes and name literal paths, or use the Read tool')
            else:
                classifications[command] = ('prescribed', "a registered read-only lookup of this job's inputs or outputs")
        else:
            raise ValueError('saved history has an unsupported ordinary Bash command')
    final_result = gates.current_evidence(run)
    phase, _ = capture_api.phase_replay(run, complete=True)
    record = _mapping(snapshot.read(policy['post_final_recorder']['destination'], 'provenance'), 'native provenance')
    if (c.canonical(record.get('native_shared_generation')) != c.canonical(capture_api._provenance_block(run))
            or c.canonical(record.get('prompts', {}).get('request', {}).get('spec')) != c.canonical(run.composition['render_spec'])):
        raise ValueError('saved native provenance differs from exact selected stage/render authority')
    prepared = {'run': run, 'pool': pool, 'value': value, 'snapshot': snapshot, 'state': state,
        'composition_raw': value['composition_raw_json'].encode(), 'composition': run.composition,
        'events': events, 'records': records, 'policy': policy, 'controls': controls,
        'record': record, 'final_result': final_result, 'phase_report': phase,
        'classifications': classifications, 'readonly': readonly, 'replay_complete': True}
    prepared['saved_result'] = check_capture(prepared)
    return prepared


def check_capture(prepared):
    """Recompute control, phase, immutable-stage and attribution obligations."""
    run, policy, controls = prepared['run'], prepared['policy'], prepared['controls']
    def classify(command, python, programs, supplied):
        if python != policy['python'] or c.canonical(supplied) != c.canonical(policy):
            raise ValueError('saved classifier differs from exact selected policy')
        return prepared['classifications'][command]
    files = inherited.CapturedFiles(prepared['snapshot'], policy, controls)
    control = inherited._control_history(prepared['events'], prepared['records'], policy, classify, files, controls)
    lifecycle = inherited._control_lifecycle(prepared['events'], prepared['records'], controls)
    draft, final, recorder = inherited._saved_draft(prepared, classify)
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
        view = capture_api.current_effect_view(current, correction_window=draft_seen,
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
    """Additional fixed readback; failed attempts never gain success by omission."""
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
    from .native_attribution_controller import load_controls
    prepared = prepare(evidence.decode(raw), value, load_controls())
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
    from . import native_shared_gates as gates
    from .native_execution import expected_runtime_observation
    fresh_live = {**prepared['saved_result']['draft'],
        'recorder_completed': prepared['saved_result']['recorder_completed_in_trace'],
        'controller_stop': None if prepared['saved_result']['passed'] else 'saved reconstruction failed'}
    cleanup = result['lifecycle_artifacts'].get('keep-awake.json')
    cleanup_raw = (evidence.read_regular(cleanup['path'], 'cleanup',
        max_bytes=c.HARD_LIMITS['input_bytes']).captured.raw if cleanup is not None else None)
    fresh = gates.check(prepared, projections,
        {**value['runtime'], 'attempt_directory': value['attempt_directory']}, prepared['controls'],
        exit_code=result['child_exit_code'], shutdown=result['shutdown'], live=fresh_live,
        first_stop=result['first_stop'], runtime_authority=result['runtime_observation'],
        keep_awake=result['keep_awake'], keep_awake_raw=cleanup_raw,
        runtime_authority_expected=expected_runtime_observation(value))
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


def validate_file_basis(value, result):
    """Native-only bound before the common reader's historical file loop."""
    files = result['captured_files']
    if len(files) > c.HARD_LIMITS['captured_members']:
        raise ValueError('saved native file catalog exceeds its bounded count')
    total = 0
    for path, pin in files.items():
        c.canonical_path(path, 'saved native file')
        c.exact(pin, {'bytes', 'sha256', 'roles'}, 'saved native file identity')
        size = pin['bytes']
        if (type(size) is not int or not 0 <= size <= c.HARD_LIMITS['stream_bytes']
                or type(pin['roles']) is not list or not pin['roles']
                or any(type(role) is not str or not role for role in pin['roles'])
                or sorted(set(pin['roles'])) != pin['roles']):
            raise ValueError('saved native file identity has untyped or oversized bytes/roles')
        total += size
        if total > c.HARD_LIMITS['evidence_raw_total_bytes']:
            raise ValueError('saved native file basis exceeds its aggregate byte bound')
        actual = evidence.read_regular(path, 'saved_file', max_bytes=max(1, size)).captured
        if actual.pin.bytes != size or actual.pin.sha256 != pin['sha256']:
            raise ValueError('saved evidence differs from its bounded captured basis')


def _read_pool(path, limit):
    # This role's wire ceiling exceeds an individual native stream ceiling.
    # The opened read remains bounded and metadata-stable before JSON decoding.
    import os
    import stat
    c.canonical_path(path, 'saved pool path')
    target = Path(path)
    before = target.lstat()
    if (target.resolve(strict=True) != target or not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1 or before.st_size > limit):
        raise ValueError('saved pool is not its bounded regular physical file')
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        opened = os.fstat(descriptor)
        chunks, remaining = [], limit + 1
        while remaining:
            part = os.read(descriptor, min(65536, remaining))
            if not part: break
            chunks.append(part); remaining -= len(part)
        raw = b''.join(chunks)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    identity = lambda x: (x.st_dev, x.st_ino, x.st_mode, x.st_nlink, x.st_size, x.st_mtime_ns)
    if (len(raw) != before.st_size or len(raw) > limit or
            any(identity(x) != identity(before) for x in (opened, after, target.lstat()))):
        raise ValueError('saved pool changed or exceeded its bound during opened capture')
    return raw
