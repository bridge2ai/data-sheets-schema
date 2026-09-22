"""Sequential fresh native sessions, one canonical audit owner and budget."""
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import stat
import time
from types import SimpleNamespace

from budgeted_cborg import BudgetStop, STALL_DEBIT_BASIS, attempt_identity, now, provider_context_headers, write_new
from native_command_policy import _literal_rule, permission_arguments
from native_control import CONTRACT, load_native_events
from . import batch_output as output
from . import native
from .batch_history import BatchHistory
from .registration import (strict_json, sha, native_api_timeout, native_api_force_idle_timeout,
                           native_stall_policy, native_upstream_read_timeout)
from .output_parts import canonical, describe, read_regular, same_json
from .transport import provider_clients


class BatchProxy(native.AuditProxy):
    """Deadline checked again under the proxy lock after token counting."""
    def __init__(self, *, deadline_guard, **kwargs):
        self.deadline_guard = deadline_guard
        super().__init__(**kwargs)

    def require_open(self):
        self.deadline_guard()
        super().require_open()
        self.deadline_guard()


def _identity(manifest):
    return output._registration_identity(manifest)


def _rows(manifest):
    return strict_json(read_regular(manifest['budget']['ledger_path'], output.MAX_DOCUMENT))['requests']


def _own_rows(manifest, identity):
    owner = attempt_identity(identity, manifest['job']['id'])
    return [r for r in _rows(manifest) if r['attempt'] == owner]


def _digest(value):
    return hashlib.sha256(output._encoded(value)).hexdigest()


def _tree(root):
    """Opaque complete roster, including ignored and hidden files; no symlinks."""
    root = canonical(root)
    files, directories = {}, []
    for directory, names, leaves in os.walk(root, followlinks=False):
        base = Path(directory)
        for name in sorted(names):
            path = base / name
            if not stat.S_ISDIR(path.lstat().st_mode):
                raise BudgetStop('batch child evidence has a linked directory')
            directories.append(str(path.relative_to(root)))
        for name in sorted(leaves):
            path = base / name
            if path == root / 'closed.json':
                continue
            info = path.lstat()
            if not stat.S_ISREG(info.st_mode) or info.st_nlink not in (1, 2):
                raise BudgetStop('batch child evidence must be regular frozen files')
            raw = read_regular(path, 512 * 1024 * 1024, links=info.st_nlink)
            files[str(path.relative_to(root))] = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
                                                 'links': info.st_nlink}
    return {'files': files, 'directories': sorted(directories)}


def _request_ids(child_row):
    root = Path(child_row['attempt_dir']) / 'requests'
    identities = []
    for path in output._directory(root, optional=True):
        if path.name == 'count_retries.jsonl' and path.is_file() and not path.is_symlink():
            continue
        if not re.fullmatch(r'[0-9a-f]{32}', path.name) or not stat.S_ISDIR(path.lstat().st_mode):
            raise BudgetStop('batch request roster has an unknown entry')
        identities.append(path.name)
    return set(identities)


def integration_material(manifest):
    """Deterministically reconstruct all dynamic data from immutable proposals."""
    from data_sheets_schema import audit_batches, audit_batch_context
    from .batch_registration import scientific_arguments
    block = output.configuration(manifest)
    proposals = output.proposals(manifest)
    plan = output.plan(manifest)
    index = audit_batches.build_index(plan, proposals)
    root = Path(output.child(manifest, 'integration')['attempt_dir'])
    parsed = {name: strict_json(raw) for name, raw in proposals.items()}
    by_path = {row['path']: row for value in parsed.values() for row in value['source_review']['values']}
    row_artifacts, views, bindings = {}, {}, {}
    for entry in index['rows']:
        row = by_path[entry['path']]
        raw = audit_batches.canonical_bytes(row)
        digest = hashlib.sha256(raw).hexdigest()
        if digest != entry['sha256']:
            raise BudgetStop('batch row view differs from the indexed scientific proposal')
        path = root / 'rows' / (digest + '.json')
        row_artifacts[entry['path']] = path
        views[str(path)] = raw
        bindings[str(path)] = {'row_path': entry['path'], 'row_sha256': entry['sha256'],
                              'sha256': digest, 'bytes': len(raw)}
    return index, row_artifacts, views, bindings, scientific_arguments(manifest)


def prepare_integration(manifest, identity):
    from data_sheets_schema import audit_batches, audit_batch_context
    output.worker_closures(manifest, identity)
    block = output.configuration(manifest)
    row = output.child(manifest, 'integration')
    index, artifacts, views, bindings, args = integration_material(manifest)
    Path(row['attempt_dir']).mkdir(parents=False, exist_ok=False)
    (Path(row['attempt_dir']) / 'rows').mkdir()
    for path, raw in views.items():
        output._exclusive(path, raw)
    output._exclusive(block['integration_index'], audit_batches.canonical_bytes(index))
    instruction = audit_batch_context.render_integration_context(**args, worker_index=index,
        worker_artifacts={r['id']: Path(r['proposal_path']) for r in block['children'] if r['kind'] == 'worker'},
        row_artifacts=artifacts)
    output._exclusive(row['instruction'], instruction.encode('utf-8'))
    receipt = {'schema_version': 1, 'registration_sha256': identity, 'child_id': 'integration',
               'index': describe(block['integration_index'], audit_batches.canonical_bytes(index)),
               'instruction': describe(row['instruction'], instruction.encode('utf-8')), 'row_views': bindings}
    output._exclusive(Path(row['attempt_dir']) / 'context.json', output._encoded(receipt))
    return verify_integration(manifest, identity)


def verify_integration(manifest, identity):
    from data_sheets_schema import audit_batches, audit_batch_context
    row = output.child(manifest, 'integration')
    index, artifacts, views, bindings, args = integration_material(manifest)
    instruction = audit_batch_context.render_integration_context(**args, worker_index=index,
        worker_artifacts={r['id']: Path(r['proposal_path']) for r in manifest['audit_batches']['children'] if r['kind'] == 'worker'},
        row_artifacts=artifacts).encode('utf-8')
    for path, raw in views.items():
        if read_regular(path, output.MAX_BYTES) != raw:
            raise BudgetStop('integration row view changed')
    root = Path(row['attempt_dir'])
    if {str(p) for p in output._directory(root / 'rows')} != set(views):
        raise BudgetStop('integration row view roster changed')
    index_path = manifest['audit_batches']['integration_index']
    if (read_regular(index_path, output.MAX_DOCUMENT) != audit_batches.canonical_bytes(index)
            or read_regular(row['instruction'], output.MAX_DOCUMENT) != instruction):
        raise BudgetStop('integration index/instruction differs from exact immutable proposals')
    expected = {'schema_version': 1, 'registration_sha256': identity, 'child_id': 'integration',
        'index': describe(index_path, audit_batches.canonical_bytes(index)),
        'instruction': describe(row['instruction'], instruction), 'row_views': bindings}
    if not same_json(strict_json(read_regular(root / 'context.json', output.MAX_DOCUMENT)), expected):
        raise BudgetStop('integration dynamic context receipt changed')
    return expected


def build_policy(manifest, registration_path, child_id):
    from .registration import batch_authority_paths, pinned
    row = output.child(manifest, child_id)
    reads = set(manifest['inputs'].values()) | {row['instruction'], row['system_prompt'], manifest['audit_batches']['plan_path']}
    for path in batch_authority_paths(manifest):
        pinned(manifest, str(path))
        reads.add(str(path))
    row_views = {}
    if child_id == 'integration':
        context = verify_integration(manifest, _identity(manifest))
        row_views = context['row_views']
        reads.update(row_views)
        reads.add(manifest['audit_batches']['integration_index'])
        reads.update(r['proposal_path'] for r in manifest['audit_batches']['children'] if r['kind'] == 'worker')
    commands = [r['check_argv'] for r in row['rounds']] + [row['seal_argv']]
    validator = manifest['job']['validator_argv'] if child_id == 'integration' else []
    assembly = manifest['audit_batches']['assemble_argv'] if child_id == 'integration' else []
    return {'version': 1, 'pretool_control': CONTRACT, 'python': manifest['python'],
        'programs': [], 'manifest_paths': [], 'validator_argv': validator, 'assemble_argv': assembly,
        'draft_argv': commands, 'allowed_tools': ['Read', 'Write', *[_literal_rule(shlex.join(a))
            for a in [*commands, *([assembly, validator] if child_id == 'integration' else [])]]],
        'batch_row_views': row_views,
        'readonly_lookups': {'repository': manifest['repository'], 'inputs': sorted(reads),
            'output_directories': [row['output_dir']], 'write_paths': {
                p: output.MAX_PART_BYTES for round in row['rounds'] for p in round['parts']}}}


def _history(manifest, identity, policy, child_id, *, replay=False):
    return BatchHistory(manifest, identity, policy, child_id, replay=replay)


def _inspect(manifest, identity, row, policy):
    root = Path(row['attempt_dir'])
    evidence = native.inspect_transcript(load_native_events(root / 'transcript.jsonl'), policy, manifest, identity,
        root / 'control.jsonl', root / 'cli_config', phase_key='batch_child',
        history_factory=lambda m, i, p: _history(m, i, p, row['id'], replay=True))
    # Preserve raw evidence on disk; closed summaries need no model final prose.
    terminal = evidence['terminal']
    evidence['terminal'] = {k: terminal[k] for k in ('is_error', 'terminal_reason', 'stop_reason', 'modelUsage')}
    evidence['denials'] = [{'tool': r.get('tool_name'), 'classification': r['classification']} for r in evidence['denials']]
    return evidence


def verify_child_closure(manifest, identity, child_id):
    row = output.child(manifest, child_id)
    root = Path(row['attempt_dir'])
    raw = read_regular(root / 'closed.json', output.MAX_DOCUMENT)
    receipt = strict_json(raw)
    if (type(receipt) is not dict or receipt.get('registration_sha256') != identity
            or receipt.get('child_id') != child_id or receipt.get('job_id') != manifest['job']['id']
            or receipt.get('billing_attempt') != attempt_identity(identity, manifest['job']['id'])
            or receipt.get('status') != 'completed_proposal' or receipt.get('runtime', {}).get('exit_code') != 0
            or type(receipt['runtime']['exit_code']) is not int
            or receipt['runtime'].get('proxy_shutdown_complete') is not True
            or receipt['runtime'].get('proxy_initialized') is not True
            or type(receipt['runtime'].get('unfinished_handlers')) is not int
            or receipt['runtime']['unfinished_handlers'] != 0):
        raise BudgetStop('batch child lacks exact successful closed runtime evidence')
    if not same_json(_tree(root), receipt.get('frozen_evidence')):
        raise BudgetStop('batch child evidence changed after closure')
    policy = build_policy(manifest, Path(manifest['job']['attempt_dir']).parent.parent / 'registration.json', child_id)
    if _digest(policy) != receipt.get('policy_sha256'):
        raise BudgetStop('batch child policy changed after closure')
    evidence = _inspect(manifest, identity, row, policy)
    if not same_json(receipt.get('evidence'), evidence):
        raise BudgetStop('batch child typed history differs from its closure receipt')
    all_rows = _own_rows(manifest, identity)
    ids = _request_ids(row)
    selected = [r for r in all_rows if r['id'] in ids]
    if not ids or len(selected) != len(ids) or any(r['status'] != 'settled' for r in selected):
        raise BudgetStop('batch child requests lack settled canonical ledger rows')
    if not same_json(selected, receipt.get('request_rows')):
        raise BudgetStop('batch child ledger rows changed after closure')
    for entry in selected:
        folder = root / 'requests' / entry['id']
        if sha(folder / 'request.json') != entry['request_sha256']:
            raise BudgetStop('batch request bytes differ from their ledger reservation')
        if entry.get('settlement_basis') != STALL_DEBIT_BASIS:
            if sha(folder / 'response.json') != entry.get('response_sha256'):
                raise BudgetStop('batch settled response bytes differ from ledger evidence')
    context = SimpleNamespace(attempt=root, job=row)
    if not same_json(native.verify_initial_context(context, selected), receipt.get('initial_context')):
        raise BudgetStop('batch child first context changed after closure')
    return {**receipt, 'closure_sha256': hashlib.sha256(raw).hexdigest()}


def _remaining(context, deadline, clock):
    left = deadline - clock()
    if left <= 0:
        raise BudgetStop('aggregate batch deadline elapsed; no further child or request admitted')
    context.ledger.require_resolved(attempt_identity(context.manifest_sha256, context.job['id']))
    return left


def _execute_child(context, row, deadline, *, clock=time.monotonic, client=None, upstream=None):
    manifest, identity = context.manifest, context.manifest_sha256
    owner = attempt_identity(identity, context.job['id'])
    root = Path(row['attempt_dir'])
    if row['id'] != 'integration':
        root.mkdir(parents=True, exist_ok=False)
    elif not (root / 'context.json').is_file():
        raise BudgetStop('integration child has no exact dynamic context')
    Path(row['output_dir']).mkdir()
    for round in row['rounds']:
        Path(round['parts'][0]).parent.mkdir(parents=True)
    config = root / 'cli_config'; config.mkdir(mode=0o700)
    policy = build_policy(manifest, context.registration_path, row['id'])
    history = _history(manifest, identity, policy, row['id'])
    state = {'first_stop_source': None, 'proxy': None}
    before = _own_rows(manifest, identity)
    initial_left = _remaining(context, deadline, clock)
    used = sum((Decimal(r['cost_usd']) for r in before), Decimal(0))
    stage_cap = (Decimal(manifest['audit_batches']['worker_total_cap_usd'])
                 if row['kind'] == 'worker' else context.ledger.limit_for_attempt(owner))
    if stage_cap <= used:
        raise BudgetStop('aggregate stage allowance is exhausted before child launch')
    def admission():
        _remaining(context, deadline, clock)
        context.verify()
        for prior in manifest['audit_batches']['children']:
            if prior['id'] == row['id']:
                break
            verify_child_closure(manifest, identity, prior['id'])
        if row['id'] == 'integration':
            verify_integration(manifest, identity)
        history.verify_admission()
        if clock() >= deadline:
            raise BudgetStop('aggregate batch deadline elapsed during admission verification')
    def controller_stop(reason):
        state.setdefault('first_stop_reason', reason)
        state['first_stop_source'] = state['first_stop_source'] or 'native_controller'
        context.ledger.stop_attempt(owner, reason)
    key = os.environ.get('CBORG_API_KEY')
    if not key and client is None:
        raise BudgetStop('CBORG_API_KEY is required')
    if client is None:
        client, registered_upstream = provider_clients(manifest, key)
        if upstream is None:
            upstream = registered_upstream
    proxy = None
    try:
        def deadline_guard():
            if clock() >= deadline:
                raise BudgetStop('aggregate batch deadline elapsed; no further request admitted')
        proxy = BatchProxy(deadline_guard=deadline_guard, audit_history=history, sdk=client, ledger=context.ledger, attempt=owner,
            evidence=root / 'requests', model=manifest['model']['model'], prices=manifest['budget']['prices_per_token'],
            verify=admission, provider_key=key or 'offline-test-key', base_url=manifest['provider_base_url'],
            request_headers=provider_context_headers(manifest), upstream=upstream,
            **({'upstream_read_timeout_seconds': native_upstream_read_timeout(manifest)}
               if native_upstream_read_timeout(manifest) is not None else {}),
            **({'stall_policy': native_stall_policy(manifest)} if native_stall_policy(manifest) is not None else {}),
            **({'stage_cap': str(stage_cap)} if row['kind'] == 'worker' else {}))
        state['proxy'] = proxy
        environment = {k: v for k, v in os.environ.items() if k in {'PATH', 'HOME', 'SHELL', 'TMPDIR', 'LANG', 'LC_ALL', 'TERM'}}
        environment.update(native.ENVIRONMENT)
        timeout = native_api_timeout(manifest)
        if timeout is not None:
            environment['API_TIMEOUT_MS'] = str(timeout)
        if native_api_force_idle_timeout(manifest) is not None:
            environment['API_FORCE_IDLE_TIMEOUT'] = 'false'
        environment.update(CLAUDE_CONFIG_DIR=str(config), ANTHROPIC_API_KEY=proxy.token,
            PYTHONPATH=os.pathsep.join([str(Path(manifest['repository']) / 'src'), str(native.BASE), str(native.BASE / 'native_controls')]),
            VIRTUAL_ENV=str(Path(manifest['python']).parent.parent))
        directories = sorted({str(Path(p).parent) for p in policy['readonly_lookups']['inputs']} | {row['output_dir']})
        executable = native.verify_runtime(manifest)
        argv = [str(executable), *native.CLI_FLAGS, *[p for d in directories for p in ('--add-dir', d)],
            '--model', manifest['model']['model'], '--name', context.job['id'] + '-' + row['id'],
            '--max-budget-usd', str(stage_cap - used), *permission_arguments(policy),
            '--system-prompt', Path(row['system_prompt']).read_text()]
        write_new(root / 'started.json', {'schema_version': 1, 'job_id': context.job['id'],
            'registration_sha256': identity, 'billing_attempt': owner, 'child_id': row['id'],
            'started_at': now(), 'remaining_seconds_at_start': initial_left,
            'canonical_attempt_cap_usd': str(context.ledger.limit_for_attempt(owner)),
            'child_cli_cap_usd': str(stage_cap - used), 'stage_cap_usd': str(stage_cap),
            'prior_request_ids': [r['id'] for r in before], 'policy_sha256': _digest(policy)})
        with proxy.running() as url:
            environment['ANTHROPIC_BASE_URL'] = url
            try:
                exit_code = native.execute_child(argv, proxy=proxy, instruction=Path(row['instruction']), attempt=root,
                    cwd=manifest['repository'], env=environment, deadline_seconds=_remaining(context, deadline, clock),
                    verify_launch=admission, command_policy=policy, command_classifier=native.classify_command,
                    event_observer=history.observe, record_stop=controller_stop)
            except BaseException as error:
                primary = native.controller_primary(state, error)
                state['primary_error'] = primary
                raise primary from None
        runtime = {'exit_code': exit_code, 'native_version': manifest['native_runtime']['version'],
            'model': manifest['model']['model'], 'effort': 'native_default', **native.shutdown_evidence(proxy)}
        if proxy.failed.is_set() or type(exit_code) is not int or exit_code != 0 or runtime['unfinished_handlers'] != 0:
            raise BudgetStop('batch child did not close successfully')
        _remaining(context, deadline, clock); context.verify()
        current = _own_rows(manifest, identity)
        if not same_json(current[:len(before)], before):
            raise BudgetStop('prior canonical ledger rows changed during child execution')
        selected = current[len(before):]
        if not selected or {r['id'] for r in selected} != _request_ids(row):
            raise BudgetStop('batch child ledger/request membership is incomplete')
        evidence = _inspect(manifest, identity, row, policy)
        first = native.verify_initial_context(SimpleNamespace(attempt=root, job=row), selected)
        receipt = {'schema_version': 1, 'job_id': context.job['id'], 'registration_sha256': identity,
            'billing_attempt': owner, 'child_id': row['id'], 'status': 'completed_proposal',
            'finished_at': now(), 'runtime': runtime, 'policy_sha256': _digest(policy),
            'request_rows': selected, 'initial_context': first, 'evidence': evidence,
            'frozen_evidence': _tree(root)}
        write_new(root / 'closed.json', receipt)
        return verify_child_closure(manifest, identity, row['id'])
    except BaseException as error:
        primary = state.get('primary_error', error)
        runtime = native.shutdown_evidence(proxy)
        primary.native_stop = {'stop_source': state.get('first_stop_source') or
            ('native_proxy' if proxy is not None and proxy.failed.is_set() else 'batch_controller'),
            'runtime': runtime, 'batch_child': row['id']}
        if 'first_stop_reason' in state:
            primary.native_stop_reason = state['first_stop_reason']
        try:
            write_new(root / 'stopped.json', {'child_id': row['id'], 'registration_sha256': identity,
                'status': 'stopped', 'error_type': type(primary).__name__, **primary.native_stop})
        except Exception:
            pass
        if proxy is None:
            for resource in (client, upstream):
                close = getattr(resource, 'close', None)
                if close:
                    try: close()
                    except Exception: pass
        raise primary from None


def finish_deadline(context, result):
    """Include final verification/accounting in the same monotonic job bound."""
    clock = getattr(context, '_batch_clock', None)
    deadline = getattr(context, '_batch_deadline', None)
    if not callable(clock) or type(deadline) not in (int, float):
        raise BudgetStop('batch completion lacks its original aggregate deadline')
    remaining = deadline - clock()
    if remaining <= 0:
        error = BudgetStop('aggregate batch deadline elapsed before final result')
        observation = {'stop_source': 'batch_deadline', 'runtime': native.shutdown_evidence(None)}
        try:
            snapshots, aggregate = stopped_runtime_snapshot(context.manifest)
            observation.update(batch_runtime_children=snapshots, runtime=aggregate)
        except BaseException as snapshot_error:
            observation['batch_runtime_snapshot_error'] = type(snapshot_error).__name__
        error.native_stop = observation
        raise error
    result['evidence']['aggregate_elapsed_seconds'] = context.job['deadline_seconds'] - remaining


def execute_job(context, *, client=None, upstream=None, clock=None, child_runner=None):
    manifest, identity = context.manifest, context.manifest_sha256
    block = output.configuration(manifest, context.registration_path)
    if block is None:
        raise BudgetStop('audit batches were not explicitly selected')
    if client is not None or upstream is not None:
        raise BudgetStop('batch execution requires a fresh provider client pair for every child')
    clock = clock or getattr(context, '_batch_clock', None) or time.monotonic
    if not hasattr(context, '_batch_deadline'):
        context._batch_clock = clock
        context._batch_deadline = clock() + manifest['job']['deadline_seconds']
    elif clock is not context._batch_clock:
        raise BudgetStop('batch execution cannot replace its original deadline clock')
    deadline = context._batch_deadline
    runner = child_runner or _execute_child
    completed = []
    root = Path(manifest['job']['attempt_dir']) / 'children'
    root.mkdir(exist_ok=False)
    try:
        for row in block['children']:
            _remaining(context, deadline, clock)
            if row['id'] == 'integration':
                prepare_integration(manifest, identity)
            completed.append(runner(context, row, deadline, clock=clock))
        _remaining(context, deadline, clock)
        final = completed[-1]
        validation = final['evidence']['batch_child']['validation']
        # No second source-check execution. Typed final receipt and immutable
        # assembled bytes are re-bound by the complete child closure below.
        assembly = output.validate_output(manifest)
        evidence = {'batch_children': [{'id': r['child_id'], 'closure_sha256': r['closure_sha256']} for r in completed],
                    'assembly': assembly, 'aggregate_elapsed_seconds': manifest['job']['deadline_seconds'] - (deadline - clock())}
        runtime = {'exit_code': 0, 'native_version': manifest['native_runtime']['version'],
            'model': manifest['model']['model'], 'effort': 'native_default',
            'proxy_initialized': True, 'proxy_shutdown_complete': True, 'unfinished_handlers': 0,
            'children_closed': len(completed)}
        candidate = {'registration_sha256': identity, 'job_id': manifest['job']['id'],
            'audit_sha256': assembly['audit']['sha256'], 'evidence': evidence, 'runtime': runtime,
            'validation': validation}
        verify_aggregate_closure(manifest, context.registration_path, candidate)
        _remaining(context, deadline, clock)
        finish_deadline(context, candidate)
        return {'audit_path': Path(manifest['job']['audit_path']), 'validation': validation,
                'evidence': evidence, 'runtime': runtime}
    except BaseException as error:
        stop = getattr(error, 'native_stop', {'stop_source': 'batch_orchestrator',
                'runtime': native.shutdown_evidence(None)})
        stop['batch_children_closed'] = [{'id': r['child_id'], 'closure_sha256': r['closure_sha256']} for r in completed]
        try:
            snapshots, aggregate = stopped_runtime_snapshot(manifest)
            stop['batch_runtime_children'] = snapshots
            stop['runtime'] = aggregate
        except BaseException as snapshot_error:
            stop['batch_runtime_snapshot_error'] = type(snapshot_error).__name__
            stop['runtime'] = native.shutdown_evidence(None)
        error.native_stop = stop
        raise


def stopped_runtime_snapshot(manifest):
    """All extant child namespaces; unknown setup is never reported as closed."""
    block = output.configuration(manifest)
    root = Path(manifest['job']['attempt_dir']) / 'children'
    actual = {p.name for p in output._directory(root, optional=True)}
    allowed = {r['id'] for r in block['children']}
    if actual - allowed:
        raise BudgetStop('stopped audit has an unknown batch child')
    snapshots = []
    for row in block['children']:
        if row['id'] not in actual:
            continue
        child_root = Path(row['attempt_dir'])
        paths = [p for p in (child_root / 'closed.json', child_root / 'stopped.json') if os.path.lexists(p)]
        if len(paths) != 1:
            snapshots.append({'id': row['id'], 'receipt': None, 'runtime': native.shutdown_evidence(None), 'known': False})
            continue
        raw = read_regular(paths[0], output.MAX_DOCUMENT)
        receipt = strict_json(raw)
        expected_status = 'completed_proposal' if paths[0].name == 'closed.json' else 'stopped'
        if (type(receipt) is not dict or receipt.get('child_id') != row['id']
                or receipt.get('registration_sha256') != _identity(manifest)
                or receipt.get('status') != expected_status):
            raise BudgetStop('stopped batch child runtime names another execution')
        runtime = receipt.get('runtime')
        if (type(runtime) is not dict or type(runtime.get('proxy_initialized')) is not bool
                or type(runtime.get('proxy_shutdown_complete')) is not bool):
            raise BudgetStop('stopped batch child runtime is missing typed proxy state')
        if runtime['proxy_initialized'] is False:
            valid = runtime['proxy_shutdown_complete'] is False and runtime.get('unfinished_handlers') is None
        elif runtime['proxy_shutdown_complete'] is True:
            valid = type(runtime.get('unfinished_handlers')) is int and runtime['unfinished_handlers'] >= 0
        else:
            valid = runtime.get('unfinished_handlers') is None
        if not valid:
            raise BudgetStop('stopped batch child runtime has contradictory shutdown state')
        snapshots.append({'id': row['id'], 'receipt': describe(paths[0], raw),
                          'runtime': runtime, 'known': True})
    runtimes = [r['runtime'] for r in snapshots]
    complete = bool(snapshots) and all(r['known'] and type(r['runtime']) is dict for r in snapshots)
    initialized = complete and any(r.get('proxy_initialized') is True for r in runtimes)
    closed = complete and all(r.get('proxy_initialized') is False or r.get('proxy_shutdown_complete') is True for r in runtimes)
    counts = [r.get('unfinished_handlers') for r in runtimes if r.get('proxy_initialized') is not False] if complete else [None]
    known_counts = all(type(n) is int and n >= 0 for n in counts)
    return snapshots, {'proxy_initialized': bool(initialized), 'proxy_shutdown_complete': bool(closed),
        'unfinished_handlers': sum(counts) if closed and known_counts else None}


def require_closed_batch_runtime(manifest, result):
    """Source binding for later accounting; a last-child snapshot is insufficient."""
    snapshots, aggregate = stopped_runtime_snapshot(manifest)
    if not same_json(snapshots, result.get('batch_runtime_children')) or not same_json(aggregate, result.get('runtime')):
        raise BudgetStop('stopped aggregate runtime does not bind every extant child')
    if aggregate['proxy_shutdown_complete'] is not True or aggregate['unfinished_handlers'] != 0:
        raise BudgetStop('stopped audit has an unclosed or unknown child runtime')
    return {Path(r['receipt']['path']) for r in snapshots if r['receipt'] is not None}


def verify_aggregate_closure(manifest, registration_path, result):
    identity = _identity(manifest)
    if sha(registration_path) != identity or result.get('registration_sha256') != identity or result.get('job_id') != manifest['job']['id']:
        raise BudgetStop('batch aggregate closure names another registration or job')
    block = output.configuration(manifest, registration_path)
    roots = output._directory(Path(manifest['job']['attempt_dir']) / 'children')
    if {p.name for p in roots} != {r['id'] for r in block['children']} or any(not p.is_dir() or p.is_symlink() for p in roots):
        raise BudgetStop('batch aggregate child roster differs from its registration')
    closed = [verify_child_closure(manifest, identity, r['id']) for r in block['children']]
    expected = [{'id': r['child_id'], 'closure_sha256': r['closure_sha256']} for r in closed]
    if not same_json(result.get('evidence', {}).get('batch_children'), expected):
        raise BudgetStop('batch aggregate closure omitted or reordered a child')
    ids = [r['id'] for c in closed for r in c['request_rows']]
    rows = _own_rows(manifest, identity)
    if len(set(ids)) != len(ids) or ids != [r['id'] for r in rows] or any(r['status'] != 'settled' for r in rows):
        raise BudgetStop('batch aggregate requests lack exact one-child settled membership')
    cost = sum((Decimal(r['cost_usd']) for r in rows), Decimal(0))
    parent_cap = Decimal(str(manifest['budget']['per_job_attempt_usd'][manifest['job']['id']]))
    workers = [r for c in closed[:-1] for r in c['request_rows']]
    worker_cap = Decimal(block['worker_total_cap_usd'])
    if cost > parent_cap or sum((Decimal(r['cost_usd']) for r in workers), Decimal(0)) > worker_cap:
        raise BudgetStop('batch aggregate or worker spending exceeds its registered ceiling')
    if any(Decimal(r['attempt_cap_usd']) != parent_cap or Decimal(r.get('stage_cap_usd', '-1')) != worker_cap for r in workers):
        raise BudgetStop('batch worker reservations did not bind both registered ceilings')
    policy = native_stall_policy(manifest)
    if policy is not None and sum(r.get('settlement_basis') == STALL_DEBIT_BASIS for r in rows) > policy['max_stall_debits']:
        raise BudgetStop('batch aggregate stall allowance was exceeded')
    elapsed = result.get('evidence', {}).get('aggregate_elapsed_seconds')
    if type(elapsed) not in (int, float) or not 0 <= elapsed <= manifest['job']['deadline_seconds']:
        raise BudgetStop('batch aggregate lacks a bounded total execution duration')
    assembly = output.validate_output(manifest)
    final_validation = closed[-1]['evidence']['batch_child']['validation']
    if (not same_json(result.get('evidence', {}).get('assembly'), assembly)
            or result.get('audit_sha256') != assembly['audit']['sha256']
            or not same_json(result.get('validation'), final_validation)):
        raise BudgetStop('batch aggregate final validation/assembly differs from typed child evidence')
    paths = {Path(manifest['job']['audit_path']), Path(assembly['lineage']['path']),
             *output.assembly_paths(manifest)[:2], Path(manifest['job']['attempt_dir']) / 'validation.json'}
    for row, receipt in zip(block['children'], closed):
        root = Path(row['attempt_dir'])
        paths.add(root / 'closed.json')
        paths.update(root / relative for relative in receipt['frozen_evidence']['files'])
    return paths
