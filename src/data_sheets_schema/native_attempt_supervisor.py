"""One-use, explicitly neutral native controller supervision (#4325).

This module has no arbitrary command/executable entry point and no live runtime
adapter. Its only child is the pinned package-owned local protocol fixture.
An engineering pass is never scientific acceptance or launch authorization.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import re
import shlex
import stat
import sys
import tempfile
import threading
from types import SimpleNamespace

from data_sheets_schema import native_attribution_controller as composition
from data_sheets_schema import native_attribution_registration as draft
from data_sheets_schema import native_attribution_results as replay
from data_sheets_schema import native_supervisor_authority as authority
from data_sheets_schema import native_receipt_origin as receipt_origin

KIND = 'd4d_native_neutral_attempt_supervisor'
VERSION = 1
EXECUTION = 'neutral_local_fixture_only'
RECIPE = 'source_receipt_derive_audit_reconcile_attribution_record_v1'
DRIVER = Path('src/data_sheets_schema/native_neutral_runtime_v1.py')
MAX_BYTES = 8 * 1024 * 1024
GATES = ('terminal', 'shutdown', 'first_stop', 'live_attribution', 'saved_attribution',
         'phase_history', 'recipe_history', 'schema', 'pair', 'receipts', 'evidence', 'observation', 'accounting')
UNASSESSED = dict(generation_acceptance='not_assessed', native_permission_proof='not_assessed',
                  provider_metering='not_assessed', launch_authorization='not_assessed')


def _file(path, name):
    target = Path(path)
    if target.is_symlink() or not target.is_file() or target.stat().st_nlink != 1:
        raise ValueError(f'{name} must be a regular non-symlink single-link file')
    before = target.stat()
    if before.st_size > MAX_BYTES:
        raise ValueError(f'{name} exceeds {MAX_BYTES} bytes')
    raw = target.read_bytes()
    after = target.stat()
    fields = ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_nlink')
    if len(raw) != before.st_size or any(getattr(before, k) != getattr(after, k) for k in fields):
        raise ValueError(f'{name} changed during capture')
    return raw


def _declaration(value):
    keys = {'model', 'auxiliary_models', 'effort', 'limits', 'runtime_version', 'usage', 'model_usage', 'cost_usd'}
    if type(value) is not dict or set(value) != keys:
        raise ValueError('complete explicit synthetic runtime declaration is required')
    if (not isinstance(value['model'], str) or not value['model'].startswith('neutral-fixture-')
            or value['runtime_version'] != 'neutral-local-v1'
            or not isinstance(value['effort'], str) or not value['effort'].startswith('neutral-fixture-')):
        raise ValueError('only explicitly named neutral fixture runtime/model/effort are supported')
    if type(value['auxiliary_models']) is not list or any(not isinstance(x, str)
            or not x.startswith('neutral-fixture-') for x in value['auxiliary_models']):
        raise ValueError('auxiliary models must be explicit neutral fixture names')
    if len(set(value['auxiliary_models'])) != len(value['auxiliary_models']):
        raise ValueError('auxiliary model declarations repeat')
    if type(value['limits']) is not dict or set(value['limits']) != {'contextWindow', 'maxOutputTokens'}:
        raise ValueError('both synthetic runtime limits must be explicit')
    if any(type(x) is not int or x <= 0 for x in value['limits'].values()):
        raise ValueError('synthetic runtime limits must be positive integers')
    if type(value['usage']) is not dict or set(value['usage']) != {
            'input_tokens', 'output_tokens', 'cache_read_input_tokens', 'cache_creation_input_tokens'}:
        raise ValueError('all synthetic usage counters must be explicit')
    if any(type(x) is not int or x < 0 for x in value['usage'].values()):
        raise ValueError('synthetic usage counters must be nonnegative integers')
    if type(value['model_usage']) is not dict:
        raise ValueError('synthetic model accounting must be explicit')
    cost = value['cost_usd']
    if type(cost) not in (int, float) or cost < 0 or cost != cost or cost == float('inf'):
        raise ValueError('synthetic runtime cost must be a finite nonnegative number')
    return draft._json(draft._encoded(value))


def _fixture(raw):
    value = draft._json(raw)
    if type(value) is not dict or set(value) != {'full', 'receipt', 'audit', 'report'}:
        raise ValueError('neutral recipe requires exactly full/receipt/audit/report text')
    if any(not isinstance(v, str) or not v.strip() for v in value.values()):
        raise ValueError('neutral recipe artifacts must be nonempty UTF-8 text')
    return value


def recipe_steps(spec, policy, fixture):
    """Closed helper sequence; the caller cannot supply argv or shell commands."""
    commands = draft._commands(spec)
    spellings = policy['helper_arguments']['spellings']
    receipt = next(c for c in spellings['receipts'] if '--write' not in shlex.split(c))
    derive = next(c for c in spellings['derive'] if '--phase4-complete' not in shlex.split(c))
    freeze = [c for c in policy['command_examples'] if 'original_sha256' in c]
    if len(freeze) != 1:
        raise ValueError('neutral recipe requires one registered original-freeze command')
    def command(kind, artifact=None):
        values = [c for c, k in commands.items() if k == kind and (artifact is None or artifact in shlex.split(c))]
        if len(values) != 1:
            raise ValueError(f'neutral recipe requires one exact {kind} helper')
        return values[0]
    def bash(value):
        return {'tool': 'Bash', 'input': {'command': value}}
    def write(path, text):
        return {'tool': 'Write', 'input': {'file_path': str(path), 'content': text}}
    paths = spec._agentic_artifact_paths
    reads = [spec.bundle, spec.chunk_manifest] + ([spec.manifest] if spec.manifest_used else [])
    return ([{'tool': 'Read', 'input': {'file_path': str(p)}} for p in reads]
        + [write(paths['full'], fixture['full']), write(paths['receipt'], fixture['receipt']),
           bash(receipt), bash(derive), bash(freeze[0]), bash(command('source_inventory', 'original_full')),
           write(Path(paths['core']).parent/'evidence/audit.json', fixture['audit']),
           bash(command('evidence')), bash(derive+' --phase4-complete'),
           bash(command('source_inventory', 'final_full')), write(paths['report'], fixture['report']),
           bash(command('draft')), bash(command('final_evidence')), bash(policy['post_final_recorder']['command'])])


def registration(composition_path, fixture_path, *, attempt_id, attempt_directory,
                 evidence_directory, deadline_seconds, synthetic_runtime, receipt_origin_version=0):
    """Prepare offline identity only. No directory is reserved and no child starts."""
    if type(receipt_origin_version) is not int or receipt_origin_version not in (0, 1):
        raise ValueError('receipt_origin_version must be exactly integer 0 or 1')
    if not isinstance(attempt_id, str) or re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,127}', attempt_id) is None:
        raise ValueError('attempt id must be one explicit safe path component')
    if type(deadline_seconds) is not int or not 0 < deadline_seconds <= 3600:
        raise ValueError('an explicit positive local deadline of at most 3600 seconds is required')
    paths = {key: str(Path(path).absolute()) for key, path in {
        'composition': composition_path, 'fixture': fixture_path,
        'attempt_directory': attempt_directory, 'evidence_directory': evidence_directory}.items()}
    if Path(paths['attempt_directory']).name != attempt_id:
        raise ValueError('attempt directory basename must equal its consumed identity')
    raw = _file(paths['composition'], 'composition')
    value = composition.verified_composition(raw)
    spec, _ = draft.verified(value['registration_raw_json'].encode())
    from data_sheets_schema.agentic_runtime import toolchain
    if draft._encoded(spec._agentic_toolchain) != draft._encoded(toolchain()):
        raise ValueError('neutral recipe requires this exact pinned local interpreter and resource toolchain')
    if spec.provider != 'neutral fixture (no provider)':
        raise ValueError('neutral recipe requires an explicit no-provider request declaration')
    if spec.out_dir is not None:
        raise ValueError('neutral recipe uses the explicit manifest-rooted corpus layout, not out_dir')
    if spec.manifest is None:
        raise ValueError('neutral recipe requires an explicit standalone manifest/corpus root')
    fixture_raw = _file(paths['fixture'], 'neutral fixture')
    fixture = _fixture(fixture_raw)
    runtime = _declaration(synthetic_runtime)
    steps = recipe_steps(spec, value['policy'], fixture)
    controls = composition.load_controls()
    for step in steps:
        if step['tool'] == 'Bash' and composition._classify(step['input']['command'],
                value['policy']['python'], set(), value['policy'], controls)[0] != 'prescribed':
            raise ValueError('neutral recipe command differs from the selected policy')
    result = {'kind': KIND, 'version': VERSION, 'execution': EXECUTION, 'recipe': RECIPE,
        'attempt_id': attempt_id, **paths, 'composition_sha256': draft._sha(raw),
        'fixture_sha256': draft._sha(fixture_raw), 'deadline_seconds': deadline_seconds,
        'synthetic_runtime': runtime, 'working_directory': str(Path.cwd().resolve()),
        'dependencies': authority.dependency_identity(), 'gate_plan': list(GATES),
        'driver': {'path': str(authority.ROOT/DRIVER), 'sha256': draft._sha((authority.ROOT/DRIVER).read_bytes())},
        'steps_sha256': draft._sha(draft._encoded(steps)), **UNASSESSED}
    if receipt_origin_version:
        result[receipt_origin.KEY] = receipt_origin.declaration(
            paths['attempt_directory'], spec._agentic_artifact_paths)
    _paths(result, value, fresh=False)
    return result


def verified(raw):
    if type(raw) is not bytes or len(raw) > MAX_BYTES:
        raise ValueError('supervisor registration must be bounded exact bytes')
    value = draft._json(raw)
    if (type(value) is not dict or value.get('kind') != KIND or type(value.get('version')) is not int
            or value['version'] != VERSION or value.get('execution') != EXECUTION):
        raise ValueError('not a supported neutral-only supervisor registration')
    expected = registration(value['composition'], value['fixture'], attempt_id=value['attempt_id'],
        attempt_directory=value['attempt_directory'], evidence_directory=value['evidence_directory'],
        deadline_seconds=value['deadline_seconds'], synthetic_runtime=value['synthetic_runtime'],
        receipt_origin_version=receipt_origin.version(value))
    if draft._encoded(expected) != draft._encoded(value):
        raise ValueError('supervisor registration differs from exact selection, dependencies or inputs')
    return value


def _paths(value, selected, *, fresh):
    spec, reg = draft.verified(selected['registration_raw_json'].encode())
    outputs = sorted({Path(p).resolve() for p in selected['policy']['readonly_lookups']['output_directories']})
    reserved = [Path(value[k]) for k in ('attempt_directory', 'evidence_directory')] + outputs
    protected = [Path(value[k]).resolve() for k in ('composition', 'fixture')]
    protected += [Path(selected['instruction_path']).resolve()]
    protected += [Path(pin['path']).resolve() for pin in reg['inputs'].values()]
    protected += [Path(pin['path']).resolve() for pin in selected['metadata_inputs'].values()]
    protected += [authority.ROOT/'src', authority.ROOT/'notes', authority.ROOT/'.git']
    for path in reserved:
        if path != path.resolve() or path.is_symlink():
            raise ValueError('reserved paths must be canonical and have no symlink components')
        if fresh and (path.exists() or path.is_symlink()):
            raise ValueError('attempt, evidence and output directories must be new; identities cannot resume')
        if any(path == p or path in p.parents or p in path.parents for p in protected):
            raise ValueError('reserved directory overlaps an immutable input or protected source')
    for i, path in enumerate(reserved):
        if any(path == other or path in other.parents or other in path.parents for other in reserved[i+1:]):
            raise ValueError('attempt, evidence and output directories must be disjoint')
    return reserved


def durable_new(path, raw):
    """Fsync a private staging file, link exclusively, then fsync its directory.

    Failed staging files are retained as failed evidence. This never replaces
    an existing destination; callers reserve the containing directory first.
    """
    path = Path(path)
    fd, temporary = tempfile.mkstemp(prefix='.'+path.name+'.pending-', dir=path.parent)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    os.link(temporary, path)
    _sync_directory(path.parent)
    os.unlink(temporary)


def _sync_directory(path):
    """Persist directory entries; failure never grants dispatch or publication."""
    handle = os.open(path, os.O_RDONLY)
    try:
        os.fsync(handle)
    finally:
        os.close(handle)


class NeutralState:
    def __init__(self):
        self.state = threading.Condition(threading.RLock())
        self.failed = threading.Event()
        self.failure = None
        self.closed = False
        self.unfinished_handlers = 0

    def close_admission(self):
        with self.state:
            self.closed = True


def supervise(registration_raw):
    """Consume one neutral attempt. There is deliberately no retry/resume flag."""
    from data_sheets_schema import native_supervisor_gates as gates
    value = verified(registration_raw)
    raw = _file(value['composition'], 'composition')
    selected = composition.verified_composition(raw)
    reserved = _paths(value, selected, fresh=True)
    attempt, evidence, *outputs = reserved
    attempt.mkdir(mode=0o700)  # The first reservation consumes the identity.
    _sync_directory(attempt.parent)  # Persist that new entry before any later failure.
    durable_new(attempt/'registration.json', registration_raw)
    started = {'kind': KIND, 'version': VERSION, 'state': 'started', 'attempt_id': value['attempt_id'],
        'registration_sha256': draft._sha(registration_raw), 'composition_sha256': draft._sha(raw),
        'execution': EXECUTION, 'dispatch_limit': 1, **UNASSESSED}
    started_raw = draft._encoded(started)
    durable_new(attempt/'started.json', started_raw)
    evidence.mkdir(mode=0o700)
    _sync_directory(evidence.parent)  # A result directory must survive before dispatch.
    for directory in outputs:
        directory.mkdir(parents=True, mode=0o700)
    adapter = composition.CallbackAdapter(raw)
    proxy = NeutralState()
    status, first_stop, prepared = None, None, None
    def stopped(message):
        nonlocal first_stop
        if first_stop is None:
            first_stop = str(message)
    def launch_check():
        if _file(attempt/'registration.json', 'attempt registration') != registration_raw:
            raise ValueError('consumed attempt registration changed')
        verified(registration_raw)
        if proxy.closed or proxy.failed.is_set():
            raise ValueError('neutral controller admission is already closed')
    env = {'PATH': str(Path(sys.executable).parent)+os.pathsep+'/usr/bin:/bin',
        'PYTHONPATH': str(authority.ROOT/'src'), 'PYTHONDONTWRITEBYTECODE': '1',
        'PYTHONUNBUFFERED': '1', 'D4D_LAUNCH_INSTRUCTION': selected['instruction_path'],
        'D4D_MANIFEST': str(adapter.spec.manifest), 'LANG': 'en_US.UTF-8'}
    argv = [sys.executable, value['driver']['path'], '--registration', str(attempt/'registration.json'),
            '--sha256', draft._sha(registration_raw), '--input-format', 'stream-json']
    with authority.loaded_dependencies(value['dependencies']) as controls:
        try:
            status = controls['run_native_canary'].execute_child(argv, proxy=proxy,
                instruction=Path(selected['instruction_path']), attempt=attempt,
                cwd=value['working_directory'], env=env, deadline_seconds=value['deadline_seconds'],
                verify_launch=launch_check, record_stop=stopped, command_policy=adapter.policy,
                phase_spec=adapter.spec, command_classifier=adapter.classify, event_observer=adapter.observe)
        except BaseException as exc:
            stopped(f'{type(exc).__name__}: {exc}')
        if proxy.failed.is_set():
            stopped(proxy.failure or 'neutral controller reported failure')
        if type(proxy.unfinished_handlers) is not int or proxy.unfinished_handlers != 0:
            stopped('neutral controller has unresolved handler state')
        live = adapter.report(complete=True)
        results = {name: {'checked': False, 'passed': False, 'reason': 'capture unavailable'} for name in GATES}
        additional_path = evidence/'attribution-replay.json'
        try:
            try:
                prepared = gates.capture(value['composition'], attempt, controls)
            except Exception as exc:
                problem = f'capture: {type(exc).__name__}: {exc}'
                stopped(problem)
                prepared = gates.incomplete_capture(value['composition'], attempt, adapter, problem)
            if (prepared.get('replay_complete') and prepared['snapshot'].read(
                    attempt/'registration.json', 'supervisor_registration') != registration_raw):
                raise ValueError('captured recipe belongs to a different consumed registration')
            projections = gates.project(prepared, evidence/'captured')
            if prepared.get('replay_complete'):
                replay.write_report(prepared, additional_path)
            declaration = {**value['synthetic_runtime'], 'attempt_directory': str(attempt)}
            results = gates.check(prepared, projections, declaration, controls, exit_code=status,
                shutdown=getattr(proxy, 'control_shutdown', None), live=live, first_stop=first_stop)
            # No checker may alter captured projections or their original identities.
            for path, copy in projections.items():
                if copy.read_bytes() != prepared['snapshot'].raw[path]:
                    raise ValueError('a captured projection changed during validation')
            prepared['snapshot'].verify_unchanged()
            verified(registration_raw)
        except Exception as exc:
            stopped(f'finalization: {type(exc).__name__}: {exc}')
        if first_stop is not None:
            results['first_stop'] = {'checked': True, 'passed': False, 'reason': first_stop}
        if receipt_origin.version(value):
            results = receipt_origin.attach_prepared(value, results, prepared)
        completed = (set(results) == set(GATES)
            and all(row.get('checked') is True and row.get('passed') is True for row in results.values()))
        final = {'kind': KIND, 'version': VERSION, 'execution': EXECUTION, 'attempt_id': value['attempt_id'],
            'engineering_completion': completed, **UNASSESSED, 'first_stop': first_stop,
            'registration_sha256': draft._sha(registration_raw), 'started_sha256': draft._sha(started_raw),
            'composition_sha256': draft._sha(raw), 'child_exit_code': status,
            'shutdown': getattr(proxy, 'control_shutdown', None), 'gates': results,
            'captured_files': prepared['snapshot'].identity() if prepared is not None else {},
            'captured_aliases': dict(prepared['snapshot'].aliases) if prepared is not None else {},
            'captured_metadata': dict(prepared['snapshot'].metadata) if prepared is not None else {},
            'captured_alias_metadata': dict(prepared['snapshot'].alias_metadata) if prepared is not None else {},
            'additional_report': {'path': str(additional_path), 'sha256': draft._sha(additional_path.read_bytes())}
                if additional_path.exists() else None,
            'scope': 'Explicitly synthetic local engineering evidence. No paid generation, native permission, model truth or scientific acceptance.'}
        final_raw = draft._encoded(final)
        receipt_origin.check_final_bytes(value, final_raw, max_bytes=MAX_BYTES)
        durable_new(evidence/'final.json', final_raw)
        durable_new(evidence/'published.json', draft._encoded({'final_sha256': draft._sha(final_raw),
            'started_sha256': draft._sha(started_raw), 'registration_sha256': draft._sha(registration_raw)}))
        return final


def read_final(registration_raw):
    """Read-only committed-result check; no directory or attempt is resumed."""
    value = verified(registration_raw)
    evidence, attempt = Path(value['evidence_directory']), Path(value['attempt_directory'])
    final_raw = _file(evidence/'final.json', 'final result')
    marker = draft._json(_file(evidence/'published.json', 'publication marker'))
    expected = {'final_sha256': draft._sha(final_raw),
        'started_sha256': draft._sha(_file(attempt/'started.json', 'started result')),
        'registration_sha256': draft._sha(registration_raw)}
    if draft._encoded(marker) != draft._encoded(expected):
        raise ValueError('final publication is incomplete or differs from consumed evidence')
    result = draft._json(final_raw)
    if result.get('registration_sha256') != expected['registration_sha256'] or result.get('started_sha256') != expected['started_sha256']:
        raise ValueError('final result does not bind this consumed attempt')
    if (_file(attempt/'registration.json', 'consumed registration') != registration_raw
            or result.get('attempt_id') != value['attempt_id'] or result.get('execution') != EXECUTION
            or result.get('kind') != KIND or type(result.get('version')) is not int or result['version'] != VERSION
            or any(result.get(key) != status for key, status in UNASSESSED.items())):
        raise ValueError('final result identity or scope differs from this neutral attempt')
    checks = result.get('gates')
    if (type(checks) is not dict or set(checks) != set(GATES)
            or any(type(row) is not dict or type(row.get('checked')) is not bool
                or type(row.get('passed')) is not bool for row in checks.values())):
        raise ValueError('final result lacks every strict required gate')
    expected_completion = all(row['checked'] and row['passed'] for row in checks.values())
    if type(result.get('engineering_completion')) is not bool or result['engineering_completion'] != expected_completion:
        raise ValueError('final completion disagrees with its required gates')
    origin_raw = {}
    origin_paths = receipt_origin.required_paths(value, checks['receipts'], result.get('captured_aliases', {}))
    for path, pin in result.get('captured_files', {}).items():
        body = Path(path).read_bytes()
        if draft._sha(body) != pin['sha256']:
            raise ValueError('saved evidence differs from the captured final basis')
        if path in origin_paths:
            origin_raw[path] = body
    for alias, target in result.get('captured_aliases', {}).items():
        if str(Path(alias).resolve()) != target:
            raise ValueError('saved evidence path identity differs from its capture')
        expected_alias = result.get('captured_alias_metadata', {}).get(alias)
        if expected_alias != {'symlink': Path(alias).is_symlink()}:
            raise ValueError('saved evidence alias metadata differs from its capture')
    metadata = result.get('captured_metadata')
    if (not isinstance(metadata, dict) or not set(result.get('captured_files', {})) <= set(metadata)
            or not set(result.get('captured_aliases', {}).values()) <= set(metadata)):
        raise ValueError('saved evidence lacks captured file metadata')
    for path, expected_meta in metadata.items():
        try:
            info = Path(path).stat()
            current_meta = {'exists': True, 'regular': stat.S_ISREG(info.st_mode), 'links': info.st_nlink,
                'device': info.st_dev, 'inode': info.st_ino, 'size': info.st_size, 'mtime_ns': info.st_mtime_ns}
        except FileNotFoundError:
            current_meta = {'exists': False, 'regular': False}
        if current_meta != expected_meta:
            raise ValueError('saved evidence file metadata differs from its capture')
    receipt_origin.check_saved(value, checks['receipts'], raw=origin_raw,
        aliases=result.get('captured_aliases', {}), metadata=metadata)
    additional = result.get('additional_report')
    if additional is None:
        if expected_completion:
            raise ValueError('completed supervision lacks its generated replay report')
    else:
        expected_path = evidence/'attribution-replay.json'
        if (type(additional) is not dict or set(additional) != {'path', 'sha256'}
                or additional['path'] != str(expected_path)
                or draft._sha(_file(expected_path, 'generated replay report')) != additional['sha256']):
            raise ValueError('generated replay report differs from its exact final identity')
    return result
