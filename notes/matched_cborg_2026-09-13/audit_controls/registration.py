"""Identity, ancestry and accounting for a separately registered native audit."""
from contextlib import contextmanager
from decimal import Decimal
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys

from filelock import FileLock

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
CONTROLS = BASE / 'native_controls'
for directory in (BASE, CONTROLS):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

from budgeted_cborg import BudgetStop, Ledger, attempt_identity


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def strict_json(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('duplicate JSON key')
            result[key] = value
        return result
    value = json.loads(raw, object_pairs_hook=unique,
        parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite JSON')))
    pending = [value]
    while pending:
        item = pending.pop()
        if isinstance(item, dict):
            pending.extend(item.keys()); pending.extend(item.values())
        elif isinstance(item, list):
            pending.extend(item)
        elif isinstance(item, float) and not math.isfinite(item):
            raise ValueError('nonfinite JSON')
        elif isinstance(item, str):
            item.encode('utf-8')
    return value


def canonical_json(value):
    return json.dumps(value, sort_keys=True, allow_nan=False, separators=(',', ':'))


def read_json(path):
    return strict_json(Path(path).read_bytes())


def canonical_path(value, *, exists=False):
    if not isinstance(value, str) or not value:
        raise BudgetStop('a nonempty canonical path is required')
    path = Path(value)
    if not path.is_absolute() or path.resolve(strict=exists) != path:
        raise BudgetStop('registered path is not absolute and canonical')
    return path


def pinned(manifest, value, expected=None):
    path = canonical_path(value, exists=True)
    recorded = manifest['pinned_files'].get(str(path))
    if (not path.is_file() or not recorded or
            (expected is not None and recorded != expected) or sha(path) != recorded):
        raise BudgetStop('registered input or implementation changed: ' + str(path))
    return path


@contextmanager
def working_directory(path):
    """Only used for offline replay, before starting any provider threads."""
    previous = Path.cwd()
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(previous)


def parent_path(parent, value):
    path = Path(value)
    return path if path.is_absolute() else Path(parent['repository']) / path


def parent_job(manifest):
    generation = read_json(manifest['parent']['registration'])
    jobs = [job for job in generation['generation']['jobs']
            if job['id'] == manifest['parent']['job_id']]
    if len(jobs) != 1:
        raise BudgetStop('parent generation job is missing or ambiguous')
    return generation, jobs[0]


def inspect_parent(manifest):
    """Replay actual parent history; never synthesize events for this session."""
    from data_sheets_schema.api_runner import RunSpec
    from native_control import check_control_history, load_native_events
    from native_phase_history import phase_history
    from run_native_canary import _classify_command, prescribed_programs

    parent = manifest['parent']
    generation, job = parent_job(manifest)
    if generation['repository'] != parent['repository']:
        raise BudgetStop('parent repository differs from its registration')
    expected_attempt = Path(parent['registration']).parent / 'attempts' / parent['job_id']
    for key, name in (('result', 'result.json'), ('transcript', 'transcript.jsonl'), ('control', 'control.jsonl')):
        if canonical_path(parent[key]) != expected_attempt / name:
            raise BudgetStop('parent terminal evidence path differs from its attempt')
    overlay = read_json(parent['overlay'])
    result = read_json(parent['result'])
    if (overlay['registration_sha256'] != sha(parent['registration']) or
            result.get('registration_sha256') != sha(parent['registration']) or
            result.get('overlay_sha256') != sha(parent['overlay']) or
            result.get('job') != parent['job_id']):
        raise BudgetStop('parent execution identities differ')
    if (job.get('execution_arm') != 'agentic' or job['render_spec'].get('condition') != 'generic_v9' or
            job['render_spec'].get('render_version') != 14 or result.get('status') != 'stopped' or
            result.get('unfinished_handlers_at_freeze') != 0 or result.get('reason_source') != 'proxy'):
        raise BudgetStop('parent is not a frozen native transport stop with renderer 14')
    if result.get('disqualifying_denials'):
        raise BudgetStop('parent has disqualifying tool denials')
    paths = job['render_spec']['agentic_artifact_paths']
    evidence = parent_path(parent, paths['core']).parent / 'evidence'
    for key in ('audit.json',):
        if (evidence / key).exists():
            raise BudgetStop('parent already has an audit; do not silently replace it')
    expected = {
        'original_full': evidence / 'original_full.yaml',
        'original_core': evidence / 'original_core.yaml',
        'receipt': parent_path(parent, paths['receipt']),
        'bundle': Path(job['input_identity']['bundle']['path']),
        'chunk_manifest': Path(job['input_identity']['chunks']['path']),
        'source_manifest': Path(job['input_identity']['source_manifest']['path']),
        'parent_instruction': Path(job['instruction']),
        'protocol': Path(parent['repository']) / 'src/download/prompts/evidence_protocol_v3.md',
    }
    resources = job['render_spec']['agentic_toolchain']['resources']
    expected.update(full_schema=Path(resources['src/data_sheets_schema/schema/data_sheets_schema_all.yaml']),
                    core_schema=Path(resources['src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml']))
    for key, path in expected.items():
        if canonical_path(manifest['inputs'][key], exists=True) != path:
            raise BudgetStop('audit input is not the exact inherited ' + key)
    for key, old_key in (('bundle', 'bundle'), ('chunk_manifest', 'chunks'), ('source_manifest', 'source_manifest')):
        if sha(expected[key]) != job['input_identity'][old_key]['sha256']:
            raise BudgetStop('inherited source bytes differ')
    for key in ('original_full', 'original_core', 'receipt'):
        path = expected[key]
        relative = str(path.relative_to(parent['repository']))
        if result['artifacts'].get(relative, result['artifacts'].get(str(path))) != sha(path):
            raise BudgetStop('inherited artifact differs from the frozen result')
    for kind in ('full', 'core'):
        if sha(parent_path(parent, paths[kind])) != sha(expected['original_' + kind]):
            raise BudgetStop('parent record changed after its original snapshot')
    events = load_native_events(Path(parent['transcript']))
    policy = overlay['per_job_command_policy'][parent['job_id']]
    control = check_control_history(events, Path(parent['control']), policy, _classify_command,
                                    expected_attempt / 'cli_config')
    with working_directory(parent['repository']):
        spec = RunSpec.from_render_spec(job['render_spec'], project=job['project'],
                                       method=job['method'], label=job['label'])
        if spec.instruction != Path(job['instruction']).read_text(encoding='utf-8'):
            raise BudgetStop('shared parent instruction no longer replays exactly')
        history = phase_history(events, spec, complete=False, repository=parent['repository'], command_policy=policy)
    if (not control.get('checked') or control.get('problems') or history['problems'] or
            history['terminal_failures'] or history['pending_tool_ids'] or
            not history['phase2_completed'] or not history['receipt_gate_current']):
        raise BudgetStop('parent does not establish clean inherited Phase 1/2 boundaries')
    freeze_programs = [program for program in prescribed_programs(
        Path(job['instruction']).read_text(encoding='utf-8'), generation['python'])
        if 'original_sha256' in program]
    if len(freeze_programs) != 1:
        raise BudgetStop('parent original-freeze command is ambiguous')
    calls, freezes = {}, []
    expected_hashes = {str(expected['original_full'].relative_to(parent['repository'])): sha(expected['original_full']),
                       str(expected['original_core'].relative_to(parent['repository'])): sha(expected['original_core'])}
    for line, event in enumerate(events, 1):
        message = event.get('message')
        for block in (message.get('content', []) if isinstance(message, dict) else []):
            if not isinstance(block, dict):
                continue
            if block.get('type') == 'tool_use' and block.get('name') == 'Bash':
                command = block.get('input', {}).get('command', '')
                try:
                    tokens = shlex.split(command)
                except ValueError:
                    continue
                if len(tokens) == 3 and tokens[:2] == [generation['python'], '-c'] and tokens[2].strip() == freeze_programs[0]:
                    calls[block['id']] = line
            if block.get('type') == 'tool_result' and block.get('tool_use_id') in calls:
                metadata = event.get('tool_use_result') or {}
                try:
                    value = strict_json(metadata.get('stdout', ''))
                except (ValueError, TypeError):
                    continue
                if (block.get('is_error') is False and metadata.get('interrupted') is False and
                        value == {'original_sha256': expected_hashes}):
                    freezes.append({'call_line': calls[block['tool_use_id']], 'result_line': line,
                                    'original_sha256': expected_hashes})
    if len(freezes) != 1 or freezes[0]['result_line'] <= history['phase1_receipt_checks'][-1]['result_event']:
        raise BudgetStop('parent exact original freeze lacks successful ordered evidence')
    with working_directory(parent['repository']):
        before_freeze = phase_history(events[:freezes[0]['call_line'] - 1], spec, complete=False,
            repository=parent['repository'], command_policy=policy)
    if not before_freeze['phase2_completed'] or before_freeze['pending_tool_ids']:
        raise BudgetStop('original freeze precedes completed core derivation')
    return {'kind': 'inherited_native_phase12', 'registration_sha256': sha(parent['registration']),
        'overlay_sha256': sha(parent['overlay']), 'result_sha256': sha(parent['result']),
        'transcript_sha256': sha(parent['transcript']), 'control_sha256': sha(parent['control']),
        'phase_history': history, 'original_freeze': freezes[0],
        'source_reads_basis': 'Preserved parent transcript; the new auditor receives complete inputs inline.',
        'new_generation_claimed': False}


def implementation_paths(manifest):
    repository = canonical_path(manifest['repository'], exists=True)
    paths = set((repository / 'src/data_sheets_schema').rglob('*.py'))
    paths.update((repository / 'src/data_sheets_schema').rglob('*.yaml'))
    paths.update((repository / 'src/data_sheets_schema').rglob('*.json'))
    paths.update(path for path in (repository / 'src/download/prompts').rglob('*') if path.is_file())
    paths.update(HERE.glob('*.py'))
    paths.update(CONTROLS.glob('*.py'))
    paths.update(BASE / name for name in ('budgeted_cborg.py', 'run_api_canary.py', 'prepare_registration.py'))
    paths.update(repository / name for name in ('pyproject.toml', 'poetry.lock'))
    if 'context_recovery' in manifest:
        paths.update(BASE / name for name in ('native_context.py', 'native_context_control.py'))
    return paths


def required_paths(manifest):
    from .transport import transport_paths
    paths = implementation_paths(manifest)
    if 'context_recovery' in manifest:
        from native_context_control import paths as recovery_paths
        paths.update(Path(name) for name in recovery_paths(manifest))
    paths.update(transport_paths(manifest))
    paths.add(canonical_path(manifest['python_identity']['resolved_path'], exists=True))
    config = Path(manifest['python']).parent.parent / 'pyvenv.cfg'
    if config.exists():
        paths.add(config.resolve())
    paths.add(canonical_path(manifest['native_runtime']['executable'], exists=True))
    paths.update(canonical_path(value, exists=True) for value in manifest['inputs'].values())
    paths.update(canonical_path(manifest['job'][key], exists=True) for key in ('instruction', 'system_prompt'))
    parent = manifest['parent']
    paths.update(canonical_path(parent[key], exists=True) for key in
                 ('registration', 'overlay', 'result', 'transcript', 'control', 'phase2_proof',
                  'reconciliation_receipt', 'reconciled_checkpoint'))
    for record in (read_json(parent['registration']), read_json(parent['overlay'])):
        paths.update(canonical_path(str(parent_path(parent, name).resolve()), exists=True) for name in record['pinned_files'])
    paths.add(canonical_path(manifest['budget']['continuation']['checkpoint'], exists=True))
    bridge = manifest['budget']['continuation'].get('reconciliation')
    if bridge is not None:
        if not isinstance(bridge, dict) or set(bridge) != {'source_registration', 'source_ledger', 'receipt', 'result'}:
            raise BudgetStop('invalid audit reconciliation identity fields')
        paths.update(canonical_path(value, exists=True) for value in bridge.values())
    return paths


def verify(manifest, path, expected_sha):
    if sha(path) != expected_sha:
        raise BudgetStop('audit continuation registration changed')
    repository = canonical_path(manifest['repository'], exists=True)
    if Path.cwd() != repository:
        raise BudgetStop('audit controller is running from another repository')
    head = subprocess.check_output(['git', '-C', str(repository), 'rev-parse', 'HEAD'], text=True).strip()
    if head != manifest['repository_commit']:
        raise BudgetStop('audit continuation code commit changed')
    code = sorted(str(value.relative_to(repository)) for value in implementation_paths(manifest))
    for command in (['git', 'ls-files', '--error-unmatch', '--', *code],
                    ['git', 'diff', '--quiet', 'HEAD', '--', *code]):
        if subprocess.run(command, cwd=repository, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode:
            raise BudgetStop('audit implementation files differ from the registered committed code')
    if (sys.executable != manifest['python'] or sys.version != manifest['python_version'] or
            str(Path(sys.executable).resolve()) != manifest['python_identity']['resolved_path'] or
            sys.prefix != manifest['python_identity']['prefix']):
        raise BudgetStop('audit Python interpreter or environment changed')
    from data_sheets_schema import api_runner
    if Path(api_runner.__file__).resolve() != repository / 'src/data_sheets_schema/api_runner.py':
        raise BudgetStop('audit implementation imported from another checkout')
    for value in manifest['pinned_files']:
        pinned(manifest, value)
    failure = Path(manifest['job']['attempt_dir']) / 'validation_failure.json'
    if failure.exists():
        raise BudgetStop('audit validation failed; no further paid request is permitted')


def validate_registration(path):
    path = canonical_path(str(Path(path).absolute()), exists=True)
    manifest = read_json(path)
    if (manifest.get('kind') != 'd4d_native_audit_continuation' or type(manifest.get('schema_version')) is not int or manifest.get('schema_version') != 1 or
            manifest.get('protocol_version') != 3 or manifest.get('render_version') != 14):
        raise BudgetStop('unsupported native audit-continuation contract')
    from .transport import verified_context
    verified_context(manifest)
    verify(manifest, path, sha(path))
    missing = {str(value) for value in required_paths(manifest)} - set(manifest['pinned_files'])
    if missing:
        raise BudgetStop('audit implementation/input closure is not fully pinned')
    parent = manifest['parent']
    generation, parent_record = parent_job(manifest)
    for record in (generation, read_json(parent['overlay'])):
        for filename, digest in record['pinned_files'].items():
            pinned(manifest, str(parent_path(parent, filename).resolve()), digest)
    overlay = read_json(parent['overlay'])
    if (manifest['native_runtime']['executable'] != overlay['claude_executable'] or
            manifest.get('provider_context_policy') != generation.get('provider_context_policy')):
        raise BudgetStop('audit changes inherited native executable or provider policy')
    if (manifest['model'] != generation['model'] or manifest['profile'] != parent_record['profile'] or
            manifest['native_runtime']['version'] != generation['claude_version'] or
            manifest['native_runtime'].get('effort') != 'native_default'):
        raise BudgetStop('audit changes the inherited model, profile or native effort')
    for filename in ('api_runner.py', 'evidence_assertions.py', 'source_review.py', 'profiles.py', 'schema_digest.py'):
        relative = Path('src/data_sheets_schema') / filename
        if sha(Path(manifest['repository']) / relative) != sha(Path(parent['repository']) / relative):
            raise BudgetStop('shared scientific instrument changed: ' + filename)
    proof = inspect_parent(manifest)
    if read_json(parent['phase2_proof']) != proof:
        raise BudgetStop('inherited phase proof differs from actual parent history')
    job = manifest['job']
    if not isinstance(job.get('id'), str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,150}', job['id']):
        raise BudgetStop('invalid audit job identity')
    attempt, output = canonical_path(job['attempt_dir']), canonical_path(job['output_dir'])
    if (attempt != path.parent / 'attempts' / job['id'] or output != attempt / 'output' or
            canonical_path(job['audit_path']) != output / 'audit.json'):
        raise BudgetStop('audit destinations differ from the exclusive registered layout')
    if any(output == Path(name) or output in Path(name).parents or attempt == Path(name) or attempt in Path(name).parents
           for name in manifest['pinned_files']):
        raise BudgetStop('audit writable destinations overlap immutable inputs')
    expected_argv = [manifest['python'], '-m', 'audit_controls.contract', '--registration', str(path)]
    if job['validator_argv'] != expected_argv:
        raise BudgetStop('audit validator arguments differ from registration')
    readable = set(manifest['inputs'].values()) | {job['instruction'], job['system_prompt']}
    if 'context_recovery' in manifest:
        from native_context_control import paths as recovery_paths, validate as validate_recovery
        validate_recovery(manifest, path)
        readable.update(recovery_paths(manifest))
    if set(job['readable_inputs']) != readable:
        raise BudgetStop('audit readable input roster differs')
    if type(job['deadline_seconds']) is not int or job['deadline_seconds'] <= 0:
        raise BudgetStop('audit deadline must be positive whole seconds')
    native_api_timeout(manifest)
    native_api_force_idle_timeout(manifest)
    budget = manifest['budget']
    previous = read_json(budget['continuation']['checkpoint'])
    costs = [Decimal(str(row.get('cost_usd', 'NaN'))) for row in previous['requests']]
    ids = [row.get('id') for row in previous['requests']]
    if (any(row.get('status') != 'settled' for row in previous['requests']) or
            any(not value.is_finite() or value < 0 for value in costs) or len(ids) != len(set(ids)) or
            any(not isinstance(value, str) or not value for value in ids) or
            sum(costs, Decimal(0)) != Decimal(str(budget['continuation']['cost_usd']))):
        raise BudgetStop('audit billing predecessor is unresolved or inconsistent')
    for key, old_key in (('additional_usd', 'additional_cap_usd'), ('per_attempt_usd', 'attempt_cap_usd')):
        if Decimal(str(budget[key])) != Decimal(str(previous[old_key])) or budget[key] != generation['budget'][key]:
            raise BudgetStop('audit changes the approved allocation or default cap')
    cap = budget.get('per_job_attempt_usd', {}).get(job['id'])
    approved = generation['budget'].get('per_job_attempt_usd', {}).get(parent['job_id'], generation['budget']['per_attempt_usd'])
    if (set(budget.get('per_job_attempt_usd', {})) != {job['id']} or cap is None or
            not Decimal(str(cap)).is_finite() or not Decimal(0) < Decimal(str(cap)) <= Decimal(str(approved)) or
            budget['prices_per_token'] != generation['budget']['prices_per_token'] or
            canonical_path(budget['ledger_path']) != path.parent / 'billing.json'):
        raise BudgetStop('audit budget cap, pricing or ledger location differs')
    pinned(manifest, budget['continuation']['checkpoint'], budget['continuation']['sha256'])
    validate_audit_reconciliation(manifest)
    checkpoint = validate_reconciliation(manifest)
    if canonical_json(previous['requests'][:len(checkpoint['requests'])]) != canonical_json(checkpoint['requests']):
        raise BudgetStop('audit predecessor does not preserve reconciled source charges')
    from .contract import render_instruction
    from .prepare import render_system
    if Path(job['system_prompt']).read_text(encoding='utf-8') != render_system(manifest):
        raise BudgetStop('audit system prompt differs from its registered contract')
    if Path(job['instruction']).read_text(encoding='utf-8') != render_instruction(manifest):
        raise BudgetStop('audit instruction does not match its deterministic registered rendering')
    return manifest


def native_api_timeout(manifest):
    """Optional local native SDK timeout; omission preserves its historical default."""
    runtime = manifest['native_runtime']
    if 'api_timeout_ms' not in runtime:
        return None
    value = runtime['api_timeout_ms']
    deadline = manifest['job']['deadline_seconds']
    if (type(value) is not int or value <= 0 or
            type(deadline) is not int or deadline <= 0 or value > deadline * 1000):
        raise BudgetStop('native API timeout must be positive whole milliseconds within the audit deadline')
    return value


def native_api_force_idle_timeout(manifest):
    """Optional native fetch idle policy, independent of the SDK request deadline."""
    runtime = manifest['native_runtime']
    if 'api_force_idle_timeout' not in runtime:
        return None
    value = runtime['api_force_idle_timeout']
    if value is not False:
        raise BudgetStop('native API force-idle-timeout override must be explicit false')
    if native_api_timeout(manifest) is None:
        raise BudgetStop('disabling native fetch idle timeout requires a registered bounded native API timeout')
    return value


@contextmanager
def sequence_guard(manifest, registration_sha):
    """Serialize descendants of the same confirmed source charge checkpoint."""
    generation, _ = parent_job(manifest)
    path = parent_path(manifest['parent'], generation['budget']['ledger_path']).with_name('audit_sequence.json')
    expected = canonical_path(manifest['sequence_state'])
    if expected != path:
        raise BudgetStop('audit sequence state is not derived from its immutable source ledger')
    lock = FileLock(str(path) + '.lock')
    with lock.acquire(timeout=0):
        previous = read_json(path) if path.exists() else None
        checkpoint = manifest['budget']['continuation']
        if previous is None:
            if checkpoint['checkpoint'] != manifest['parent']['reconciled_checkpoint']:
                raise BudgetStop('first audit does not continue the confirmed source checkpoint')
        elif previous['registration_sha256'] == registration_sha:
            raise BudgetStop('audit continuation identity is already consumed')
        else:
            reconciled = validate_audit_reconciliation(manifest)
            if reconciled is None:
                if (checkpoint['checkpoint'] != previous['ledger_path'] or
                        sha(previous['ledger_path']) != checkpoint['sha256']):
                    raise BudgetStop('audit billing fork: predecessor is not the current sequence tip')
                state = read_json(previous['ledger_path'])
            else:
                bridge = checkpoint['reconciliation']
                if (bridge['source_ledger'] != previous['ledger_path'] or
                        sha(bridge['source_registration']) != previous['registration_sha256']):
                    raise BudgetStop('audit reconciliation does not belong to the current sequence tip')
                state = reconciled
            if (state.get('manifest_sha256') != previous['registration_sha256'] or
                    previous.get('source_registration_sha256') != sha(manifest['parent']['registration'])):
                raise BudgetStop('audit predecessor identity differs from sequence tip')
            if any(row.get('status') != 'settled' for row in state['requests']):
                raise BudgetStop('audit sequence has an unresolved predecessor charge')
        value = {'schema_version': 1, 'registration_sha256': registration_sha,
                 'ledger_path': manifest['budget']['ledger_path'],
                 'parent_checkpoint_sha256': checkpoint['sha256'],
                 'source_registration_sha256': sha(manifest['parent']['registration'])}
        temporary = path.with_name(path.name + '.tmp')
        with temporary.open('x') as handle:
            json.dump(value, handle, indent=2)
            handle.write('\n')
        temporary.replace(path)
        yield


def validate_reconciliation(manifest):
    """Only the explicitly confirmed source request may change its accounting."""
    parent = manifest['parent']
    generation, _ = parent_job(manifest)
    source = parent_path(parent, generation['budget']['ledger_path'])
    old = read_json(source)
    receipt = read_json(parent['reconciliation_receipt'])
    checkpoint = read_json(parent['reconciled_checkpoint'])
    digest = sha(parent['reconciliation_receipt'])
    if (receipt.get('kind') != 'user_confirmed_provider_charge_reconciliation' or
            receipt.get('source_registration_sha256') != sha(parent['registration']) or
            receipt.get('source_ledger_sha256') != sha(source) or
            receipt.get('stopped_result_sha256') != sha(parent['result']) or
            not receipt.get('user_confirmation', {}).get('exact_response') or
            not receipt.get('user_confirmation', {}).get('quoted_request') or
            checkpoint.get('manifest_sha256') != sha(parent['registration'])):
        raise BudgetStop('audit reconciliation does not bind the stopped source accounting')
    expected = strict_json(json.dumps(old))
    pending = [row for row in expected['requests'] if row.get('status') != 'settled']
    if len(pending) != 1 or pending[0].get('status') != 'pending':
        raise BudgetStop('reconciliation must resolve exactly one pending source request')
    row = pending[0]
    cost = Decimal(str(receipt['confirmed_complete_charge_usd']))
    if (row['id'] != receipt['request_id'] or row['attempt'] != receipt['attempt'] or
            row['attempt'] != attempt_identity(sha(parent['registration']), parent['job_id']) or
            row['reserved_usd'] != receipt['previous_reservation_usd'] or
            not cost.is_finite() or not Decimal(0) <= cost <= Decimal(row['reserved_usd'])):
        raise BudgetStop('confirmed request identity or charge differs from source reservation')
    row.update(status='settled', cost_usd=str(cost), settled_at=receipt['recorded_at'],
        settlement_basis='user_confirmed_provider_accounting',
        reconciliation_receipt_sha256=digest,
        provider_observation_sha256=receipt['provider_observation_sha256'],
        provider_usage_is_final=False, generation_outcome='stopped')
    expected['reconciled_from'] = {'checkpoint_sha256': sha(source), 'receipt_sha256': digest,
        'request_id': receipt['request_id'], 'previous_status': 'pending',
        'confirmed_charge_usd': str(cost), 'generation_completed': False}
    if canonical_json(checkpoint) != canonical_json(expected):
        raise BudgetStop('reconciled checkpoint changes unconfirmed source accounting')
    return checkpoint


def open_audit_ledger(manifest, registration_path, manifest_sha256):
    budget, job = manifest['budget'], manifest['job']
    location = canonical_path(budget['ledger_path'])
    if location != Path(registration_path).parent / 'billing.json':
        raise BudgetStop('audit ledger differs from the registered condition')
    if set(budget['per_job_attempt_usd']) != {job['id']}:
        raise BudgetStop('audit cap does not bind its sole job')
    prior = budget['continuation']
    pinned(manifest, prior['checkpoint'], prior['sha256'])
    ledger = Ledger(location, manifest_sha256=manifest_sha256,
        total_cap=budget['additional_usd'], attempt_cap=budget['per_attempt_usd'],
        attempt_caps_usd={attempt_identity(manifest_sha256, job['id']): budget['per_job_attempt_usd'][job['id']]})
    ledger.continue_from(prior['checkpoint'], expected_sha256=prior['sha256'], expected_cost_usd=prior['cost_usd'])
    return ledger


def validate_audit_reconciliation(manifest):
    """A confirmed copy can succeed an audit ledger without rewriting it (#2110)."""
    continuation = manifest['budget']['continuation']
    bridge = continuation.get('reconciliation')
    if bridge is None:
        return None
    keys = {'source_registration', 'source_ledger', 'receipt', 'result'}
    if not isinstance(bridge, dict) or set(bridge) != keys:
        raise BudgetStop('invalid audit reconciliation identity fields')
    paths = {key: pinned(manifest, bridge[key]) for key in keys}
    checkpoint_path = pinned(manifest, continuation['checkpoint'], continuation['sha256'])
    source_reg = read_json(paths['source_registration'])
    if source_reg.get('kind') != 'd4d_native_audit_continuation':
        raise BudgetStop('reconciled audit predecessor must be a native audit registration')
    source_sha = sha(paths['source_registration'])
    job = source_reg['job']
    if (paths['source_ledger'] != paths['source_registration'].parent / 'billing.json' or
            paths['source_ledger'] != canonical_path(source_reg['budget']['ledger_path']) or
            checkpoint_path == paths['source_ledger'] or
            Path(job['attempt_dir']) != paths['source_registration'].parent / 'attempts' / job['id'] or
            paths['result'] != Path(job['attempt_dir']) / 'result.json' or
            sha(source_reg['parent']['registration']) != sha(manifest['parent']['registration'])):
        raise BudgetStop('reconciled audit predecessor paths or generation lineage differ')
    source = read_json(paths['source_ledger'])
    result, receipt = read_json(paths['result']), read_json(paths['receipt'])
    if (source.get('manifest_sha256') != source_sha or
            result.get('registration_sha256') != source_sha or result.get('job_id') != job['id'] or
            result.get('scope') != 'phase3_audit_only' or result.get('status') != 'stopped' or
            receipt.get('kind') != 'user_confirmed_provider_charge_reconciliation' or
            receipt.get('source_attempt_kind') != 'phase3_audit_only' or
            receipt.get('source_registration_sha256') != source_sha or
            receipt.get('source_ledger_sha256') != sha(paths['source_ledger']) or
            receipt.get('stopped_result_sha256') != sha(paths['result'])):
        raise BudgetStop('reconciliation does not bind the stopped audit accounting')
    confirmation = receipt.get('user_confirmation', {})
    if any(not isinstance(confirmation.get(key), str) or not confirmation[key].strip()
           for key in ('exact_response', 'quoted_request')):
        raise BudgetStop('audit reconciliation lacks explicit confirmation evidence')
    expected = strict_json(canonical_json(source))
    pending = [row for row in expected['requests'] if row.get('status') != 'settled']
    if len(pending) != 1 or pending[0].get('status') != 'pending':
        raise BudgetStop('audit reconciliation must resolve exactly one pending source request')
    row = pending[0]
    cost = Decimal(str(receipt['confirmed_complete_charge_usd']))
    if (row['id'] != receipt['request_id'] or row['attempt'] != receipt['attempt'] or
            row['attempt'] != attempt_identity(source_sha, job['id']) or
            row['reserved_usd'] != receipt['previous_reservation_usd'] or
            result.get('unresolved_requests') != [row['id']] or
            not cost.is_finite() or not Decimal(0) <= cost <= Decimal(row['reserved_usd'])):
        raise BudgetStop('audit confirmation differs from the source request or reservation')
    row.update(status='settled', cost_usd=str(cost), settled_at=receipt['recorded_at'],
        settlement_basis='user_confirmed_provider_accounting',
        reconciliation_receipt_sha256=sha(paths['receipt']),
        provider_observation_sha256=receipt['provider_observation_sha256'], provider_usage_is_final=False,
        source_attempt_kind='phase3_audit_only', source_attempt_outcome='stopped')
    expected['reconciled_from'] = {'checkpoint_sha256': sha(paths['source_ledger']),
        'receipt_sha256': sha(paths['receipt']), 'request_id': receipt['request_id'],
        'previous_status': 'pending', 'confirmed_charge_usd': str(cost), 'source_attempt_completed': False}
    checkpoint = read_json(checkpoint_path)
    if canonical_json(checkpoint) != canonical_json(expected):
        raise BudgetStop('reconciled audit checkpoint changes unconfirmed history')
    return checkpoint
