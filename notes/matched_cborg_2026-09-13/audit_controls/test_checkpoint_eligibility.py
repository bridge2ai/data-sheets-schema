"""Invented events and copied public sources only; no provider/scientific inputs."""
import copy
import hashlib
import json
import os
from pathlib import Path
import shlex

import pytest

from budgeted_cborg import BudgetStop
from . import checkpoint_eligibility as p

SOURCE = Path(__file__).resolve().parent.parent


def strict(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            assert key not in result
            result[key] = value
        return result
    def constant(_): raise ValueError('nonfinite')
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)


@pytest.fixture(scope='module')
def pure():
    sources = {name: (SOURCE / name).read_bytes() for name in p.SUPPORTED_SOURCES}
    assert all(hashlib.sha256(raw).hexdigest() in p.SUPPORTED_SOURCES[name] for name, raw in sources.items())
    return p._pure_source_functions(sources)


@pytest.fixture
def history(pure):
    manifest = {'python': '/synthetic/python', '_registration_path': '/synthetic/registration.json',
      'repository': '/synthetic/repository',
      'job': {'validator_argv': ['/synthetic/python', '-m', 'audit_controls.contract', '--registration', '/synthetic/registration.json']},
      'audit_batches': {'assemble_argv': ['/synthetic/python', '-m', 'assemble'], 'children': [
        {'id': 'integration', 'rounds': [{'check_argv': ['/synthetic/python', '-m', 'grammar1']},
          {'check_argv': ['/synthetic/python', '-m', 'grammar2']}], 'seal_argv': ['/synthetic/python', '-m', 'seal']}]}}
    ack = {'type': 'control_response', 'response': {'subtype': 'success', 'request_id': pure['INIT_ID'], 'response': {}}}
    events = [ack, {'type': 'system', 'subtype': 'init', 'session_id': 'synthetic-session'}]
    records = [{'kind': 'initialize_sent', 'frame': pure['initialize_frame'](), 'policy_sha256': 'a' * 64},
               {'kind': 'initialize_ack', 'frame': ack}]
    return events, records, manifest


def add_call(history, pure, tool='Read', command=None, error=False):
    events, records, manifest = history
    tid = 'synthetic-tool-' + str(len(events)); rid = 'synthetic-callback-' + str(len(events))
    payload = {'file_path': '/synthetic/private-read'} if tool != 'Bash' else {'command': command}
    call = {'type': 'tool_use', 'id': tid, 'name': tool, 'input': payload}
    events.append({'type': 'assistant', 'session_id': 'synthetic-session', 'message': {'role': 'assistant', 'content': [call]}})
    callback = {'type': 'control_request', 'request_id': rid, 'request': {'subtype': 'hook_callback',
        'callback_id': pure['CONTRACT']['callback_id'], 'input': {'hook_event_name': 'PreToolUse',
        'tool_name': tool, 'tool_input': copy.deepcopy(payload), 'tool_use_id': tid, 'cwd': manifest['repository']}}}
    events.append(callback)
    if tool == 'Bash':
        child = manifest['audit_batches']['children'][0]
        policy = {'validator_argv': manifest['job']['validator_argv'], 'assemble_argv': manifest['audit_batches']['assemble_argv'],
                  'draft_argv': [r['check_argv'] for r in child['rounds']] + [child['seal_argv']]}
        classification, basis = pure['classify_command'](command, manifest['python'], set(), policy)
    else: classification, basis = 'prescribed', 'synthetic-read-decision'
    response = {'type': 'control_response', 'response': {'subtype': 'success', 'request_id': rid,
                'response': pure['hook_output'](classification, basis)}}
    records.append({'kind': 'decision', 'request': copy.deepcopy(callback), 'classification': classification,
                    'basis': basis, 'response': response})
    events.append({'type': 'user', 'session_id': 'synthetic-session', 'message': {'role': 'user', 'content': [
      {'type': 'tool_result', 'tool_use_id': tid, 'is_error': error or classification == 'not_prescribed',
       'content': 'PRIVATE SCIENTIFIC SENTINEL MUST NEVER APPEAR'}]}})
    return tid


def report(history, pure): return p._project(*history, pure)


def test_zero_checks_without_native_terminal_is_valid_predicate(history, pure):
    add_call(history, pure)
    add_call(history, pure, 'Bash', shlex.join(history[2]['audit_batches']['children'][0]['rounds'][0]['check_argv']))
    result = report(history, pure)
    assert result['zero_terminal_source_check'] is True
    assert result['native_terminal_frames'] == 0
    assert result['checker_permission_admissions'] == 0
    assert result['tool_calls'] == result['tool_results'] == result['permission_decisions'] == 2
    assert result['carry_forward_authorized'] is False


@pytest.mark.parametrize('error', [False, True])
@pytest.mark.parametrize('quote', [False, True])
def test_completed_or_failed_checker_never_eligible(history, pure, error, quote):
    argv = history[2]['job']['validator_argv']
    command = shlex.join(argv) if not quote else ' '.join('"' + a + '"' for a in argv)
    add_call(history, pure, 'Bash', command, error)
    result = report(history, pure)
    assert result['predicate'] == 'terminal_check_observed'
    assert result['zero_terminal_source_check'] is False
    assert result['checker_tool_attempts'] == result['checker_permission_admissions'] == result['checker_result_envelopes'] == 1


def test_checker_with_missing_result_is_unproven(history, pure):
    add_call(history, pure, 'Bash', shlex.join(history[2]['job']['validator_argv']))
    history[0].pop()
    with pytest.raises(ValueError, match='incomplete_tools'): report(history, pure)


@pytest.mark.parametrize('command', [
    '/synthetic/python -m audit_controls.contract --registration /other',
    'echo x; /synthetic/python -m audit_controls.contract --registration /synthetic/registration.json',
    '$(/synthetic/python -m audit_controls.contract)',
    '/synthetic/python -m audit_controls.contract --registration /synthetic/registration.json --extra'])
def test_off_policy_checker_like_commands_denied_without_execution(history, pure, command):
    add_call(history, pure, 'Bash', command)
    assert report(history, pure)['zero_terminal_source_check'] is True
    history[1][-1]['classification'] = 'prescribed'
    with pytest.raises(ValueError, match='bash_policy'): report(history, pure)


@pytest.mark.parametrize('mutation', [
 'missing_call', 'missing_callback', 'missing_result', 'missing_decision', 'duplicate_call', 'duplicate_result',
 'duplicate_callback', 'duplicate_decision', 'orphan_decision', 'wrong_callback_id', 'wrong_cwd',
 'wrong_hook', 'wrong_tool', 'wrong_request_copy', 'wrong_response', 'unknown_tool',
 'session_change', 'nested_session', 'unrecognized_event', 'unrecognized_record',
 'duplicate_initialization', 'no_initialization', 'tool_after_terminal', 'denied_success', 'bool_error'])
def test_ambiguous_histories_fail_closed(history, pure, mutation):
    add_call(history, pure, 'Bash', 'not-a-prescribed-command')
    events, records, _ = history
    if mutation == 'missing_call': events.pop(2)
    elif mutation == 'missing_callback': events.pop(3)
    elif mutation == 'missing_result': events.pop(4)
    elif mutation == 'missing_decision': records.pop()
    elif mutation == 'duplicate_call': events.insert(3, copy.deepcopy(events[2]))
    elif mutation == 'duplicate_result': events.append(copy.deepcopy(events[-1]))
    elif mutation == 'duplicate_callback': events.insert(4, copy.deepcopy(events[3]))
    elif mutation == 'duplicate_decision': records.append(copy.deepcopy(records[-1]))
    elif mutation == 'orphan_decision':
        extra = copy.deepcopy(records[-1]); extra['request']['request_id'] = 'orphan'; extra['request']['request']['input']['tool_use_id'] = 'orphan'
        records.append(extra)
    elif mutation == 'wrong_callback_id': events[3]['request']['callback_id'] = 'unknown'
    elif mutation == 'wrong_cwd': events[3]['request']['input']['cwd'] = '/other'
    elif mutation == 'wrong_hook': events[3]['request']['input']['hook_event_name'] = 'PostToolUse'
    elif mutation == 'wrong_tool': events[3]['request']['input']['tool_name'] = 'Write'
    elif mutation == 'wrong_request_copy': records[-1]['request']['request']['input']['tool_input'] = {'command':'other'}
    elif mutation == 'wrong_response': records[-1]['response']['response']['response'] = {}
    elif mutation == 'unknown_tool': events[2]['message']['content'][0]['name'] = 'Task'
    elif mutation == 'session_change': events[4]['session_id'] = 'other'
    elif mutation == 'nested_session': events[2]['parent_tool_use_id'] = 'parent'
    elif mutation == 'unrecognized_event': events.append({'type':'unknown'})
    elif mutation == 'unrecognized_record': records.append({'kind':'unknown'})
    elif mutation == 'duplicate_initialization': events.append(events[0])
    elif mutation == 'no_initialization': events.pop(0)
    elif mutation == 'tool_after_terminal': events.insert(2, {'type':'result'})
    elif mutation == 'denied_success': events[4]['message']['content'][0]['is_error'] = False
    elif mutation == 'bool_error': events[4]['message']['content'][0]['is_error'] = 0
    with pytest.raises((ValueError, KeyError, TypeError)): report(history, pure)


def test_bash_payload_correlation_is_typed(history, pure):
    add_call(history, pure, 'Bash', 'not-prescribed')
    history[0][2]['message']['content'][0]['input']['timeout'] = False
    history[0][3]['request']['input']['tool_input']['timeout'] = 0
    history[1][-1]['request'] = copy.deepcopy(history[0][3])
    with pytest.raises(ValueError, match='bash_callback_input'): report(history, pure)


def test_read_runtime_numeric_string_rejection_is_recognized_without_execution(history, pure):
    events, records, _ = history
    call = {'type':'tool_use','id':'bad-read','name':'Read','input':{'file_path':'/synthetic/path','offset':'1'}}
    event = {'type':'assistant','session_id':'synthetic-session','message':{'role':'assistant','content':[call]}}
    errors = [{'expected':'number','code':'invalid_type','path':['offset'],'message':'Invalid input'}]
    result = {'type':'user','session_id':'synthetic-session','message':{'role':'user','content':[
      {'type':'tool_result','tool_use_id':'bad-read','is_error':True,'content':
       '<tool_use_error>InputValidationError: Read failed due to the following issue:\nThe parameter `offset` type is expected as `number` but provided as `unknown`</tool_use_error>'}]},
       'tool_use_result':'InputValidationError: ' + json.dumps(errors)}
    events.extend([event, result])
    records.append(pure['input_validation_rejection'](event, call, result, 3, 4, 'synthetic-session'))
    assert report(history, pure)['unexecuted_read_input_rejections'] == 1
    result['message']['content'][0]['content'] += 'ambiguous'
    with pytest.raises(ValueError, match='unmatched_call'): report(history, pure)


@pytest.mark.parametrize('raw', [b'', b'{}', b'{}\n\n', b'\n', b'[]\n', b'{bad}\n',
 b'{"x":1,"x":2}\n', b'{"x":NaN}\n', b'{}\r\nBAD', b'\xff\n'])
def test_bad_jsonl_refuses(raw):
    with pytest.raises((ValueError, AssertionError, UnicodeDecodeError)): p._frames(raw, strict)


def test_unicode_separator_is_inside_one_physical_frame():
    assert len(p._frames('{"x":"a\u2028b"}\n'.encode(), strict)) == 1


def test_complete_terminal_optional_but_unique(history, pure):
    add_call(history, pure)
    history[0].append({'type':'result','is_error':False,'result':'PRIVATE RESULT'})
    assert report(history, pure)['native_terminal_frames'] == 1
    history[0].append({'type':'result'})
    with pytest.raises(ValueError): report(history, pure)


def test_no_decoded_content_in_projection(history, pure):
    add_call(history, pure, 'Bash', 'PRIVATE_COMMAND_SECRET')
    history[0].append({'type':'assistant','session_id':'synthetic-session','message':{'role':'assistant',
       'content':[{'type':'text','text':'SECRET SOURCE REVIEW TEXT'}]}})
    encoded = json.dumps(report(history, pure))
    for secret in ('PRIVATE', 'SECRET', '/synthetic', 'synthetic-tool', 'synthetic-session', 'not_prescribed'):
        assert secret not in encoded


def inventory(root):
    files = {}; directories = []; groups = {}
    for path in root.rglob('*'):
        relative = str(path.relative_to(root))
        if path.is_dir(): directories.append(relative)
        else:
            info = path.stat()
            files[relative] = {'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                              'bytes':info.st_size,'links':info.st_nlink}
            groups.setdefault((info.st_dev, info.st_ino), []).append(relative)
    return {'kind':p.INVENTORY_KIND,'root':str(root),'files':files,'directories':sorted(directories),
            'hardlink_groups':sorted(sorted(v) for v in groups.values() if len(v) > 1)}


@pytest.fixture
def frozen_history(tmp_path, history, pure):
    root = tmp_path.resolve() / 'condition'; root.mkdir()
    repo = tmp_path.resolve() / 'repository'; repo.mkdir()
    reg = root / 'registration.json'; job = 'SYNTHETIC'
    integration = root / 'attempts' / job / 'children/integration'; integration.mkdir(parents=True)
    events, records, m = history
    m.pop('_registration_path')
    m.update(kind='d4d_native_audit_continuation',protocol_version=7,render_version=23,
      scientific_contract_transition={'kind':'frozen_pair_child_navigation_v1'},
      audit_batch_navigation={'kind':'explicit_child_reads_v1'},repository=str(repo),pinned_files={})
    m['job'].update(id=job,attempt_dir=str(root/'attempts'/job))
    m['job']['validator_argv'][-1] = str(reg)
    m['audit_batches']['kind'] = 'fresh_context_integrated_v1'
    m['audit_batches']['children'][0].update(kind='integration',attempt_dir=str(integration))
    m['audit_batches']['children'].insert(0, {'id':'worker_1','kind':'worker'})
    for rel, allowed in p.SUPPORTED_SOURCES.items():
        path = repo/'notes/matched_cborg_2026-09-13'/rel; path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes((SOURCE/rel).read_bytes())
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
        assert sha in allowed
        m['pinned_files'][str(path)] = sha
    add_call(history, pure)
    for name, value in [('transcript.jsonl',events),('control.jsonl',records)]:
        (integration/name).write_bytes(b''.join(json.dumps(v).encode()+b'\n' for v in value))
    reg.write_text(json.dumps(m))
    return m, reg, inventory(root), events, records


def rewrite(fixture):
    m, reg, inv, events, records = fixture
    root = Path(m['audit_batches']['children'][-1]['attempt_dir'])
    for name, value in [('transcript.jsonl',events),('control.jsonl',records)]:
        (root/name).write_bytes(b''.join(json.dumps(v).encode()+b'\n' for v in value))
    reg.write_text(json.dumps(m)); inv.clear(); inv.update(inventory(reg.parent))


def test_real_supported_source_contract_and_private_decoding(frozen_history):
    m, reg, inv, _, _ = frozen_history
    before = {p: p.read_bytes() for p in reg.parent.rglob('*') if p.is_file()}
    result = p.verify(m, reg, inv)
    assert result['zero_terminal_source_check'] is True
    assert result['registration_sha256'] == hashlib.sha256(reg.read_bytes()).hexdigest()
    assert all(sha in p.SUPPORTED_SOURCES[rel] for rel,sha in result['source_sha256'].items())
    assert result['tool_calls'] == result['read_calls'] == result['permission_decisions'] == 1
    assert result['carry_forward_authorized'] is False and result['scientific_acceptance'] is False
    assert before == {path:path.read_bytes() for path in reg.parent.rglob('*') if path.is_file()}


@pytest.mark.parametrize('mutation', [
 'null_checkpoint','wrong_protocol','bool_protocol','wrong_renderer','float_renderer','wrong_kind',
 'wrong_navigation','wrong_transition','wrong_batch_kind','wrong_attempt','wrong_integration',
 'missing_integration','duplicate_integration','wrong_validator','wrong_inventory_kind','wrong_inventory_root',
 'extra_inventory_key','malformed_descriptor','bool_size','bool_links','absolute_inventory_path',
 'traversal_inventory_path','missing_transcript_descriptor','missing_control_descriptor','stale_transcript_hash',
 'stale_registration_hash','different_manifest','source_pin_missing','source_pin_changed','source_bytes_changed'])
def test_bound_public_verifier_refuses_invalid_proofs(frozen_history, mutation):
    m, reg, inv, _, _ = frozen_history
    relative = str(Path(m['audit_batches']['children'][-1]['attempt_dir']).relative_to(reg.parent))
    if mutation == 'null_checkpoint': m['audit_worker_checkpoint'] = None
    elif mutation == 'wrong_protocol': m['protocol_version'] = 6
    elif mutation == 'bool_protocol': m['protocol_version'] = True
    elif mutation == 'wrong_renderer': m['render_version'] = 22
    elif mutation == 'float_renderer': m['render_version'] = 23.0
    elif mutation == 'wrong_kind': m['kind'] = 'generation'
    elif mutation == 'wrong_navigation': m['audit_batch_navigation'] = {'kind':'explicit_row_reads_v1'}
    elif mutation == 'wrong_transition': m['scientific_contract_transition'] = {'kind':'unknown'}
    elif mutation == 'wrong_batch_kind': m['audit_batches']['kind'] = 'checkpoint'
    elif mutation == 'wrong_attempt': m['job']['attempt_dir'] = '/other'
    elif mutation == 'wrong_integration': m['audit_batches']['children'][-1]['attempt_dir'] = '/other'
    elif mutation == 'missing_integration': m['audit_batches']['children'].pop()
    elif mutation == 'duplicate_integration': m['audit_batches']['children'].append(copy.deepcopy(m['audit_batches']['children'][-1]))
    elif mutation == 'wrong_validator': m['job']['validator_argv'][-1] = '/foreign'
    elif mutation == 'wrong_inventory_kind': inv['kind'] = 'unknown'
    elif mutation == 'wrong_inventory_root': inv['root'] = '/other'
    elif mutation == 'extra_inventory_key': inv['extra'] = True
    elif mutation == 'malformed_descriptor': inv['files'][relative+'/transcript.jsonl']['extra'] = True
    elif mutation == 'bool_size': inv['files'][relative+'/transcript.jsonl']['bytes'] = True
    elif mutation == 'bool_links': inv['files'][relative+'/transcript.jsonl']['links'] = True
    elif mutation == 'absolute_inventory_path': inv['files']['/foreign'] = inv['files']['registration.json']
    elif mutation == 'traversal_inventory_path': inv['files']['../foreign'] = inv['files']['registration.json']
    elif mutation == 'missing_transcript_descriptor': inv['files'].pop(relative+'/transcript.jsonl')
    elif mutation == 'missing_control_descriptor': inv['files'].pop(relative+'/control.jsonl')
    elif mutation == 'stale_transcript_hash': inv['files'][relative+'/transcript.jsonl']['sha256'] = '0'*64
    elif mutation == 'stale_registration_hash': inv['files']['registration.json']['sha256'] = '0'*64
    elif mutation == 'different_manifest': m['extra'] = 'PRIVATE_SOURCE_SENTINEL'
    elif mutation == 'source_pin_missing': m['pinned_files'].pop(next(iter(m['pinned_files'])))
    elif mutation == 'source_pin_changed': m['pinned_files'][next(iter(m['pinned_files']))] = '0'*64
    elif mutation == 'source_bytes_changed': Path(next(iter(m['pinned_files']))).write_text('raise RuntimeError("PRIVATE_SOURCE_SENTINEL")')
    # Most mutations describe a self-consistent but unsupported source registration.
    # The separate different_manifest and stale registration cases test binding failures.
    if mutation not in ('different_manifest','stale_registration_hash'):
        reg.write_text(json.dumps(m)); raw = reg.read_bytes()
        inv['files']['registration.json'] = {'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'links':1}
    with pytest.raises(BudgetStop) as exc: p.verify(m, reg, inv)
    assert str(exc.value) == 'closed-worker checkpoint requires complete evidence of zero prior terminal source checks'
    assert 'PRIVATE_SOURCE_SENTINEL' not in str(exc.value)


def test_public_api_rejects_observed_checker_even_when_result_error(frozen_history, pure):
    m, reg, inv, events, records = frozen_history
    # add_call expects integration first only for constructing the fixture classifier.
    fixture_manifest = copy.deepcopy(m); fixture_manifest['audit_batches']['children'] = [m['audit_batches']['children'][-1]]
    add_call((events, records, fixture_manifest), pure, 'Bash', shlex.join(m['job']['validator_argv']), error=True)
    rewrite(frozen_history)
    with pytest.raises(BudgetStop): p.verify(m, reg, inv)


@pytest.mark.parametrize('target', ['registration','transcript','source'])
def test_symlink_input_is_refused(frozen_history, tmp_path, target):
    m, reg, inv, _, _ = frozen_history
    path = reg if target == 'registration' else Path(next(iter(m['pinned_files']))) if target == 'source' else Path(m['audit_batches']['children'][-1]['attempt_dir'])/'transcript.jsonl'
    outside = tmp_path.resolve()/'target'; outside.write_bytes(path.read_bytes()); path.unlink(); path.symlink_to(outside)
    with pytest.raises(BudgetStop): p.verify(m, reg, inv)


def test_mutation_during_projection_is_refused(frozen_history, monkeypatch):
    m, reg, inv, _, _ = frozen_history
    original = p._project
    def mutate(*args):
        result = original(*args)
        (Path(m['audit_batches']['children'][-1]['attempt_dir'])/'control.jsonl').write_bytes(b'changed')
        return result
    monkeypatch.setattr(p, '_project', mutate)
    with pytest.raises(BudgetStop): p.verify(m, reg, inv)


def test_stable_output_has_no_private_paths_or_values(frozen_history):
    m, reg, inv, _, _ = frozen_history
    raw = json.dumps(p.verify(m, reg, inv))
    for forbidden in (str(reg.parent), 'SYNTHETIC', 'PRIVATE SCIENTIFIC', '/synthetic/private-read', 'synthetic-session'):
        assert forbidden not in raw


def legacy_control_source(raw):
    # Exact released older bytes from the reviewed source-only delta. This
    # fixture needs no historical Git object or private execution checkout.
    text = raw.decode()
    substitutions = (("#: The native runtime's refusal to overwrite a file this session has not\n#: read (#2285): observed in the first direct-arm canary on a Write of the\n#: full record, with no PreToolUse callback and no write.\nUNREAD_WRITE_MESSAGE = 'File has not been read yet. Read it first before writing to it.'\n\n\n", ''), ('    """Recognize the evidenced, unexecuted Read numeric-string rejection,\n    and the evidenced, unexecuted Write of an unread file (#2285).\n\n    For the Write, the call carries exactly `file_path` and `content` and the\n    result is exactly the runtime\'s unread-file wrapper and its plain error\n    text; the record keeps the literal, unresolved target path (#2330).\n', '    """Recognize the evidenced, unexecuted Read numeric-string rejection.\n'), ("        call.get('type') != 'tool_use' or call.get('name') not in ('Read', 'Write') or\n", "        call.get('type') != 'tool_use' or call.get('name') != 'Read' or\n"), ("    if call.get('name') == 'Write':\n        # Exactly the runtime's unread-file refusal: the Write carried its\n        # two arguments, the result is the error wrapper and the plain error\n        # text, and nothing else. The call never reached the hook, so no\n        # decision exists and no file was written (#2285).\n        if (not isinstance(payload, dict) or set(payload) != {'file_path', 'content'} or\n            not isinstance(payload['file_path'], str) or not payload['file_path'] or\n            not isinstance(payload['content'], str) or\n            result['content'] != f'<tool_use_error>{UNREAD_WRITE_MESSAGE}</tool_use_error>' or\n            result_event.get('tool_use_result') != f'Error: {UNREAD_WRITE_MESSAGE}'):\n            return None\n        return {'kind': 'input_rejected_before_callback', 'tool_use_id': call['id'],\n                'tool': 'Write', 'rejection': 'file_not_read', 'file_path': payload['file_path'],\n                'session_id': call_session,\n                'call_line': call_line, 'result_line': result_line,\n                'call_sha256': digest(call_event), 'result_sha256': digest(result_event)}\n", ''))
    for current, historical in substitutions:
        assert text.count(current) == 1
        text = text.replace(current, historical, 1)
    result = text.encode()
    assert hashlib.sha256(result).hexdigest() == 'f87a5bfe77e37a8ac2961487355b2a31d4b8a7d556fc095531e4c4056ee08a3e'
    return result


def test_exact_legacy_source_version_is_accepted(frozen_history):
    m, reg, inv, _, _ = frozen_history
    rel = 'native_controls/native_control.py'
    path = Path(m['repository'])/'notes/matched_cborg_2026-09-13'/rel
    path.write_bytes(legacy_control_source(path.read_bytes()))
    m['pinned_files'][str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
    rewrite(frozen_history)
    result = p.verify(m, reg, inv)
    assert result['zero_terminal_source_check'] is True
    assert result['source_sha256'][rel] == 'f87a5bfe77e37a8ac2961487355b2a31d4b8a7d556fc095531e4c4056ee08a3e'


def test_pure_read_recognition_and_classifier_behavior_identical(history, pure):
    sources = {name:(SOURCE/name).read_bytes() for name in p.SUPPORTED_SOURCES}
    sources['native_controls/native_control.py'] = legacy_control_source(sources['native_controls/native_control.py'])
    legacy = p._pure_source_functions(sources)
    test_read_runtime_numeric_string_rejection_is_recognized_without_execution(copy.deepcopy(history), legacy)
    test_read_runtime_numeric_string_rejection_is_recognized_without_execution(copy.deepcopy(history), pure)
    for command in [shlex.join(history[2]['job']['validator_argv']), 'not-prescribed', 'x; y']:
        fixture = copy.deepcopy(history); add_call(fixture, pure, 'Bash', command)
        assert report(fixture, pure) == report(fixture, legacy)


def test_callback_free_write_is_unsupported_for_both_versions(history, pure):
    sources = {name:(SOURCE/name).read_bytes() for name in p.SUPPORTED_SOURCES}
    sources['native_controls/native_control.py'] = legacy_control_source(sources['native_controls/native_control.py'])
    legacy = p._pure_source_functions(sources)
    add_call(history, pure, 'Write'); history[0].pop(3); history[1].pop()
    history[0][-1]['message']['content'][0]['is_error'] = True
    for functions in (pure, legacy):
        with pytest.raises(ValueError, match='unsupported_callback_free_tool'):
            report(history, functions)
