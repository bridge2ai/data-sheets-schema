"""Saved native-shared permission observations, never a probe launcher.

The caller derives ``expected`` from captured S/C/R and binds these exact raw
bytes in E. This checks seven complete recorded traces, not their authenticity,
production helper execution, authentication or authorization to run a model.
The old native_execution_permissions protocol is deliberately unchanged.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
from decimal import Decimal
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shlex
from urllib.parse import urlsplit

from data_sheets_schema import native_attribution_controller as composition
from data_sheets_schema import native_shared_contract as contract
from data_sheets_schema import native_shared_policy as command_policy

KIND = contract.KINDS['permission']
EXPECTED_KIND = contract.KINDS['permission_expected']
RECIPE_KIND = contract.KINDS['permission_recipe']
VERSION = contract.VERSION
ORIGIN = 'native_cli_local_scripted_provider'
SYSTEM = 'Synthetic local permission probe only; execute exactly the scripted cases.'
EXPECTED_KEYS = {'kind', 'version', 'runtime', 'selection', 'policy', 'commands',
                 'source', 'permission_environment', 'controller_sources',
                 'instruction_sha256', 'system_sha256', 'production_sources', 'probe_recipe'}
MODULES = {'stage': 'native_shared_stage', 'draft': 'source_attribution_preflight',
           'final_evidence': 'evidence_assertions', 'recorder': 'cli'}
CONTEXTS = ('receipt', 'worker', 'omission', 'integration')
STOPS = ('future_response_write', 'sealed_request_write', 'stale_response_write',
         'outside_response_write', 'source_write', 'helper_owned_write')
TRACES = ('settled',) + tuple('stop-' + name for name in STOPS)
NONRESPONSE = ('request_ready', 'receipt_zero_work', 'await_core', 'assembly_complete', 'failed')
MAX_MEMBER = contract.HARD_LIMITS['permission_member_bytes']
MAX_RAW = contract.HARD_LIMITS['permission_decoded_total_bytes']
MAX_METADATA = contract.HARD_LIMITS['permission_metadata_wire_bytes']
MAX_WIRE = contract.HARD_LIMITS['permission_wire_bytes']
MAX_MEMBERS = contract.HARD_LIMITS['permission_members']
MAX_RECIPE = contract.HARD_LIMITS['permission_recipe_sources']
MAX_ROWS = contract.HARD_LIMITS['permission_jsonl_rows_per_member']


def _need(condition, message):
    if not condition:
        raise ValueError('native shared permission: ' + message)


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _encoded(value):
    return contract.canonical(value)

def _same(left, right):
    return _encoded(left) == _encoded(right)


def _object(value, keys, label):
    _need(type(value) is dict and set(value) == set(keys), label + ' has missing/unknown fields')
    return value


def _positive(value, label, limit=None):
    _need(type(value) is int and value > 0 and (limit is None or value <= limit), label + ' is not a bounded positive integer')
    return value


def _text(value, label):
    _need(type(value) is str and bool(value.strip()) and '\0' not in value, label + ' is not text')
    value.encode('utf-8')
    return value


def _path(value):
    _text(value, 'path')
    path = PurePosixPath(value)
    _need(value.startswith('/') and not value.startswith('//') and '..' not in path.parts
          and str(path) == value and value != '/' and all(ord(c) >= 32 for c in value),
          'path is not canonical absolute')
    return path


def _hash(value):
    _need(type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None, 'invalid SHA256')
    return value


def _pin(value, raw=None):
    _object(value, {'path', 'sha256', 'bytes'}, 'file pin')
    _path(value['path']); _hash(value['sha256']); _positive(value['bytes'], 'file bytes')
    if raw is not None:
        _need(len(raw) == value['bytes'] and _sha(raw) == value['sha256'], 'captured file differs from authority')
    return value


def _json(raw, limit=MAX_MEMBER):
    return contract.strict_json(raw, 'native shared permission JSON', max_bytes=limit)

def _budget(value):
    _need(type(value) is str and len(value) <= 32 and
          re.fullmatch(r'[0-9]+(?:\.[0-9]+)?', value) is not None and Decimal(value) > 0,
          'budget guard must retain its exact positive decimal spelling')
    return value


def _runtime(value):
    """Check the frozen declaration shape without reading/running its binary.

    Current executable identity and actual auth observation remain the caller's
    pre-dispatch gates. This saved-observation parser never probes either one.
    """
    from data_sheets_schema import native_execution_registration as registration
    _object(value, registration.RUNTIME_KEYS, 'runtime declaration')
    _need(value['route'] == registration.ROUTE, 'unsupported direct route')
    exe = _object(value['executable'], {'path','sha256','version','init_version'}, 'executable')
    _path(exe['path']); _hash(exe['sha256'])
    _text(exe['version'], 'version'); _text(exe['init_version'], 'init version')
    identifier = r'[A-Za-z0-9][A-Za-z0-9._:+/@\[\]-]{0,255}'
    for key in ('model','effort'):
        _need(type(value[key]) is str and re.fullmatch(identifier, value[key]) is not None, 'runtime identifier differs')
    auxiliary = value['auxiliary_models']
    _need(type(auxiliary) is list and len(auxiliary) <= 32 and all(type(x) is str and
          re.fullmatch(identifier,x) is not None for x in auxiliary), 'invalid auxiliary model list')
    _need(len(set(auxiliary)) == len(auxiliary) and value['model'] not in auxiliary, 'duplicate model identity')
    limits = _object(value['limits'], {'contextWindow','maxOutputTokens'}, 'runtime limits')
    for key,count in limits.items():
        _positive(count, key)
    _need(limits['maxOutputTokens'] <= limits['contextWindow'], 'output limit exceeds context assertion')
    for key in ('limits_basis','provider'):
        _text(value[key], key)
    auth = _object(value['auth'], {'loggedIn','authMethod','apiProvider','subscriptionType','expected_api_key_source'}, 'auth selection')
    _need(auth['loggedIn'] is True and auth['authMethod'] == 'claude.ai' and auth['apiProvider'] == 'firstParty'
          and auth['expected_api_key_source'] == 'none', 'unsupported selected auth declaration')
    _text(auth['subscriptionType'], 'subscription type')
    env = value['environment']
    _need(type(env) is dict and not set(env) - registration.BASE_ENV_KEYS
          and registration.ENV_REQUIRED <= set(env), 'runtime environment shape differs')
    for key,text in env.items():
        _need(type(text) is str and len(text) <= 16384 and not any(ch in text for ch in ('\0','\n','\r'))
              and (bool(text.strip()) or key == 'CLAUDE_SECURESTORAGE_CONFIG_DIR'), 'invalid runtime environment text')
    _path(env['HOME'])
    for path in env['PATH'].split(':'):
        _path(path)
    _need(env['CLAUDE_CODE_DISABLE_1M_CONTEXT'] in ('0','1'), 'context environment selection differs')
    if env['CLAUDE_SECURESTORAGE_CONFIG_DIR']:
        _path(env['CLAUDE_SECURESTORAGE_CONFIG_DIR'])
    _positive(value['deadline_seconds'], 'deadline', 86400); _budget(value['budget_guard_usd'])
    awake = _object(value['keep_awake'], {'policy','host_platform','basis'}, 'keep-awake declaration')
    _need(awake['policy'] in ('macos_iokit_ims_v1','not_applicable'), 'unknown keep-awake declaration')
    _text(awake['host_platform'], 'host platform'); _text(awake['basis'], 'keep-awake basis')
    _need(awake['policy'] != 'macos_iokit_ims_v1' or awake['host_platform'] == 'darwin', 'IOKit platform differs')


def _dependencies():
    # Fixed imports only. Neither a saved module name nor a passed callback can
    # select the classifier or replace the contract.
    from data_sheets_schema import native_shared_contract as contract
    from data_sheets_schema import native_shared_effects as effects
    return contract, effects


def stub_files():
    """Exact four harmless helper substitutions; no stub opens an artifact."""
    out = {'stubs/data_sheets_schema/__init__.py': ''}
    for role, module in MODULES.items():
        out['stubs/data_sheets_schema/' + module + '.py'] = (
            'import json, sys\n'
            'print(json.dumps({"d4d_shared_permission_stub": ' + repr(role) +
            ', "argv": sys.argv[1:]}, sort_keys=True, separators=(",", ":")))\n')
    return out


def recipe_sources():
    """The fixed recipe closure, read only from this loaded implementation.

    The recipe driver creates deterministic data; it has no subprocess/native
    launcher. A separately reviewed probe consumer must supply actual records.
    """
    out = stub_files()
    out['recipe/projection.py'] = Path(__file__).read_bytes().decode('utf-8')
    out['recipe/provider.py'] = (
        '"""Pure scripted reply selection, no network or native launcher."""\n'
        'def reply(cases, number):\n'
        '    if number == len(cases):\n'
        '        return {"type": "text", "text": "OFFLINE_COMPLETE"}\n'
        '    case = cases[number]\n'
        '    return {"type": "tool_use", "id": case["id"], '
        '"name": case["tool"], "input": case["input"]}\n')
    out['recipe/harness.py'] = (
        '"""Data-only recipe adapter; does not launch a probe."""\n'
        'from data_sheets_schema.native_shared_permissions import projection, probe_cases\n'
        'def prepare(expected, selection, launch, session_id):\n'
        '    return projection(expected, selection, launch, session_id), '
        'probe_cases(expected, selection, launch, session_id)\n')
    return out


def recipe(expected):
    """Derive source/stub joins from independently captured production pins."""
    contract, _ = _dependencies()
    sources = recipe_sources()
    rows = [{'member': name, 'sha256': _sha(text.encode()), 'bytes': len(text.encode())}
            for name, text in sorted(sources.items())]
    by_module = {row['module']: row for row in expected['production_sources']}
    mappings = []
    for role, module in MODULES.items():
        name = 'data_sheets_schema.' + module
        member = 'stubs/data_sheets_schema/' + module + '.py'
        entrypoint = name + '.__main__' if role == 'recorder' else name
        mappings.append({'module': name, 'production_sha256': by_module[entrypoint]['sha256'],
                         'stub_member': member, 'stub_sha256': _sha(sources[member].encode())})
    descriptor = {'kind': RECIPE_KIND, 'version': VERSION,
                  'roles': dict(contract.ROLE_RELATIVE_PATHS), 'contexts': list(CONTEXTS),
                  'traces': list(TRACES), 'sources': rows, 'module_map': mappings}
    return {'kind': RECIPE_KIND, 'version': VERSION, 'descriptor_sha256': _sha(_encoded(descriptor)),
            'sources': rows, 'module_map': mappings}


def _source_closure(expected):
    contract, effects = _dependencies()
    rows = expected['production_sources']
    _need(type(rows) is list and 0 < len(rows) <= 640, 'invalid production source closure')
    names, paths = set(), set()
    for row in rows:
        _object(row, {'module', 'path', 'sha256', 'bytes'}, 'production source')
        _text(row['module'], 'module'); _path(row['path']); _hash(row['sha256'])
        _positive(row['bytes'], 'source bytes', 8_000_000)
        _need(row['module'] not in names and row['path'] not in paths, 'duplicate production source')
        names.add(row['module']); paths.add(row['path'])
    by_module = {row['module']: row for row in rows}
    for module, file in [('data_sheets_schema.native_shared_permissions', __file__),
                         ('data_sheets_schema.native_shared_contract', contract.__file__),
                         ('data_sheets_schema.native_shared_effects', effects.__file__),
                         ('data_sheets_schema.native_shared_policy', command_policy.__file__)]:
        raw = Path(file).read_bytes()
        wanted = {'module': module, 'path': str(Path(file).resolve()), 'bytes': len(raw), 'sha256': _sha(raw)}
        _need(_same(by_module.get(module), wanted), 'loaded fixed source differs: ' + module)
    for role,module in MODULES.items():
        name = 'data_sheets_schema.' + module + ('.__main__' if role == 'recorder' else '')
        _need(name in names, 'missing mapped production helper entrypoint')
    _need(_same(expected['probe_recipe'], recipe(expected)), 'probe recipe is not the fixed reviewed closure')


def _authority(expected, selection, controls):
    _object(expected, EXPECTED_KEYS, 'expected')
    _need(expected['kind'] == EXPECTED_KIND and type(expected['version']) is int
          and expected['version'] == VERSION, 'unknown expected protocol')
    _pin(expected['selection']); _pin(expected['source'])
    for name in ('instruction_sha256', 'system_sha256'):
        _hash(expected[name])
    _need(_same(expected['controller_sources'], composition.controller_sources()), 'controller closure differs')
    _need(selection['registration_path'] == expected['selection']['path'], 'selected path differs')
    _need(_same(selection['inputs']['bundle'], expected['source']), 'selected bundle identity differs')
    _need(selection['kind'] == 'd4d_native_shared_selection' and type(selection['version']) is int
          and selection['version'] == 1, 'unknown selection')
    _positive(selection['bounds']['max_submissions'], 'max submissions', 4099)
    _path(selection['stage_root'])
    runtime, policy = expected['runtime'], expected['policy']
    _runtime(runtime)
    _need(type(runtime) is dict and runtime.get('route') == 'claude_code_direct_stream_json_v1', 'runtime route differs')
    exe = _object(runtime['executable'], {'path', 'sha256', 'version', 'init_version'}, 'executable')
    _path(exe['path']); _hash(exe['sha256'])
    for value in (exe['version'], exe['init_version'], runtime['model'], runtime['effort']):
        _text(value, 'runtime identity')
    _budget(runtime['budget_guard_usd'])
    _need(_same(policy['pretool_control'], controls['native_control'].HISTORY_CONTRACT), 'unrecognized native control')
    _path(policy['python']); _path(policy['readonly_lookups']['repository'])
    _need(selection['stage_root'] in policy['readonly_lookups']['output_directories'], 'exact stage root absent')
    _need(expected['source']['path'] in policy['readonly_lookups']['inputs'], 'source is not registered')
    _object(expected['commands'], MODULES, 'commands')
    wanted_stage = [policy['python'], '-m', 'data_sheets_schema.native_shared_stage',
                    'advance', '--registration', expected['selection']['path']]
    _need(shlex.split(expected['commands']['stage']) == wanted_stage, 'stage helper arguments differ')
    for role, module in MODULES.items():
        _need(shlex.split(expected['commands'][role])[:3] ==
              [policy['python'], '-m', 'data_sheets_schema.' + module], 'unsupported helper substitution')
    _need(expected['commands']['draft'] == policy['attribution_command'], 'draft spelling differs')
    _need(expected['commands']['recorder'] == policy['post_final_recorder']['command'], 'recorder spelling differs')
    _need(shlex.split(expected['commands']['recorder'])[3:5] == ['provenance', 'record'], 'recorder arguments differ')
    env = expected['permission_environment']
    _need(type(env) is dict and all(type(k) is str and type(v) is str and '\0' not in k+v for k,v in env.items()),
          'environment is not an exact string mapping')
    _need(not any(k in env for k in ('ANTHROPIC_API_KEY', 'ANTHROPIC_AUTH_TOKEN', 'OPENAI_API_KEY', 'CBORG_API_KEY')),
          'permission authority must not contain credentials')
    from data_sheets_schema import native_execution_registration as registration
    derived_names = {'CLAUDE_CONFIG_DIR','PYTHONPATH','VIRTUAL_ENV','D4D_LAUNCH_INSTRUCTION','D4D_MANIFEST','D4D_PROFILE'}
    _need(set(env) == set(runtime['environment']) | set(registration.POLICY_ENV) | derived_names,
          'production environment has missing or extra fields')
    _need(all(env[key] == value for key,value in {**runtime['environment'], **registration.POLICY_ENV}.items()),
          'fixed or selected environment differs')
    _need(env['D4D_PROFILE'] == selection['inputs']['profile']['name'], 'environment profile differs')
    manifest = selection['inputs']['source_manifest']
    _need(env['D4D_MANIFEST'] == (manifest['path'] if manifest else 'None'), 'environment source manifest differs')
    for key in ('CLAUDE_CONFIG_DIR','PYTHONPATH','VIRTUAL_ENV','D4D_LAUNCH_INSTRUCTION'):
        _path(env[key])
    _source_closure(expected)


def _stage_leaf(relative, selection):
    contract, _ = _dependencies()
    roles = contract.ROLE_RELATIVE_PATHS
    fixed = {v for k,v in roles.items() if not k.endswith('_root')}
    if relative in fixed:
        return True
    match = re.fullmatch(r'(records|observations|requests|responses)/([0-9]{6})\.(json|bin)', relative)
    if not match:
        return False
    directory, digits, suffix = match.groups(); number = int(digits)
    if directory in ('requests', 'responses'):
        return 1 <= number <= selection['bounds']['max_submissions'] and suffix == ('bin' if directory == 'responses' else 'json')
    limit = selection['bounds']['max_history_records'] if directory == 'records' else 32768
    return 0 <= number < limit and suffix == 'json'


def projected_policy(expected, selection, effect_root):
    """Closed role projection; never resolves or opens a path from evidence."""
    _path(effect_root)
    source_root = _path(selection['stage_root']); target_root = _path(effect_root)
    policy = deepcopy(expected['policy']); lookup = policy['readonly_lookups']
    def mapped(value):
        path = _path(value)
        if source_root not in path.parents:
            _need(path != source_root, 'directory cannot be a file-map key')
            return value
        relative = str(path.relative_to(source_root))
        _need(_stage_leaf(relative, selection), 'unknown stage-owned path')
        return str(target_root / relative)
    dirs = lookup['output_directories']
    _need(type(dirs) is list and dirs.count(str(source_root)) == 1 and len(set(dirs)) == len(dirs), 'ambiguous stage envelope')
    lookup['output_directories'] = [effect_root if value == str(source_root) else str(_path(value)) for value in dirs]
    inputs = lookup['inputs']
    _need(type(inputs) is list and len(inputs) == len(set(inputs)), 'ambiguous input paths')
    lookup['inputs'] = [mapped(value) for value in inputs]
    _need(len(lookup['inputs']) == len(set(lookup['inputs'])), 'projected input collision')
    for field in ('bounded_reads', 'write_paths'):
        if field not in lookup or (field == 'write_paths' and lookup[field] is None):
            continue
        old = lookup[field]
        _need(type(old) is dict and (field != 'write_paths' or bool(old)), 'unsupported file-map representation')
        new = {}
        for value, cap in old.items():
            _positive(cap, field + ' cap')
            path = mapped(value)
            _need(path not in new, 'projected file-map collision')
            if field == 'bounded_reads':
                _need(value in inputs, 'bounded Read is not an input')
            else:
                _need(any(_path(folder) in _path(value).parents for folder in dirs), 'Write outside output envelope')
            new[path] = cap
        lookup[field] = new
    if lookup.get('write_paths') is not None:
        # Exact ordinary destinations must come from the selected policy, never
        # from the probe's four representative contexts or an advertised map.
        _, effects = _dependencies()
        _need(hasattr(effects, 'ordinary_write_paths'),
              'this fixed classifier cannot establish a complete ordinary Write domain')
        ordinary = list(effects.ordinary_write_paths(expected['policy']))
        _need(ordinary and len(set(ordinary)) == len(ordinary),
              'selected policy has no complete finite ordinary Write domain')
        required = [str(target_root / 'responses' / ('%06d.bin' % number))
                    for number in range(1, selection['bounds']['max_submissions'] + 1)]
        for value in ordinary:
            _path(value)
            _need(source_root not in _path(value).parents, 'ordinary Write domain contains stage paths')
        _need(all(path in lookup['write_paths'] for path in required + ordinary), 'incomplete global Write map')
    return policy


def _roots(expected, selection, launch):
    roots = [_path(launch[name]) for name in ('config_root', 'stub_root', 'effect_root', 'evidence_root')]
    protected = [expected['policy']['readonly_lookups']['repository'], expected['selection']['path'],
                 expected['source']['path'], selection['stage_root'],
                 *expected['policy']['readonly_lookups']['inputs'],
                 *expected['policy']['readonly_lookups']['output_directories']]
    protected += [value for key,value in expected['permission_environment'].items()
                  if key in ('CLAUDE_CONFIG_DIR', 'D4D_LAUNCH_INSTRUCTION') and value.startswith('/')]
    protected_paths = [_path(x) for x in protected]
    for number, root in enumerate(roots):
        for other in roots[number+1:] + protected_paths:
            _need(root != other and root not in other.parents and other not in root.parents, 'neutral roots overlap authority')
    return roots


def probe_argv(expected, probe_policy):
    """Exact recorded argv, never executed here."""
    controls = composition.load_controls(); runtime = expected['runtime']
    return [runtime['executable']['path'], '--print', '--safe-mode', '--restricted',
            '--strict-mcp-config', '--no-session-persistence', '--model', runtime['model'],
            '--effort', runtime['effort'], '--disable-slash-commands', '--max-budget-usd',
            _budget(runtime['budget_guard_usd']), '--prompt-suggestions', 'false', '--output-format',
            'stream-json', '--verbose', '--permission-mode', 'dontAsk', '--tools', 'Read,Write,Bash',
            *controls['native_command_policy'].permission_arguments(probe_policy), '--system-prompt', SYSTEM]


def _artifact(role, path, raw):
    return {'role': role, 'path': path, 'sha256': _sha(raw), 'bytes': len(raw)}


def _recipe_data(expected, selection, launch, session):
    contract, _ = _dependencies()
    _roots(expected, selection, launch)
    root = _path(launch['effect_root'])
    basis = {'domain': 'native_shared_permission_projection_v1',
             'selection_sha256': expected['selection']['sha256'],
             'recipe_sha256': expected['probe_recipe']['descriptor_sha256'], 'session_id': session}
    fixed, requests, responses = {}, {}, {}
    for role, relative in contract.ROLE_RELATIVE_PATHS.items():
        if role.endswith('_root'):
            continue
        fixed[str(root / relative)] = _encoded({**basis, 'role': role, 'synthetic': True}) + b'\n'
    for ordinal, context in enumerate(CONTEXTS, 1):
        cursor = {'ordinal': ordinal, 'kind': context,
                  'target_id': 'worker-000001' if context == 'worker' else context}
        requests[context] = _encoded({**basis, 'kind': 'synthetic_permission_request',
                                     'cursor': cursor, 'not_a_production_request': True}) + b'\n'
        responses[context] = _encoded({**basis, 'kind': 'synthetic_permission_answer', 'cursor': cursor}) + b'\n'
    return basis, fixed, requests, responses


def _view(expected, selection, launch, session, context, *, state='awaiting_response', read=False):
    contract, _ = _dependencies()
    basis, fixed, requests, responses = _recipe_data(expected, selection, launch, session)
    root = _path(launch['effect_root']); policy = projected_policy(expected, selection, str(root))
    active = state == 'awaiting_response' and context in CONTEXTS
    ordinal = CONTEXTS.index(context) + 1 if context in CONTEXTS else 1
    cursor = contract.StageCursor(ordinal=ordinal, kind=context,
                                 target_id='worker-000001' if context == 'worker' else context) if active else None
    request_path = str(root / 'requests' / ('%06d.json' % ordinal))
    request = contract.ArtifactPin(**_artifact('stage_request:' + str(ordinal), request_path,
                                               requests[context])) if active else None
    response = contract.ResponseDestination(role='stage_response:' + str(ordinal),
        path=str(root / 'responses' / ('%06d.bin' % ordinal)), media_type='application/json',
        max_bytes=min(selection['bounds']['max_response_bytes'], 2_097_152)) if active else None
    protected = [contract.RolePath(role=role, path=str(root / relative))
                 for role, relative in sorted(contract.ROLE_RELATIVE_PATHS.items())]
    protected.extend([contract.RolePath(role='stage_root', path=str(root)),
                      contract.RolePath(role='selection', path=expected['selection']['path']),
                      contract.RolePath(role='source', path=expected['source']['path'])])
    sealed = tuple(contract.ArtifactPin(**_artifact('probe_sealed', path, raw)) for path, raw in sorted(fixed.items()))
    return contract.NativeEffectView(protocol='native_shared_generation_v1',
        selection_sha256=expected['selection']['sha256'],
        execution_binding_sha256=_sha(_encoded({**basis, 'identity': 'synthetic-execution-binding'})),
        static_policy_sha256=_sha(_encoded(policy)), stage_root=str(root),
        working_directory=expected['policy']['readonly_lookups']['repository'],
        stage_command=expected['commands']['stage'], state=state, cursor=cursor, request=request,
        response=response, sealed=sealed, protected_roles=tuple(protected),
        correction_window=False, pending_advance_tool_use_id=None,
        history_sha256=_sha(_encoded({**basis, 'identity': 'synthetic-history', 'context': context, 'state': state})),
        request_read_observation_sha256=(_sha(_encoded({**basis, 'identity': 'synthetic-read',
                                                       'context': context})) if read and active else None),
        response_intent_observation_sha256=None)


def projection(expected, selection, launch, session_id):
    """Deterministic software projection; never evidence of a real stage."""
    policy = projected_policy(expected, selection, launch['effect_root'])
    states = []
    for context in CONTEXTS:
        for read in (False, True):
            states.append({'name': context + ('-read' if read else '-unread'),
                           'view': asdict(_view(expected, selection, launch, session_id, context, read=read))})
    for state in NONRESPONSE:
        states.append({'name': state, 'view': asdict(_view(expected, selection, launch, session_id,
                                                         'worker', state=state))})
    return {'kind': 'native_shared_permission_projection', 'version': VERSION,
            'effect_root': launch['effect_root'], 'session_id': session_id, 'states': states,
            'production_policy_sha256': _sha(_encoded(expected['policy'])), 'probe_policy': policy,
            'probe_policy_sha256': _sha(_encoded(policy)),
            'role_recipe_sha256': expected['probe_recipe']['descriptor_sha256']}


def probe_cases(expected, selection, launch, session_id):
    """Exact twenty-five observed cases and no caller-selected case subset."""
    _, _, requests, responses = _recipe_data(expected, selection, launch, session_id)
    root = _path(launch['effect_root'])
    def row(identity, tool, payload, context, mode):
        return {'id': identity, 'tool': tool, 'input': payload, 'context': context, 'mode': mode}
    cases = [row('source_read', 'Read', {'file_path': expected['source']['path']}, 'baseline', 'allowed')]
    for ordinal, context in enumerate(CONTEXTS, 1):
        cases += [row('stage_' + context, 'Bash', {'command': expected['commands']['stage']}, context, 'allowed'),
                  row('request_' + context + '_read', 'Read',
                      {'file_path': str(root / 'requests' / ('%06d.json' % ordinal))}, context, 'allowed'),
                  row('response_' + context + '_write', 'Write',
                      {'file_path': str(root / 'responses' / ('%06d.bin' % ordinal)),
                       'content': responses[context].decode()}, context, 'allowed')]
        if context == 'worker':
            cases += [row('future_response_write', 'Write', {'file_path': str(root / 'responses/000003.bin'),
                       'content': 'D4D_FORBIDDEN\n'}, context, 'observer_stopped'),
                      row('sealed_request_write', 'Write', {'file_path': str(root / 'requests/000002.json'),
                       'content': 'D4D_FORBIDDEN\n'}, context, 'observer_stopped')]
        elif context == 'omission':
            cases.append(row('stale_response_write', 'Write', {'file_path': str(root / 'responses/000002.bin'),
                             'content': 'D4D_FORBIDDEN\n'}, context, 'observer_stopped'))
        elif context == 'integration':
            cases.append(row('outside_response_write', 'Write', {'file_path': str(root / 'outside.bin'),
                             'content': 'D4D_FORBIDDEN\n'}, context, 'observer_stopped'))
    for role in ('draft', 'final_evidence', 'recorder'):
        cases.append(row(role, 'Bash', {'command': expected['commands'][role]}, 'terminal', 'allowed'))
    cases += [row('arbitrary_python', 'Bash', {'command': shlex.join([expected['policy']['python'], '-c',
                     'print("D4D_UNREGISTERED_PERMISSION_PROBE")'])}, 'baseline', 'native_denied'),
              row('modified_draft', 'Bash', {'command': expected['commands']['draft'] +
                     ' --d4d-unregistered-permission-argument'}, 'baseline', 'native_denied'),
              row('modified_stage', 'Bash', {'command': expected['commands']['stage'] +
                     ' --worker d4d-unregistered'}, 'worker', 'native_denied'),
              row('source_write', 'Write', {'file_path': expected['source']['path'],
                     'content': 'D4D_SOURCE_MUST_NOT_CHANGE\n'}, 'baseline', 'observer_stopped'),
              row('helper_owned_write', 'Write', {'file_path': str(root / 'journal.json'),
                     'content': 'D4D_FORBIDDEN\n'}, 'integration', 'observer_stopped')]
    policy = projected_policy(expected, selection, launch['effect_root'])
    for case in cases:
        path = case['input'].get('file_path')
        if case['tool'] == 'Read' and path in policy['readonly_lookups'].get('bounded_reads', {}):
            count = policy['readonly_lookups']['bounded_reads'][path]
            case['input'].update(offset=1, limit=min(12, count))
    return cases


def _inventory(expected, selection, launch, session, *, completed):
    _, fixed, requests, responses = _recipe_data(expected, selection, launch, session)
    root = _path(launch['effect_root']); files = dict(fixed)
    for ordinal, context in enumerate(CONTEXTS, 1):
        files[str(root / 'requests' / ('%06d.json' % ordinal))] = requests[context]
        files[str(root / 'responses' / ('%06d.bin' % ordinal))] = responses[context] if completed else None
    files[str(root / 'outside.bin')] = None
    entries = []
    for path, raw in sorted(files.items()):
        entries.append({'path': path, 'exists': raw is not None, 'text': None if raw is None else raw.decode(),
                        'sha256': None if raw is None else _sha(raw), 'bytes': 0 if raw is None else len(raw)})
    return {'source': deepcopy(expected['source']), 'files': entries}


def _file_classification(policy, case):
    """Replay the pinned FileAccess admission over captured canonical paths.

    This performs no filesystem resolution. Actual capture checks regular files
    and aliases before producing the recorded inventory; this is not a sandbox.
    """
    lookup = policy['readonly_lookups']; payload = case['input']; target = _path(payload['file_path'])
    if case['tool'] == 'Write' and lookup.get('write_paths') is not None:
        cap = lookup['write_paths'].get(str(target))
        if type(cap) is not int or set(payload) != {'file_path', 'content'} or type(payload['content']) is not str:
            return 'not_prescribed', 'outside exact registered native part Writes'
        if not 0 < len(payload['content'].encode()) <= cap:
            return 'not_prescribed', 'native part Write exceeds its registered byte bounds'
    if case['tool'] == 'Read' and str(target) in lookup.get('bounded_reads', {}):
        count = lookup['bounded_reads'][str(target)]
        if (set(payload) != {'file_path', 'offset', 'limit'} or type(payload['offset']) is not int or
                type(payload['limit']) is not int or payload['offset'] != 1 or payload['limit'] != min(12, count)):
            return 'not_prescribed', 'bounded context Read requires one exact registered range'
    if case['tool'] == 'Read' and str(target) in lookup['inputs']:
        return 'prescribed', 'a registered input the instruction reads'
    if any(_path(folder) in target.parents for folder in lookup['output_directories']):
        if str(target) in lookup['inputs']:
            return 'not_prescribed', 'a registered input cannot be overwritten'
        return 'prescribed', 'a file inside the registered output directories'
    return 'not_prescribed', 'a path outside the registered inputs and outputs'


def _classification(expected, selection, launch, session, case, controls):
    _, effects = _dependencies()
    context = case['context'] if case['context'] in CONTEXTS else 'worker'
    view = _view(expected, selection, launch, session, context, read=case['tool'] == 'Write')
    policy = projected_policy(expected, selection, launch['effect_root'])
    governed = command_policy.stage_overlay_governs(view, tool_name=case['tool'],
        tool_input=case['input'], policy=policy)
    _need(type(governed) is bool, 'effect routing is not a strict boolean')
    effect = None
    if governed:
        effect = effects.classify_effect(view, tool_name=case['tool'], tool_input=case['input'])
        _need(type(effect) is tuple and len(effect) == 2 and effect[0] in ('prescribed', 'not_prescribed')
              and type(effect[1]) is str and effect[1].strip(), 'invalid fixed classifier result')
    if case['mode'] == 'observer_stopped':
        _need(governed and effect[0] == 'not_prescribed', 'file negative does not reach observer stop')
        return effect, view
    if effect is not None:
        _need(effect[0] == ('prescribed' if case['mode'] == 'allowed' else 'not_prescribed'), 'effect classification differs')
    if case['tool'] == 'Bash':
        result = effect if governed else command_policy.classify_bash(case['input']['command'], policy['python'], set(), policy, controls)
    else:
        result = _file_classification(policy, case)
    _need(result[0] == ('prescribed' if case['mode'] == 'allowed' else 'not_prescribed'), 'required native classification differs')
    return result, view


def _rows(raw, label):
    _need(raw.endswith(b'\n'), label + ' lacks a final physical newline')
    lines = raw.split(b'\n')[:-1]
    _need(0 < len(lines) <= MAX_ROWS and all(line.strip() for line in lines), label + ' row bounds differ')
    rows = [_json(line) for line in lines]
    _need(all(type(row) is dict for row in rows), label + ' contains a non-object')
    return rows


def _members(value):
    _need(type(value) is dict and len(value) <= MAX_MEMBERS, 'invalid member map')
    names = {'policy.json', 'selection.json', 'cases.json', 'source.before', 'source.after', 'version.txt'}
    sources = recipe_sources()
    _need(len(sources) <= MAX_RECIPE, 'fixed recipe exceeds its member bound')
    names.update(sources)
    for trace in TRACES:
        for file in ('launch.json', 'config.json', 'projection.json', 'neutral.before.json', 'neutral.after.json',
                     'transcript.jsonl', 'control.jsonl', 'outcome.json'):
            names.add('traces/' + trace + '/' + file)
        if trace != 'settled':
            names.update('traces/' + trace + '/' + file for file in ('effect-stop.json', 'parent-stop.json'))
    _object(value, names, 'raw member roster')
    raw, total = {}, 0
    for name, row in value.items():
        _object(row, {'text', 'sha256', 'bytes'}, 'raw member')
        _need(type(row['text']) is str, 'member content is not UTF-8 text')
        _need(type(row['bytes']) is int and 0 <= row['bytes'] <= MAX_MEMBER, 'member size is not bounded')
        _hash(row['sha256']); content = row['text'].encode('utf-8')
        _need(row['bytes'] == len(content) and row['sha256'] == _sha(content), 'member raw identity differs')
        total += len(content)
        _need(total <= MAX_RAW, 'decoded aggregate exceeds bound')
        raw[name] = content
    for name, text in sources.items():
        _need(raw[name] == text.encode(), 'fixed recipe source differs: ' + name)
    return raw


def _native_scope(event, session, model, role=None):
    _need(event.get('session_id') == session and event.get('parent_tool_use_id') is None,
          'frame is outside the initialized parent session')
    containers = [event]
    if 'message' in event:
        _need(type(event['message']) is dict, 'message is not an object')
        containers.append(event['message'])
    for value in containers:
        if 'model' in value:
            _need(value['model'] == model, 'frame contradicts selected model')
        if role is not None and 'role' in value:
            _need(value['role'] == role, 'frame contradicts event role')


def _settled_text(events, offset, session, model):
    while offset < len(events):
        event = events[offset]
        if event.get('type') != 'assistant':
            break
        content = (event.get('message') or {}).get('content')
        if not (type(content) is list and content and all(type(x) is dict and set(x) == {'type','text'}
                and x['type'] == 'text' and type(x['text']) is str for x in content)):
            break
        _native_scope(event, session, model, 'assistant')
        offset += 1
    return offset


def _read_content(case, expected, selection, launch, session, source_raw, *, observed_lines=None):
    if case['id'] == 'source_read':
        raw = source_raw
    else:
        raw = _recipe_data(expected, selection, launch, session)[2][case['context']]
    text = raw.decode(); lines = text.split('\n')
    if 'limit' in case['input']:
        count = projected_policy(expected, selection, launch['effect_root'])['readonly_lookups']['bounded_reads'][case['input']['file_path']]
        _need(count == len(lines), 'bounded Read count contradicts captured raw file')
        if case['id'] != 'source_read':
            _need(case['input']['limit'] == len(lines), 'current request cannot be completely read in this range')
        selected = lines[:case['input']['limit']]
        text = '\n'.join(selected)
    else:
        selected = lines
        if case['id'] == 'source_read' and observed_lines is not None:
            _positive(observed_lines, 'observed source Read lines', len(lines))
            selected = lines[:observed_lines]
            text = '\n'.join(selected)
    return text, '\n'.join(str(i+1) + '\t' + line for i,line in enumerate(selected)), len(selected), len(lines)


def _tool_result(event, case, expected, selection, launch, session, source_raw):
    content = event.get('message', {}).get('content')
    _need(type(content) is list and len(content) == 1 and type(content[0]) is dict, 'one unique tool result required')
    item = content[0]
    _need(item.get('type') == 'tool_result' and item.get('tool_use_id') == case['id'], 'result has a foreign tool identity')
    allowed = case['mode'] == 'allowed'
    _need(item.get('is_error', False) is (not allowed), 'result contradicts admission')
    metadata = event.get('tool_use_result', {})
    _need(type(metadata) is dict and not any(metadata.get(k) for k in
          ('interrupted', 'backgroundTaskId', 'background_task_id', 'persistedOutputPath')), 'pending/unsupported result')
    if 'interrupted' in metadata:
        _need(metadata['interrupted'] is False, 'interrupted flag is not exact false')
    if 'error' in metadata:
        _need(metadata['error'] is None, 'tool metadata reports an explicit error')
    exits = [metadata[k] for k in ('exitCode', 'exit_code') if k in metadata]
    _need(all(type(x) is int for x in exits) and len(set(exits)) <= 1, 'exit aliases differ or have wrong types')
    text = _text(item.get('content'), 'tool result content')
    if not allowed:
        _need(not exits or exits[0] != 0, 'denied command reports successful exit')
        _need(text.startswith('Outside the registered tool policy') and 'd4d_shared_permission_stub' not in text,
              'unrelated failure is not a native permission denial')
        if 'stdout' in metadata:
            _need(metadata['stdout'] == text, 'denial stdout differs')
        return
    _need(not exits or exits[0] == 0, 'allowed tool reports unsuccessful exit')
    if case['tool'] == 'Bash':
        role = 'stage' if case['id'].startswith('stage_') else case['id']
        wanted = {'d4d_shared_permission_stub': role, 'argv': shlex.split(case['input']['command'])[3:]}
        _need(_same(_json(text.encode()), wanted), 'helper marker or arguments differ')
        _need(type(metadata.get('stdout')) is str and _same(_json(metadata['stdout'].encode()), wanted),
              'helper stdout differs in value or type')
        if 'stderr' in metadata:
            _need(metadata['stderr'] == '', 'helper stderr contradicts fixed recipe')
    elif case['tool'] == 'Read':
        file = metadata.get('file')
        _need(type(file) is dict and metadata.get('type') == 'text', 'Read lacks native file metadata')
        raw_text, rendered, count, total = _read_content(case, expected, selection, launch, session, source_raw,
            observed_lines=file.get('numLines') if case['id'] == 'source_read' else None)
        wanted = {'filePath': case['input']['file_path'], 'content': raw_text,
                  'numLines': count, 'startLine': 1, 'totalLines': total}
        _need(_same(file, wanted) and text == rendered, 'Read does not contain exact complete captured range')
    else:
        _need(metadata.get('type') == 'create' and metadata.get('filePath') == case['input']['file_path']
              and metadata.get('content') == case['input']['content'], 'Write metadata differs from exact current response')
        _need(metadata.get('originalFile') is None and metadata.get('userModified', False) is False,
              'Write was not a new unchanged response')
        _need(metadata.get('structuredPatch', []) == [], 'Write patch contradicts creation')
        _need(text.startswith('File created successfully at: ' + case['input']['file_path']), 'Write success names another path')


def _launch(expected, selection, trace, launch, raw, policy):
    _object(launch, {'cwd', 'argv', 'environment', 'config_root', 'stub_root', 'effect_root', 'evidence_root',
                     'provider_url', 'provider_source_sha256', 'exit_code', 'shutdown', 'executable'}, 'launch')
    _roots(expected, selection, launch)
    _need(launch['cwd'] == expected['policy']['readonly_lookups']['repository'], 'callback cwd differs')
    _need(_same(launch['argv'], probe_argv(expected, policy)), 'native argv differs')
    _need(_same(launch['executable'], expected['runtime']['executable']), 'executable identity differs')
    _need(raw['version.txt'] == (expected['runtime']['executable']['version'] + '\n').encode(), 'version stdout differs')
    prefix = 'traces/' + trace + '/'
    _need(_same(_json(raw[prefix + 'config.json']), {}), 'config is not explicitly empty and isolated')
    url = urlsplit(launch['provider_url'])
    _need(url.scheme == 'http' and url.hostname == '127.0.0.1' and url.port is not None and
          not url.username and not url.password and not url.query and not url.fragment and url.path in ('','/'),
          'provider is not the declared loopback scripted endpoint')
    wanted_env = {**expected['permission_environment'], 'CLAUDE_CONFIG_DIR': launch['config_root'],
                  'PYTHONPATH': launch['stub_root'], 'ANTHROPIC_BASE_URL': launch['provider_url'],
                  'ANTHROPIC_API_KEY': 'd4d-local-permission-probe-token'}
    _need(_same(launch['environment'], wanted_env), 'unregistered environment substitution')
    _need(launch['provider_source_sha256'] == _sha(raw['recipe/provider.py']), 'provider source differs')
    _need(type(launch['exit_code']) is int, 'exit status is not an observed integer')
    _need(_same(launch['shutdown'], {'control_initialized': True, 'control_shutdown_complete': True,
                                    'unfinished_control_workers': 0, 'child_reaped': True}), 'incomplete bounded shutdown')


def effect_stop(expected, policy, case, view, call, callback, classification):
    """Recompute the selected observer's exact stop artifact, never a verdict."""
    return {'kind': 'native_shared_effect_stop', 'version': 1, 'reason_code': 'prohibited_file_effect',
            'selection_sha256': expected['selection']['sha256'], 'policy_sha256': _sha(_encoded(policy)),
            'view_sha256': _sha(_encoded(asdict(view))), 'tool_use_id': case['id'],
            'callback_id': callback['request_id'], 'tool_name': case['tool'],
            'tool_input_sha256': _sha(_encoded(case['input'])), 'classification': classification[0],
            'basis': classification[1], 'call_event_sha256': _sha(_encoded(call)),
            'callback_event_sha256': _sha(_encoded(callback))}


def _trace(expected, selection, trace, raw, controls):
    prefix = 'traces/' + trace + '/'
    launch = _json(raw[prefix + 'launch.json'])
    policy = projected_policy(expected, selection, launch['effect_root'])
    _launch(expected, selection, trace, launch, raw, policy)
    events = _rows(raw[prefix + 'transcript.jsonl'], 'transcript')
    records = _rows(raw[prefix + 'control.jsonl'], 'control')
    clean = [{k:v for k,v in row.items() if k != 'at'} for row in records]
    native = controls['native_control']; model = expected['runtime']['model']
    ack = {'type': 'control_response', 'response': {'subtype': 'success', 'request_id': native.INIT_ID}}
    _need(_same(clean[0], {'kind': 'initialize_sent', 'policy_sha256': native.digest(policy),
                          'frame': native.initialize_frame(policy['pretool_control'])}), 'initialization sent differs')
    _need(_same(events[0], ack) and _same(clean[1], {'kind': 'initialize_ack', 'frame': ack}), 'initialization ack differs')
    init = events[1]
    _need(init.get('type') == 'system' and init.get('subtype') == 'init' and init.get('model') == model
          and init.get('claude_code_version') == expected['runtime']['executable']['init_version']
          and init.get('cwd') == launch['cwd'] and init.get('tools') == ['Read','Write','Bash']
          and init.get('apiKeySource') == 'ANTHROPIC_API_KEY'
          and init.get('permissionMode', 'dontAsk') == 'dontAsk', 'native init differs')
    session = init.get('session_id')
    _need(type(session) is str and re.fullmatch(r'[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}', session),
          'invalid parent session')
    _native_scope(init, session, model)
    projected = projection(expected, selection, launch, session)
    _need(_same(_json(raw[prefix + 'projection.json']), projected), 'projection is not independently derived')
    _need(_same(_json(raw[prefix + 'neutral.before.json']), _inventory(expected, selection, launch, session, completed=False)),
          'neutral before inventory differs')
    _need(_same(_json(raw[prefix + 'neutral.after.json']), _inventory(expected, selection, launch, session, completed=trace == 'settled')),
          'neutral after inventory shows missing or forbidden effects')
    all_cases = probe_cases(expected, selection, launch, session)
    cases = [c for c in all_cases if c['mode'] != 'observer_stopped'] if trace == 'settled' else [
        c for c in all_cases if c['id'] == trace[5:]]
    _need(len(clean) == (len(cases) + 2 if trace == 'settled' else 2), 'control has missing/extra grants')
    offset, request_ids, outcomes = 2, set(), []
    for number, case in enumerate(cases):
        offset = _settled_text(events, offset, session, model)
        call, callback = events[offset:offset+2]; offset += 2
        _need(call.get('type') == 'assistant', 'tool call is out of order')
        _native_scope(call, session, model, 'assistant')
        wanted_block = {'type': 'tool_use', 'id': case['id'], 'name': case['tool'], 'input': case['input']}
        _need(_same(call.get('message', {}).get('content'), [wanted_block]), 'call differs from required case')
        request_id = callback.get('request_id')
        _need(type(request_id) is str and request_id and request_id not in request_ids and request_id != native.INIT_ID,
              'duplicate or missing callback identity')
        request_ids.add(request_id)
        wanted = {'type': 'control_request', 'request_id': request_id, 'request': {'subtype': 'hook_callback',
            'callback_id': policy['pretool_control']['callback_id'], 'input': {'hook_event_name': 'PreToolUse',
            'tool_name': case['tool'], 'tool_use_id': case['id'], 'cwd': launch['cwd'], 'tool_input': case['input']}}}
        if 'effort' in (callback.get('request') or {}).get('input', {}):
            wanted['request']['input']['effort'] = expected['runtime']['effort']
        _need(_same(callback, wanted), 'callback differs from observed call/selected authority')
        classification, view = _classification(expected, selection, launch, session, case, controls)
        stop_sha, result_sha = None, None
        if case['mode'] == 'observer_stopped':
            _need(offset == len(events), 'stopped file case contains a result or continuation')
            stop = effect_stop(expected, policy, case, view, call, callback, classification)
            _need(_same(_json(raw[prefix + 'effect-stop.json']), stop), 'durable observer-stop cause differs')
            stop_sha = _sha(raw[prefix + 'effect-stop.json'])
            parent = {'kind': 'native_shared_permission_parent_stop', 'version': 1, 'outcome': 'observer_stopped',
                      'effect_stop_sha256': stop_sha, 'reason_code': 'prohibited_file_effect', 'error_type': 'BudgetStop'}
            _need(_same(_json(raw[prefix + 'parent-stop.json']), parent), 'parent stop lacks exact durable cause')
        else:
            result = events[offset]; offset += 1
            decision = {'kind': 'decision', 'request': callback, 'classification': classification[0], 'basis': classification[1],
                'response': {'type': 'control_response', 'response': {'subtype': 'success', 'request_id': request_id,
                    'response': native.hook_output(*classification)}}}
            _need(_same(clean[number+2], decision), 'parent decision contradicts recomputed classification')
            _need(result.get('type') == 'user', 'missing settled result')
            _native_scope(result, session, model, 'user')
            _tool_result(result, case, expected, selection, launch, session, raw['source.before'])
            result_sha = _sha(_encoded(result))
        outcomes.append({'id': case['id'], 'trace_id': trace, 'state': view.state, 'tool': case['tool'],
            'input_sha256': _sha(_encoded(case['input'])), 'classification': classification[0], 'basis': classification[1],
            'observed_mode': case['mode'], 'call_id': case['id'], 'callback_id': request_id,
            'result_sha256': result_sha, 'stop_sha256': stop_sha})
    outcome = _json(raw[prefix + 'outcome.json'])
    if trace == 'settled':
        offset = _settled_text(events, offset, session, model)
        _need(len(events) == offset + 1, 'extra/pending/post-terminal evidence')
        terminal = events[offset]; _native_scope(terminal, session, model)
        _need(terminal.get('type') == 'result' and terminal.get('is_error') is False and terminal.get('error') is None
              and terminal.get('subtype', 'success') == 'success' and terminal.get('terminal_reason') == 'completed'
              and terminal.get('stop_reason') == 'end_turn', 'terminal contradicts successful completion')
        denied = terminal.get('permission_denials')
        denied_cases = {c['id']:c for c in cases if c['mode'] == 'native_denied'}
        _need(type(denied) is list and len(denied) == 3 and all(type(x) is dict for x in denied)
              and sorted(x.get('tool_use_id','') for x in denied) == sorted(denied_cases), 'denial inventory differs')
        for row in denied:
            for key,wanted_value in (('tool_name',denied_cases[row['tool_use_id']]['tool']),
                                     ('tool_input',denied_cases[row['tool_use_id']]['input'])):
                if key in row:
                    _need(_same(row[key], wanted_value), 'terminal denial contradicts its exact case')
        _need(launch['exit_code'] == 0, 'successful probe process exit differs')
        wanted_outcome = {'kind': 'native_shared_permission_outcome', 'version': 1, 'mode': 'settled',
                          'session_id': session, 'terminal_sha256': _sha(_encoded(terminal)), 'parent_stop_sha256': None}
    else:
        _need(launch['exit_code'] != 0, 'stopped trace advertises successful process exit')
        wanted_outcome = {'kind': 'native_shared_permission_outcome', 'version': 1, 'mode': 'observer_stopped',
                          'session_id': session, 'terminal_sha256': None,
                          'parent_stop_sha256': _sha(raw[prefix + 'parent-stop.json'])}
    _need(_same(outcome, wanted_outcome), 'trace outcome differs from actual raw lifecycle')
    return {'id': trace, 'mode': wanted_outcome['mode'], 'executable': deepcopy(launch['executable']),
        'cwd': launch['cwd'], 'argv_sha256': _sha(_encoded(launch['argv'])),
        'environment_sha256': _sha(_encoded(launch['environment'])), 'session_id': session,
        'shutdown': deepcopy(launch['shutdown']),
        'projection': {'effect_root': launch['effect_root'], 'states': [
            {'name': state['name'], 'view_sha256': _sha(_encoded(state['view']))} for state in projected['states']]},
        'outcome_sha256': _sha(raw[prefix + 'outcome.json'])}, outcomes, launch


def _derived_controls(expected, selection, launch, session):
    _, effects = _dependencies()
    checks = []
    for state in NONRESPONSE:
        view = _view(expected, selection, launch, session, 'worker', state=state)
        command = {'command': expected['commands']['stage']}
        _need(effects.governs_stage_effect(view, tool_name='Bash', tool_input=command) is True,
              'fixed stage helper is outside the selected effect router')
        helper = effects.classify_effect(view, tool_name='Bash', tool_input=command)
        wanted = 'not_prescribed' if state == 'failed' else 'prescribed'
        _need(helper[0] == wanted and view.response is None, 'nonresponse helper rule differs')
        paths = []
        for ordinal in range(1, 5):
            path = str(_path(launch['effect_root']) / 'responses' / ('%06d.bin' % ordinal))
            data = {'file_path': path, 'content': 'not an admitted response\n'}
            _need(effects.governs_stage_effect(view, tool_name='Write', tool_input=data) is True and
                  effects.classify_effect(view, tool_name='Write', tool_input=data)[0] == 'not_prescribed',
                  'nonresponse state admits a model Write')
            paths.append(path)
        checks.append({'state': state, 'stage_helper_classification': helper[0],
                       'response_is_none': True, 'denied_response_paths': paths})
    for context in CONTEXTS:
        view = _view(expected, selection, launch, session, context, read=True)
        for ordinal in range(1, 6):
            path = str(_path(launch['effect_root']) / 'responses' / ('%06d.bin' % ordinal))
            if path == view.response.path:
                continue
            data = {'file_path': path, 'content': 'wrong cursor\n'}
            _need(effects.governs_stage_effect(view, tool_name='Write', tool_input=data) is True and
                  effects.classify_effect(view, tool_name='Write', tool_input=data)[0] == 'not_prescribed',
                  'wrong-cursor Write escaped the fixed classifier')
    return checks


def verify_saved_probe(raw_manifest: bytes, *, expected: dict) -> dict:
    """Recompute all recorded cases; malformed/unsupported evidence refuses.

    There is no mock flag or execution entrypoint. Fixed local source files are
    checked, but no path supplied by the manifest is opened. Authenticity of a
    saved observation and actual filesystem metadata remain separate reviews.
    """
    try:
        return _verify(raw_manifest, expected)
    except (KeyError, TypeError, IndexError, AttributeError, UnicodeError, OverflowError,
            RecursionError, OSError) as exc:
        raise ValueError('native shared permission evidence is malformed, unavailable or incomplete') from exc


def _verify(raw_manifest, expected):
    value = _object(_json(raw_manifest, MAX_WIRE), {'kind','version','origin','binding','members'}, 'manifest')
    _need(value['kind'] == KIND and type(value['version']) is int and value['version'] == VERSION
          and value['origin'] == ORIGIN, 'unknown native shared observation protocol/origin')
    _need(_same(value['binding'], expected), 'manifest binding differs from supplied authority')
    # The wrapper has two supported canonical UTF-8 encodings. Raw member text
    # itself is never normalized. This makes the metadata wire bound exact,
    # rather than allowing arbitrary whitespace to evade that separate bound.
    canonical_forms = [json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=ascii_only,
                                  allow_nan=False).encode('utf-8') for ascii_only in (False, True)]
    _need(raw_manifest in canonical_forms, 'manifest wrapper must use canonical JSON encoding')
    ascii_only = raw_manifest == canonical_forms[1]
    raw = _members(value['members'])
    content_wire = sum(len(json.dumps(row['text'], ensure_ascii=ascii_only).encode()) - 2
                       for row in value['members'].values())
    _need(len(raw_manifest) - content_wire <= MAX_METADATA, 'metadata wire exceeds bound')
    contract, _ = _dependencies()
    selection = contract.parse_selection(raw['selection.json'])
    _pin(expected['selection'], raw['selection.json']); _pin(expected['source'], raw['source.before'])
    controls = composition.load_controls()
    _authority(expected, selection, controls)
    _need(_same(_json(raw['policy.json']), expected['policy']), 'common production policy differs')
    _need(raw['source.before'] == raw['source.after'], 'selected source changed')
    traces, cases, all_roots, sessions = [], [], [], set()
    for name in TRACES:
        summary, outcomes, launch = _trace(expected, selection, name, raw, controls)
        _need(summary['session_id'] not in sessions, 'probe traces reuse one session')
        sessions.add(summary['session_id'])
        roots = [_path(launch[key]) for key in ('config_root','stub_root','effect_root','evidence_root')]
        for root in roots:
            _need(all(root != previous and root not in previous.parents and previous not in root.parents
                      for previous in all_roots), 'probe traces reuse or overlap isolation roots')
        all_roots.extend(roots)
        if name == 'settled':
            roster = [{k:v for k,v in c.items() if k != 'input'}
                      for c in probe_cases(expected, selection, launch, summary['session_id'])]
            _need(_same(_json(raw['cases.json']), roster), 'closed case roster differs')
            derived = _derived_controls(expected, selection, launch, summary['session_id'])
        traces.append(summary); cases.extend(outcomes)
    _need(len(cases) == 25 and len({case['id'] for case in cases}) == 25, 'not every required case was checked once')
    # These two digests bind ordered per-trace raw-member hashes; the complete
    # member identities remain individually disclosed in ``members`` below.
    preservation = {'source_sha256': expected['source']['sha256'],
        'changed_response_roles': ['stage_response:' + str(i) for i in range(1,5)]}
    for moment in ('before','after'):
        rows = [{'trace_id': name, 'sha256': _sha(raw['traces/' + name + '/neutral.' + moment + '.json'])}
                for name in TRACES]
        preservation['neutral_' + moment + '_sha256'] = _sha(_encoded(rows))
    return {'instrument': KIND, 'version': VERSION, 'checked': True, 'passed': True,
        'basis': 'recomputed recorded native permission cases; production helpers stubbed',
        'manifest': {'sha256': _sha(raw_manifest), 'bytes': len(raw_manifest)}, 'binding_sha256': _sha(_encoded(expected)),
        'source_closure': {'production_sha256': _sha(_encoded(expected['production_sources'])),
            'controller_sha256': _sha(_encoded(expected['controller_sources'])),
            'probe_recipe_sha256': _sha(_encoded(expected['probe_recipe']))},
        'members': [{'name': name, 'sha256': _sha(content), 'bytes': len(content)} for name,content in sorted(raw.items())],
        'traces': traces, 'cases': cases, 'derived_nonresponse_checks': derived,
        'preservation': preservation,
        'unassessed': ['observation authenticity','production helper execution','production stage reachability',
                      'complete production request-read chronology','model attention','current authentication',
                      'provider billing','generation acceptance','owner launch authorization']}
