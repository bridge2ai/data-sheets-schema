"""Private operational proof that a stopped fresh integrator never source-checked.

Only reviewed pure command/control definitions are isolated from exact compatible
source versions. No scientific checker, assembly, FileAccess or BatchHistory
replay is imported or run. Native result contents are not interpreted. The
input-error recognizer alone reads a fixed error-only Read wrapper privately.

The caller must first validate the source registration identity, complete frozen
condition/links, stopped runtime/process/ledger closure and original source pins.
This module independently binds the passed registration, its integration event
files and compatible classifier sources before and after private decoding.
A positive predicate is necessary, never sufficient, for checkpoint eligibility.
"""
import ast
from collections import Counter
from copy import deepcopy
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import stat

from budgeted_cborg import BudgetStop

# A source-contract compatibility allowlist, not a condition or data identity.
# Changes to these semantics require an explicit reviewed compatibility update.
SUPPORTED_SOURCES = {
    'native_controls/native_control.py': frozenset({
        'f87a5bfe77e37a8ac2961487355b2a31d4b8a7d556fc095531e4c4056ee08a3e',
        'd83919c2afbf56fa79eacee7655635cd78b61079b4f106366ea103be6ce51fdc',
        # The new implementation retains exact v2 projection semantics;
        # selected v3 source histories remain ineligible (#2422).
        'e53f9627e629f06f40046460dbe43bb7a62c26d3f28bedf41408531bc5374a36'}),
    # The #2369 version adds a literal-admission check; `_shell_tokens` and
    # `_simple_command`, the only definitions executed here, are byte-identical.
    'native_controls/native_command_policy.py': frozenset({
        '9353027adace478977b0eb47ea8b0a5a321dfe2d617c251ce59f1527d3918640',
        '98e2d679942bc207ada352353cc7d89edb25efc17160c3cae22d134903313699',
        # #2443/#2444 change policy building and classification only; the
        # two definitions executed here are byte-identical.
        '99db1879752ea73fea0002ea5a3a2d8333365b4e3843abdab3e1a1f0008709cc'}),
    'audit_controls/native.py': frozenset({
        'fc6f3aa8175634b9b4eece74a4ae8e2082c262a3155a7f6bd857431a1d53fcbb',
        'ec56d375f8036fa3c8c13385c5e6de019d83228ea4af2af57121a63dd572636c',
        # #2467 adds the opt-in stop reconciliation around run_job;
        # `classify_command`, the only definition executed here, is byte-identical.
        '31b99995e40bbcc134ad1afd3b58c22afaf3bad4d07f79bdf00416e618fcbd17'}),
}
HEX = re.compile('[0-9a-f]{64}')
MAX_DOCUMENT = 32 * 1024 * 1024
MAX_FRAME = 16 * 1024 * 1024
INVENTORY_KIND = 'audit_batch_checkpoint_inventory_v1'


def require(value, code):
    if not value:
        raise ValueError(code)


def typed_equal(a, b):
    return json.dumps(a, sort_keys=True, separators=(',', ':'), allow_nan=False) == json.dumps(b, sort_keys=True, separators=(',', ':'), allow_nan=False)


def _strict_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'duplicate_key'); result[key] = value
        return result
    def constant(_):
        raise ValueError('nonfinite')
    value = json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)
    pending = [value]
    while pending:
        item = pending.pop()
        if isinstance(item, dict): pending.extend(item.keys()); pending.extend(item.values())
        elif isinstance(item, list): pending.extend(item)
        elif isinstance(item, float): require(math.isfinite(item), 'nonfinite')
        elif isinstance(item, str): item.encode('utf-8')
    return value


def _canonical(path):
    require(type(path) in (str, Path) or isinstance(path, Path), 'path_type')
    path = Path(path)
    require(path.is_absolute() and '..' not in path.parts and path.resolve(strict=True) == path
            and not any(p.is_symlink() for p in (path, *path.parents)), 'canonical_path')
    return path


def _read(path, limit=MAX_DOCUMENT, *, links=1):
    path = _canonical(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        before = os.fstat(stream.fileno())
        require(stat.S_ISREG(before.st_mode) and before.st_nlink == links and before.st_size <= limit, 'file_shape')
        raw = stream.read(limit + 1); after = os.fstat(stream.fileno()); latest = path.lstat()
    signature = lambda s:(s.st_dev, s.st_ino, s.st_size, s.st_nlink, s.st_mtime_ns, s.st_ctime_ns)
    require(len(raw) <= limit and signature(before) == signature(after) == signature(latest), 'file_changed')
    return raw


def _pure_source_functions(raw_sources):
    """Execute ONLY exact pinned pure definitions, never module import bodies."""
    chosen = {
      'native_controls/native_control.py': {'digest', 'initialize_frame', 'hook_output', 'input_validation_rejection'},
      'native_controls/native_command_policy.py': {'_shell_tokens', '_simple_command'},
      'audit_controls/native.py': {'classify_command'}}
    env = {'json': json, 'hashlib': hashlib, 'shlex': shlex, 'deepcopy': deepcopy, 'BudgetStop': BudgetStop,
      'OPERATOR_CHARS': frozenset(';&|<>()'),
      'FORBIDDEN_SHELL': 'shell operators, redirection or substitution the system prompt forbids'}
    native_tree = ast.parse(raw_sources['native_controls/native_control.py'])
    constants = ['CONTRACT', 'INIT_ID']
    if any(isinstance(n, ast.FunctionDef) and n.name == 'control_contract' for n in native_tree.body):
        # Pure dependencies of the new optional initialize_frame argument.
        # _project still calls its exact default and accepts v2 only.
        chosen['native_controls/native_control.py'].add('control_contract')
        constants.append('HISTORY_CONTRACT')
    for name in constants:
        values = [n.value for n in native_tree.body if isinstance(n, ast.Assign)
                  and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name) and n.targets[0].id == name]
        require(len(values) == 1, 'source_constant'); env[name] = ast.literal_eval(values[0])
    for path, names in chosen.items():
        tree = ast.parse(raw_sources[path]); nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
        require({n.name for n in nodes} == names and len(nodes) == len(names), 'pure_definitions')
        exec(compile(ast.Module(body=nodes, type_ignores=[]), path, 'exec'), env)
    return env


def _frames(raw, strict_json):
    require(type(raw) is bytes and 0 < len(raw) <= MAX_DOCUMENT and raw.endswith(b'\n'), 'frame_document')
    rows = raw.split(b'\n')[:-1]
    require(all(row.strip() and len(row) <= MAX_FRAME for row in rows), 'frame_boundary')
    result = [strict_json(row) for row in rows]
    require(all(type(r) is dict for r in result), 'frame_object')
    return result


def _project(events, records, manifest, pure):
    """Strict correlation only; no FileAccess or scientific history replay."""
    require(type(events) is list and events and type(records) is list and records, 'empty_history')
    require('native_history_control' not in manifest, 'unsupported_control_contract')
    children = manifest['audit_batches']['children']
    integration = [c for c in children if c['id'] == 'integration']
    require(len(integration) == 1, 'integration_identity'); child = integration[0]
    validator = manifest['job']['validator_argv']
    require(validator == [manifest['python'], '-m', 'audit_controls.contract', '--registration', manifest['_registration_path']], 'validator_identity')
    policy = {'validator_argv': validator, 'assemble_argv': manifest['audit_batches']['assemble_argv'],
              'draft_argv': [r['check_argv'] for r in child['rounds']] + [child['seal_argv']]}
    contract = pure['CONTRACT']; init_id = pure['INIT_ID']
    allowed_records = {'initialize_sent', 'initialize_ack', 'decision', 'persisted_output', 'input_rejected_before_callback'}
    require(all(type(r) is dict and r.get('kind') in allowed_records for r in records), 'record_kind')
    sent = [r for r in records if r['kind'] == 'initialize_sent']; ack = [r for r in records if r['kind'] == 'initialize_ack']
    require(len(sent) == len(ack) == 1 and typed_equal(sent[0]['frame'], pure['initialize_frame']())
            and type(sent[0].get('policy_sha256')) is str and HEX.fullmatch(sent[0]['policy_sha256']), 'initialization')
    require(records.index(sent[0]) < records.index(ack[0]), 'initialization_order')
    decisions = {}; decision_tools = set()
    for rec in records:
        if rec['kind'] != 'decision': continue
        require(records.index(rec) > records.index(ack[0]), 'decision_before_ack')
        frame = rec['request']; rid = frame['request_id']; data = frame['request']['input']; tid = data['tool_use_id']
        require(type(rid) is str and rid and rid != init_id and rid not in decisions and tid not in decision_tools, 'decision_identity')
        decisions[rid] = rec; decision_tools.add(tid)
    calls = {}; results = {}; callbacks = {}; terminals = 0; initialized = False; session = None; init_frames = 0
    counters = Counter(); rejections = []
    allowed_events = {'system', 'assistant', 'user', 'control_request', 'control_response', 'result', 'rate_limit_event'}
    for number, event in enumerate(events, 1):
        require(type(event) is dict and event.get('type') in allowed_events, 'event_kind')
        kind = event['type']
        require(event.get('parent_tool_use_id') is None, 'nested_session')
        if event.get('session_id'):
            require(type(event['session_id']) is str, 'session_type')
            session = session or event['session_id']; require(session == event['session_id'], 'multiple_sessions')
        if kind == 'control_response':
            require(not initialized and not calls and typed_equal(event, ack[0]['frame']), 'initialization_frame')
            response = event['response']
            require(response.get('request_id') == init_id and response.get('subtype') == 'success', 'initialization_response')
            initialized = True; init_frames += 1
        if kind == 'result':
            require(initialized and terminals == 0 and set(calls) == set(results), 'terminal_order'); terminals += 1
        message = event.get('message')
        if message is not None:
            require(type(message) is dict, 'message_shape')
            content = message.get('content')
            require(type(content) in (str, list), 'message_content_shape')
            for block in content if type(content) is list else []:
                require(type(block) is dict, 'message_block')
                typ = block.get('type')
                if typ not in ('tool_use', 'tool_result'): continue
                require(initialized and not terminals and session is not None, 'tool_order')
                if typ == 'tool_use':
                    require(kind == 'assistant' and message.get('role') == 'assistant', 'call_role')
                    tid = block.get('id'); tool = block.get('name'); payload = block.get('input')
                    require(type(tid) is str and tid and tid not in calls and tool in ('Bash', 'Read', 'Write') and type(payload) is dict, 'call_shape')
                    calls[tid] = (number, event, block, session); counters[tool] += 1
                    if tool == 'Bash':
                        require(type(payload.get('command')) is str, 'bash_input')
                        tokens, _ = pure['_simple_command'](payload['command'])
                        if tokens == validator: counters['checker_attempts'] += 1
                else:
                    require(kind == 'user' and message.get('role') == 'user', 'result_role')
                    tid = block.get('tool_use_id')
                    require(type(tid) is str and tid in calls and tid not in results, 'result_identity')
                    require('is_error' not in block or type(block['is_error']) is bool, 'result_error_type')
                    results[tid] = (number, event, block)
        if kind == 'control_request':
            require(initialized and not terminals, 'callback_order')
            req = event['request']; data = req['input']; tid = data['tool_use_id']; rid = event['request_id']
            require(type(req) is dict and type(data) is dict and tid in calls and tid not in callbacks
                    and tid not in results and rid in decisions, 'callback_identity')
            _, _, call, _ = calls[tid]; tool = call['name']; payload = call['input']; rec = decisions[rid]
            require(req.get('subtype') == 'hook_callback' and req.get('callback_id') == contract['callback_id']
                    and data.get('hook_event_name') == contract['event'] and data.get('tool_name') == tool
                    and data.get('cwd') == manifest['repository'] and req.get('tool_use_id') in (None, tid)
                    and typed_equal(rec['request'], event), 'callback_binding')
            require(type(data.get('tool_input')) is dict, 'callback_payload')
            classification, basis = rec['classification'], rec['basis']
            require(classification in ('prescribed', 'not_prescribed') and type(basis) is str, 'decision_shape')
            if tool == 'Bash':
                require(typed_equal(payload, data['tool_input']), 'bash_callback_input')
                require((classification, basis) == pure['classify_command'](payload['command'], manifest['python'], set(), policy), 'bash_policy')
                tokens, _ = pure['_simple_command'](payload['command'])
                if tokens == validator and classification == 'prescribed': counters['checker_admissions'] += 1
            expected = {'type': 'control_response', 'response': {'subtype': 'success', 'request_id': rid,
                        'response': pure['hook_output'](classification, basis)}}
            require(typed_equal(rec['response'], expected), 'decision_response')
            callbacks[tid] = (number, rid, classification)
    require(initialized and init_frames == 1 and set(calls) == set(results), 'incomplete_tools')
    require({item[1] for item in callbacks.values()} == set(decisions), 'orphan_decision')
    for tid, (line, event, call, call_session) in calls.items():
        result_line, result_event, result = results[tid]
        require(line < result_line, 'result_order')
        if tid not in callbacks:
            # Both supported controls have identical Read-rejection semantics.
            # The newer control also knows an unread-Write refusal; that branch
            # is deliberately outside this narrow scanner's supported contract.
            require(call['name'] == 'Read', 'unsupported_callback_free_tool')
            rejection = pure['input_validation_rejection'](event, call, result_event, line, result_line, call_session)
            require(rejection is not None, 'unmatched_call'); rejections.append(rejection)
            continue
        callback_line, _, classification = callbacks[tid]
        require(line < callback_line < result_line, 'callback_result_order')
        if classification == 'not_prescribed': require(result.get('is_error') is True, 'denied_success')
        if call['name'] == 'Bash':
            tokens, _ = pure['_simple_command'](call['input']['command'])
            if tokens == validator and classification == 'prescribed': counters['checker_results'] += 1
    recorded_rejections = [{k:v for k,v in r.items() if k != 'at'} for r in records if r['kind'] == 'input_rejected_before_callback']
    require(typed_equal(sorted(rejections, key=lambda r:r['result_line']), recorded_rejections), 'input_rejection_binding')
    zero = counters['checker_attempts'] == counters['checker_admissions'] == counters['checker_results'] == 0
    return {'kind': 'audit_checkpoint_terminal_check_absence_v1', 'predicate': 'zero_terminal_check_proven' if zero else 'terminal_check_observed',
      'zero_terminal_source_check': zero, 'checker_tool_attempts': counters['checker_attempts'],
      'checker_permission_admissions': counters['checker_admissions'], 'checker_result_envelopes': counters['checker_results'],
      'native_event_count': len(events), 'control_record_count': len(records), 'tool_calls': len(calls),
      'tool_results': len(results), 'permission_decisions': len(decisions), 'bash_calls': counters['Bash'],
      'read_calls': counters['Read'], 'write_calls': counters['Write'], 'unexecuted_read_input_rejections': len(rejections),
      'native_terminal_frames': terminals, 'complete_tool_correspondence': True,
      'private_operational_event_decoding': True, 'scientific_checker_replay': False,
      'scientific_acceptance': False, 'carry_forward_authorized': False,
      'checker_execution_invoked_by_projector': 0, 'provider_calls': 0}


def _verify(source_manifest, registration_path, inventory):
    registration_path = _canonical(registration_path); root = registration_path.parent
    require(registration_path.name == 'registration.json', 'registration_name')
    registration_raw = _read(registration_path)
    require(type(source_manifest) is dict and typed_equal(_strict_json(registration_raw), source_manifest), 'registration_binding')
    m = source_manifest
    require(m.get('kind') == 'd4d_native_audit_continuation' and 'audit_worker_checkpoint' not in m
            and 'native_history_control' not in m
            and type(m.get('protocol_version')) is int and m['protocol_version'] == 7
            and type(m.get('render_version')) is int and m['render_version'] == 23
            and m.get('scientific_contract_transition') == {'kind':'frozen_pair_child_navigation_v1'}
            and m.get('audit_batch_navigation') == {'kind':'explicit_child_reads_v1'}
            and m['audit_batches']['kind'] == 'fresh_context_integrated_v1', 'source_contract')
    require(type(inventory) is dict and set(inventory) == {'kind','root','files','directories','hardlink_groups'}
            and inventory['kind'] == INVENTORY_KIND and inventory['root'] == str(root)
            and type(inventory['files']) is dict and type(inventory['directories']) is list
            and type(inventory['hardlink_groups']) is list, 'inventory_contract')
    files = inventory['files']
    for relative, desc in files.items():
        require(type(relative) is str, 'inventory_name')
        posix = PurePosixPath(relative)
        require(not posix.is_absolute() and str(posix) == relative and relative
                and '..' not in posix.parts and '.' not in posix.parts, 'inventory_path')
        require(type(desc) is dict and set(desc) == {'sha256','bytes','links'}
                and type(desc['sha256']) is str and HEX.fullmatch(desc['sha256'])
                and type(desc['bytes']) is int and desc['bytes'] >= 0
                and type(desc['links']) is int and desc['links'] in (1,2), 'inventory_descriptor')
    def frozen(path):
        desc = files[str(path.relative_to(root))]
        raw = _read(path, links=desc['links'])
        require(len(raw) == desc['bytes'] and hashlib.sha256(raw).hexdigest() == desc['sha256'], 'frozen_bytes')
        return raw
    require(frozen(registration_path) == registration_raw, 'frozen_registration')
    job = m['job']; job_id = job['id']
    require(type(job_id) is str and job_id and '/' not in job_id and job_id not in ('.','..'), 'job_id')
    attempt = root / 'attempts' / job_id
    require(job['attempt_dir'] == str(attempt), 'attempt_layout')
    children = m['audit_batches']['children']
    require(type(children) is list and len(children) >= 2 and all(type(c) is dict for c in children)
            and len({c['id'] for c in children}) == len(children)
            and all(c['kind'] == 'worker' and c['id'] != 'integration' for c in children[:-1])
            and children[-1]['kind'] == children[-1]['id'] == 'integration', 'child_roster')
    integration = attempt / 'children/integration'
    require(children[-1]['attempt_dir'] == str(integration), 'integration_layout')
    require(type(m['python']) is str and type(m['repository']) is str and type(m['pinned_files']) is dict, 'source_layout')
    repository = _canonical(m['repository']); sources = {}; checked = {registration_path: registration_raw}
    source_hashes = {}
    for relative, supported in SUPPORTED_SOURCES.items():
        path = repository / 'notes/matched_cborg_2026-09-13' / relative
        expected = m['pinned_files'].get(str(path))
        require(type(expected) is str and expected in supported, 'incompatible_source_version')
        raw = _read(path)
        require(hashlib.sha256(raw).hexdigest() == expected, 'source_hash')
        sources[relative] = raw; checked[path] = raw; source_hashes[relative] = expected
    pure = _pure_source_functions(sources)
    histories = []; event_hashes = {}
    for name in ('transcript.jsonl','control.jsonl'):
        path = integration / name
        require(files[str(path.relative_to(root))]['links'] == 1, 'event_links')
        raw = frozen(path); checked[path] = raw
        histories.append(_frames(raw, _strict_json)); event_hashes[name] = hashlib.sha256(raw).hexdigest()
    report = _project(*histories, {**m, '_registration_path':str(registration_path)}, pure)
    require(report['zero_terminal_source_check'] is True, 'terminal_check_observed')
    for path, raw in checked.items(): require(_read(path) == raw, 'changed_after_scan')
    report.update(registration_sha256=hashlib.sha256(registration_raw).hexdigest(),
                  source_sha256=source_hashes, operational_evidence_sha256=event_hashes)
    return report


def verify(source_manifest, registration_path, inventory):
    """Recompute zero prior terminal checker; refuse ambiguity without content.

    No positive count is interpreted as a successful checker execution. Any
    exact checker attempt/admission/result rejects this narrow recovery mode.
    The caller separately verifies full freeze/process/accounting/source proof.
    This function has no filesystem mutation or actual checker/provider path.
    """
    try:
        return _verify(source_manifest, registration_path, inventory)
    except Exception:
        raise BudgetStop('closed-worker checkpoint requires complete evidence of zero prior terminal source checks') from None
