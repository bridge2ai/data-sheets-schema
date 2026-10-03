"""Strict saved native permission observations; no execution or authentication.

The caller supplies authority derived from its verified composition/runtime and
captures this whole raw manifest in its execution registration. A manifest embeds
raw UTF-8 policy/cases/launch/config/source-before/source-after/transcript/control,
version and provider-source members with SHA256 pins. It is a recorded observation,
not cryptographic proof that its claimed author actually ran the pinned binary.
Independent review remains necessary. Historical summaries alone are unsupported.

V1 preserves the selected command paths and callback cwd exactly. Only config,
loopback scripted-provider and the fixed no-I/O helper stub environment differ.
The seven closed cases observe three exact helper spellings, a source Read and
three restrictions; they do not establish universal filesystem permissions, real
helper correctness, authentication, provider billing or generation acceptance.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import PurePosixPath
import re
import shlex
from urllib.parse import urlsplit

from data_sheets_schema import native_attribution_controller as composition
from data_sheets_schema import native_attribution_registration as draft

KIND = 'd4d_native_saved_permission_probe'
VERSION = 1
ORIGIN = 'actual_native_binary_scripted_local_provider'
MAX_BYTES = 32 * 1024 * 1024
MAX_ROWS = 256
SYSTEM = 'Synthetic local permission probe only; execute exactly the scripted cases.'
EXPECTED_KEYS = {'runtime', 'policy', 'commands', 'source', 'permission_environment',
                 'controller_sources', 'instruction_sha256', 'system_sha256'}
MODULES = {'draft': 'source_attribution_preflight', 'final_evidence': 'evidence_assertions', 'recorder': 'cli'}


def _need(condition, message):
    if not condition:
        raise ValueError('saved permission probe: ' + message)


def _same(left, right):
    return draft._encoded(left) == draft._encoded(right)


def _object(value, keys, label):
    _need(type(value) is dict and set(value) == set(keys), label + ' has missing or unknown fields')
    return value


def _path(value):
    _need(type(value) is str and value.startswith('/') and '\0' not in value
          and '..' not in PurePosixPath(value).parts and str(PurePosixPath(value)) == value,
          'paths must be absolute canonical spellings')
    return PurePosixPath(value)


def _hash(value):
    _need(type(value) is str and re.fullmatch(r'[0-9a-f]{64}', value) is not None, 'invalid SHA256')


def stub_files():
    """The complete neutral helper package. These modules never open artifacts."""
    out = {'data_sheets_schema/__init__.py': ''}
    for role, module in MODULES.items():
        out[f'data_sheets_schema/{module}.py'] = (
            'import json, sys\n'
            f'print(json.dumps({{"d4d_permission_stub": {role!r}, "argv": sys.argv[1:]}}, '
            'sort_keys=True, separators=(",", ":")))\n')
    return out


def probe_cases(expected):
    """Closed case inventory derived from selected commands, never a saved flag."""
    commands, source = expected['commands'], expected['source']['path']
    rows = [{'id': role, 'tool': 'Bash', 'input': {'command': commands[role]}, 'allow': True}
            for role in MODULES]
    rows += [
        {'id': 'source_read', 'tool': 'Read', 'input': {'file_path': source}, 'allow': True},
        {'id': 'arbitrary_python', 'tool': 'Bash', 'input': {'command': shlex.join([
            expected['policy']['python'], '-c', 'print("D4D_UNREGISTERED_PERMISSION_PROBE")'])}, 'allow': False},
        {'id': 'modified_draft', 'tool': 'Bash', 'input': {'command': commands['draft'] +
            ' --d4d-unregistered-permission-argument'}, 'allow': False},
        {'id': 'source_write', 'tool': 'Write', 'input': {'file_path': source,
            'content': 'D4D_SOURCE_MUST_NOT_CHANGE\n'}, 'allow': False},
    ]
    return rows


def probe_argv(expected):
    """Exact native probe argv; never executed by this module."""
    controls = composition.load_controls()
    runtime = expected['runtime']
    return [runtime['executable']['path'], '--print', '--safe-mode', '--restricted',
        '--strict-mcp-config', '--no-session-persistence', '--model', runtime['model'],
        '--effort', runtime['effort'], '--disable-slash-commands', '--max-budget-usd',
        str(runtime['budget_guard_usd']), '--prompt-suggestions', 'false', '--output-format',
        'stream-json', '--verbose', '--permission-mode', 'dontAsk', '--tools', 'Read,Write,Bash',
        *controls['native_command_policy'].permission_arguments(expected['policy']), '--system-prompt', SYSTEM]


def _authority(expected, controls):
    _object(expected, EXPECTED_KEYS, 'expected authority')
    _object(expected['commands'], MODULES, 'selected commands')
    _object(expected['source'], {'path', 'sha256'}, 'source identity')
    _path(expected['source']['path']); _hash(expected['source']['sha256'])
    for key in ('instruction_sha256', 'system_sha256'):
        _hash(expected[key])
    _need(_same(expected['controller_sources'], composition.controller_sources()), 'controller closure differs')
    runtime, policy = expected['runtime'], expected['policy']
    _need(type(runtime) is dict and runtime.get('route') == 'claude_code_direct_stream_json_v1', 'unsupported runtime route')
    exe = _object(runtime.get('executable'), {'path', 'sha256', 'version', 'init_version'}, 'executable')
    _path(exe['path']); _hash(exe['sha256'])
    for value in (exe['version'], exe['init_version'], runtime.get('model'), runtime.get('effort')):
        _need(type(value) is str and bool(value.strip()) and '\0' not in value, 'missing runtime identity')
    budget = runtime.get('budget_guard_usd')
    _need(type(budget) in (int, float) and 0 < budget < float('inf'), 'invalid explicit probe budget guard')
    _need(_same(policy.get('pretool_control'), controls['native_control'].HISTORY_CONTRACT), 'only exact control v3 is supported')
    _path(policy['python']); _path(policy['readonly_lookups']['repository'])
    source = expected['source']['path']
    _need(source in policy['readonly_lookups']['inputs'], 'source is not a registered input')
    _need(not any(_path(p) in _path(source).parents for p in policy['readonly_lookups']['output_directories']),
          'source inside an output root is unsupported by this probe')
    _need(expected['commands']['draft'] == policy['attribution_command'], 'draft command differs')
    _need(expected['commands']['recorder'] == policy['post_final_recorder']['command'], 'recorder command differs')
    for role, module in MODULES.items():
        words = shlex.split(expected['commands'][role])
        _need(words[:3] == [policy['python'], '-m', 'data_sheets_schema.' + module],
              'selected command cannot be intercepted by the exact no-I/O module stub')
        if role == 'recorder':
            _need(words[3:5] == ['provenance', 'record'], 'unsupported recorder command')
    env = expected['permission_environment']
    _need(type(env) is dict and all(type(k) is str and type(v) is str and '\0' not in k+v for k,v in env.items()),
          'environment must be an explicit string mapping without credentials')
    _need(not any(k in env for k in ('ANTHROPIC_API_KEY', 'ANTHROPIC_AUTH_TOKEN', 'OPENAI_API_KEY', 'CBORG_API_KEY')),
          'production credential values must never be captured')
    classifications = {}
    for row in probe_cases(expected):
        if row['tool'] == 'Bash':
            kind, reason = composition._classify(row['input']['command'], policy['python'], set(), policy, controls)
        elif row['tool'] == 'Read':
            kind, reason = 'prescribed', 'a registered input the instruction reads'
        else:
            kind, reason = 'not_prescribed', 'a path outside the registered inputs and outputs'
        _need((kind == 'prescribed') is row['allow'], 'required case does not have its prescribed classification: ' + row['id'])
        classifications[row['id']] = (kind, reason)
    return classifications


def _members(value):
    names = {'policy.json', 'cases.json', 'launch.json', 'config.json', 'source.before', 'source.after',
             'version.txt', 'transcript.jsonl', 'control.jsonl', 'provider.py'} | set(stub_files())
    _object(value, names, 'raw members')
    raw = {}
    for name, entry in value.items():
        _object(entry, {'text', 'sha256'}, 'member ' + name)
        _need(type(entry['text']) is str, 'member is not captured UTF-8 text')
        content = entry['text'].encode('utf-8')
        _need(draft._sha(content) == entry['sha256'], 'raw member hash mismatch: ' + name)
        raw[name] = content
    for name, text in stub_files().items():
        _need(raw[name] == text.encode(), 'unreviewed helper stub: ' + name)
    _need(raw['provider.py'].strip() != b'', 'missing captured scripted-provider source')
    return raw


def _rows(raw, label):
    _need(raw.endswith(b'\n'), label + ' has an unterminated frame')
    rows = raw.split(b'\n')[:-1]
    _need(0 < len(rows) <= MAX_ROWS and all(row.strip() for row in rows), label + ' empty, oversized or blank')
    values = [draft._json(row) for row in rows]
    _need(all(type(v) is dict for v in values), label + ' has non-object frame')
    return values


def _neutral(launch, expected, raw):
    _object(launch, {'cwd', 'argv', 'environment', 'config_root', 'stub_root', 'provider_url',
                     'provider_source_sha256', 'exit_code', 'shutdown', 'executable'}, 'probe launch')
    _need(launch['cwd'] == expected['policy']['readonly_lookups']['repository'], 'probe callback cwd differs')
    _need(_same(launch['argv'], probe_argv(expected)), 'probe argv differs from exact permission arguments')
    _need(_same(launch['executable'], expected['runtime']['executable']), 'observed binary/version differs')
    _need(raw['version.txt'] == (expected['runtime']['executable']['version']+'\n').encode(), 'version stdout differs')
    config, stubs = _path(launch['config_root']), _path(launch['stub_root'])
    _need(config != stubs and config not in stubs.parents and stubs not in config.parents, 'probe isolation roots overlap')
    protected = [expected['policy']['readonly_lookups']['repository'], *expected['policy']['readonly_lookups']['inputs'],
                 *expected['policy']['readonly_lookups']['output_directories']]
    for root in (config, stubs):
        _need(all(root != _path(p) and root not in _path(p).parents and _path(p) not in root.parents for p in protected),
              'probe isolation root overlaps selected input/source/output authority')
    _need(_same(draft._json(raw['config.json']), {}), 'probe config is not explicitly isolated and empty')
    url = urlsplit(launch['provider_url'])
    _need(url.scheme == 'http' and url.hostname == '127.0.0.1' and url.port is not None
          and not url.username and not url.password and not url.query and not url.fragment
          and url.path in ('', '/'), 'provider must be an explicit loopback scripted endpoint')
    env = {**expected['permission_environment'], 'CLAUDE_CONFIG_DIR': str(config), 'PYTHONPATH': str(stubs),
           'ANTHROPIC_BASE_URL': launch['provider_url'], 'ANTHROPIC_API_KEY': 'd4d-local-permission-probe-token'}
    _need(_same(launch['environment'], env), 'unregistered probe environment substitution')
    _need(launch['provider_source_sha256'] == draft._sha(raw['provider.py']), 'scripted provider source differs')
    _need(type(launch['exit_code']) is int and launch['exit_code'] == 0, 'probe child exit was not integer zero')
    _need(_same(launch['shutdown'], {'control_initialized': True, 'control_shutdown_complete': True,
                                    'unfinished_control_workers': 0}), 'probe shutdown is incomplete')


def _result(event, case, expected, raw):
    content = event.get('message', {}).get('content')
    _need(type(content) is list and len(content) == 1, 'one unique tool result per case is required')
    item = content[0]
    _need(type(item) is dict and item.get('type') == 'tool_result' and item.get('tool_use_id') == case['id'],
          'tool result is unbound to its case')
    _need(item.get('is_error') is (not case['allow']), 'tool result contradicts expected admission')
    metadata = event.get('tool_use_result', {})
    _need(type(metadata) is dict and not any(metadata.get(k) for k in (
        'interrupted', 'backgroundTaskId', 'background_task_id', 'persistedOutputPath')), 'pending or unsupported tool result')
    exits = [metadata[k] for k in ('exitCode', 'exit_code') if k in metadata]
    _need(all(type(x) is int for x in exits) and len(set(exits)) <= 1, 'exit aliases are not exact matching integers')
    text = item.get('content')
    _need(type(text) is str and bool(text.strip()), 'tool result lacks raw text')
    if case['allow'] and case['tool'] == 'Bash':
        _need(exits and exits[0] == 0, 'admitted helper lacks explicit zero exit')
        payload = {'d4d_permission_stub': case['id'], 'argv': shlex.split(case['input']['command'])[3:]}
        _need(_same(draft._json(text), payload), 'helper execution marker or exact arguments differ')
        _need(type(metadata.get('stdout')) is str and _same(draft._json(metadata['stdout']), payload),
              'stdout and typed helper result disagree')
    elif case['allow']:
        _need(not exits or exits[0] == 0, 'source Read reports failure')
        marker = next((line.strip()[:128] for line in raw['source.before'].decode().splitlines() if line.strip()), '')
        _need(marker and marker in text, 'source Read lacks observed selected-source content')
    else:
        _need(not exits or exits[0] != 0, 'denied tool claims a successful exit')
        _need(text.startswith('Outside the registered tool policy'), 'denial was not the prescribed controller restriction')
        if 'stdout' in metadata:
            _need(type(metadata['stdout']) is str and metadata['stdout'] == text,
                  'denied tool stdout contradicts the denial result')
        _need('d4d_permission_stub' not in text, 'denied case contains helper execution marker')


def _settled_text(events, offset, session):
    """Allow ordinary assistant narration without dropping any executable frame.

    Scripted native providers emit a final OFFLINE_COMPLETE assistant message
    before the result. Text can also occur between settled cases. The caller
    invokes this only at those boundaries, never after the terminal result.
    """
    while offset < len(events):
        event = events[offset]
        if event.get('type') != 'assistant':
            break
        content = (event.get('message') or {}).get('content')
        if not (type(content) is list and content and all(type(block) is dict
                and set(block) == {'type', 'text'} and block['type'] == 'text'
                and type(block['text']) is str for block in content)):
            break
        _need(event.get('session_id') == session and event.get('parent_tool_use_id') is None,
              'assistant text is outside the initialized parent session')
        offset += 1
    return offset


def verify_saved_probe(raw_manifest: bytes, *, expected: dict) -> dict:
    """Verify captured records only. Never run a native CLI or accept a summary.

    Callers must derive expected from independently verified selected authority,
    and bind this exact raw manifest before dispatch. All malformed/unsupported
    inputs raise ValueError. No filesystem metadata/authenticity claim is made.
    """
    try:
        return _verify(raw_manifest, expected)
    except (KeyError, TypeError, IndexError, AttributeError, UnicodeError, OverflowError) as exc:
        raise ValueError('saved permission probe is malformed or incomplete') from exc


def _verify(raw_manifest, expected):
    _need(type(raw_manifest) is bytes and 0 < len(raw_manifest) <= MAX_BYTES, 'manifest must be bounded captured bytes')
    value = _object(draft._json(raw_manifest), {'kind', 'version', 'origin', 'binding', 'members'}, 'manifest')
    _need(value['kind'] == KIND and type(value['version']) is int and value['version'] == VERSION, 'unknown protocol')
    _need(value['origin'] == ORIGIN, 'mock/synthetic/historical-summary evidence is not native observation')
    controls = composition.load_controls()
    classifications = _authority(expected, controls)
    _need(_same(value['binding'], expected), 'saved binding differs from current selected authority')
    raw = _members(value['members'])
    cases = probe_cases(expected)
    _need(_same(draft._json(raw['cases.json']), cases), 'closed case inventory was omitted, duplicated, reordered or changed')
    _need(_same(draft._json(raw['policy.json']), expected['policy']), 'captured policy differs')
    _need(draft._sha(raw['source.before']) == expected['source']['sha256'] and raw['source.before'] == raw['source.after'],
          'selected source bytes changed or were not observed')
    launch = draft._json(raw['launch.json']); _neutral(launch, expected, raw)
    events, records = _rows(raw['transcript.jsonl'], 'transcript'), _rows(raw['control.jsonl'], 'control journal')
    native, policy = controls['native_control'], expected['policy']
    _need(len(records) == len(cases)+2, 'control journal lacks exact settled case decisions')
    clean = [{k:v for k,v in row.items() if k != 'at'} for row in records]
    _need(_same(clean[0], {'kind': 'initialize_sent', 'policy_sha256': native.digest(policy),
                         'frame': native.initialize_frame(policy['pretool_control'])}), 'wrong initialization sent')
    ack = {'type': 'control_response', 'response': {'subtype': 'success', 'request_id': native.INIT_ID}}
    _need(_same(events[0], ack) and _same(clean[1], {'kind': 'initialize_ack', 'frame': ack}), 'initialization acknowledgement differs')
    init = events[1]
    _need(init.get('type') == 'system' and init.get('subtype') == 'init', 'missing native init')
    _need(init.get('model') == expected['runtime']['model']
          and init.get('claude_code_version') == expected['runtime']['executable']['init_version']
          and init.get('cwd') == launch['cwd'] and init.get('tools') == ['Read', 'Write', 'Bash']
          and init.get('apiKeySource') == 'ANTHROPIC_API_KEY', 'native init differs from probe identity')
    _need(init.get('permissionMode', 'dontAsk') == 'dontAsk', 'native init contradicts permission mode')
    session = init.get('session_id')
    _need(type(session) is str and re.fullmatch(r'[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}', session), 'invalid session identity')
    offset = 2
    request_ids = set()
    outcomes = []
    for number, case in enumerate(cases):
        offset = _settled_text(events, offset, session)
        call, callback, result = events[offset:offset+3]; offset += 3
        _need(call.get('type') == 'assistant' and call.get('session_id') == session, 'tool call outside session/order')
        expected_block = {'type':'tool_use', 'id':case['id'], 'name':case['tool'], 'input':case['input']}
        _need(_same(call.get('message', {}).get('content'), [expected_block]), 'tool call differs from exact case')
        request_id = callback.get('request_id')
        _need(type(request_id) is str and request_id and request_id not in request_ids and request_id != native.INIT_ID,
              'missing or repeated callback identity')
        request_ids.add(request_id)
        wanted = {'type':'control_request','request_id':request_id,'request': {'subtype':'hook_callback',
            'callback_id': policy['pretool_control']['callback_id'], 'input': {'hook_event_name':'PreToolUse',
            'tool_name':case['tool'],'tool_use_id':case['id'],'cwd':launch['cwd'],'tool_input':case['input']}}}
        # Effort is optional probe observation, but if present must match selection.
        data = (callback.get('request') or {}).get('input') or {}
        if 'effort' in data:
            wanted['request']['input']['effort'] = expected['runtime']['effort']
        _need(_same(callback, wanted), 'callback payload differs from exact selected case')
        kind, reason = classifications[case['id']]
        decision = {'kind':'decision','request':callback,'classification':kind,'basis':reason,
            'response':{'type':'control_response','response':{'subtype':'success','request_id':request_id,
                        'response':native.hook_output(kind,reason)}}}
        _need(_same(clean[number+2], decision), 'parent decision does not match recomputed policy')
        _need(result.get('type') == 'user' and result.get('session_id') == session, 'result outside exact session/order')
        _result(result, case, expected, raw)
        outcomes.append({'id':case['id'],'admitted':case['allow'],'verified':True})
    offset = _settled_text(events, offset, session)
    _need(len(events) == offset+1, 'extra, pending, duplicate or post-terminal evidence')
    terminal = events[offset]
    _need(terminal.get('type') == 'result' and terminal.get('session_id') == session
          and terminal.get('is_error') is False
          and terminal.get('terminal_reason') == 'completed' and terminal.get('stop_reason') == 'end_turn',
          'native terminal is not explicitly successful')
    denied = terminal.get('permission_denials')
    _need(type(denied) is list and len(denied) == 3
          and all(type(row) is dict for row in denied)
          and sorted(row.get('tool_use_id', '') for row in denied) == sorted(c['id'] for c in cases if not c['allow']),
          'terminal denial inventory does not exactly match required restrictions')
    return {'instrument': KIND, 'version': VERSION, 'checked': True, 'passed': True,
        'basis': 'recomputed exact recorded native permission cases; helper execution was stubbed',
        'scope': 'selected command admission and recorded restrictions only; no universal Write permission claim',
        'manifest_sha256': draft._sha(raw_manifest), 'members': {name: {'sha256':draft._sha(content),'bytes':len(content)}
                                                             for name,content in sorted(raw.items())},
        'cases': outcomes, 'runtime': deepcopy(expected['runtime']['executable']),
        'probe': {key:deepcopy(launch[key]) for key in ('cwd','config_root','stub_root','provider_url','shutdown')},
        'unassessed': ['observation authenticity', 'production helper correctness', 'current authentication',
                       'provider billing', 'generation acceptance', 'owner launch authorization']}
