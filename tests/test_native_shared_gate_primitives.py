"""U3-D r8: parity against unedited gate sources, never native admission.

Synthetic captured values exercise the same neutral/original pure functions;
the originals are comparison oracles only and remain outside the consumer graph.
"""
from copy import deepcopy
import hashlib
from pathlib import Path
from types import SimpleNamespace

import pytest

from data_sheets_schema import native_attribution_registration as historical_json
from data_sheets_schema import native_execution_gates as historical
from data_sheets_schema import native_execution_authority_v2 as authority
from data_sheets_schema import native_shared_gate_primitives as neutral


def outcome(function, *args, **kwargs):
    try:
        return ('returned', function(*args, **kwargs))
    except (ValueError, TypeError, KeyError) as exc:
        return (type(exc).__name__, str(exc))


def test_neutral_gate_primitive_is_accepted_by_the_unchanged_guard():
    path = Path(neutral.__file__)
    raw = path.read_bytes()
    relative = 'src/data_sheets_schema/native_shared_gate_primitives.py'
    digest = hashlib.sha256(raw).hexdigest()
    checked = authority.refuse_legacy_consumer_imports(raw, name=neutral.__name__,
        package_sources={relative: digest})
    assert checked == {neutral.__name__: digest}
    assert neutral.GATES == historical.GATES
    assert neutral.IOKIT_ASSERTIONS == historical.IOKIT_ASSERTIONS
    assert neutral.RUNTIME_OBSERVATION_BASIS == historical.RUNTIME_OBSERVATION_BASIS
    assert neutral.CLEANUP_BASIS == historical.CLEANUP_BASIS
    assert neutral.DRAFT_MODULE == historical_json.policy.MODULE


@pytest.mark.parametrize('value', [None, {'z': 'Ωé', 'a': ['é', False, 0]}, float('nan')])
def test_neutral_serialization_preserves_historical_bytes_and_refusals(value):
    assert outcome(neutral._encoded, value) == outcome(historical_json._encoded, value)


@pytest.mark.parametrize('raw', ['{"a":1,"a":2}', '{"a":NaN}', '{"x":"Ω"}', '[]', '{'])
def test_neutral_json_preserves_duplicate_and_nonfinite_refusals(raw):
    assert outcome(neutral._json, raw) == outcome(historical_json._json, raw)


@pytest.mark.parametrize('command', ['synthetic draft', 'synthetic final', 'echo ordinary',
    'python -m data_sheets_schema.source_attribution_preflight --foreign',
    'python -m data_sheets_schema.evidence_assertions --foreign',
    'python -m data_sheets_schema.source_review --foreign', "echo '", None])
def test_explicit_command_map_preserves_exact_matching_and_refusals(command):
    expected = {'synthetic draft': 'draft', 'synthetic final': 'final_evidence'}
    spec = object()
    assert outcome(neutral.command_kind, command, spec, expected=expected) == outcome(
        historical_json.command_kind, command, spec, expected=expected)


def test_neutral_command_classifier_never_constructs_an_implicit_policy():
    with pytest.raises(TypeError):
        neutral.command_kind('synthetic draft', object())
    with pytest.raises(ValueError, match='map must be explicit'):
        neutral.command_kind('synthetic draft', object(), expected=None)


def tool_case():
    content = '{"checked":true}'
    events = [
        {'type': 'system', 'subtype': 'init'},
        {'type': 'assistant', 'message': {'content': [
            {'type': 'tool_use', 'id': 'one', 'name': 'Bash',
             'input': {'command': 'synthetic draft'}}]}},
        {'type': 'user', 'message': {'content': [
            {'type': 'tool_result', 'tool_use_id': 'one', 'is_error': False,
             'content': content}]}, 'tool_use_result': {'exitCode': 0, 'stdout': content}},
        {'type': 'result'},
    ]
    return {'events': events, 'state': SimpleNamespace(spec=object(),
        commands={'synthetic draft': 'draft'})}


@pytest.mark.parametrize('change', ['none', 'usable_correction', 'duplicate_call',
    'early_terminal', 'unknown_result', 'bool_exit', 'contradictory_exit',
    'stdout_disagrees', 'duplicate_json', 'interrupted', 'missing_terminal'])
def test_typed_tool_history_preserves_success_and_fail_closed_semantics(change):
    prepared = tool_case()
    events = prepared['events']
    call = events[1]['message']['content'][0]
    result = events[2]['message']['content'][0]
    metadata = events[2]['tool_use_result']
    if change == 'usable_correction':
        result['is_error'] = True
        metadata['exitCode'] = 1
    elif change == 'duplicate_call':
        events[1]['message']['content'].append(deepcopy(call))
    elif change == 'early_terminal':
        events.insert(2, {'type': 'result'})
    elif change == 'unknown_result':
        result['tool_use_id'] = 'other'
    elif change == 'bool_exit':
        metadata['exitCode'] = False
    elif change == 'contradictory_exit':
        metadata['exit_code'] = 1
    elif change == 'stdout_disagrees':
        metadata['stdout'] = '{}'
    elif change == 'duplicate_json':
        result['content'] = '{"checked":true,"checked":false}'
    elif change == 'interrupted':
        metadata['interrupted'] = True
    elif change == 'missing_terminal':
        events.pop()
    actual = outcome(neutral.tool_history, deepcopy(prepared))
    assert actual == outcome(historical.tool_history, deepcopy(prepared))
    if change in ('none', 'usable_correction'):
        assert actual[0] == 'returned' and actual[1]['passed'] is True
    else:
        assert actual[0] == 'ValueError'


@pytest.mark.parametrize('change', ['none', 'false', 'whitespace', 'foreign', 'untyped', 'missing'])
def test_captured_runtime_observation_parity(change):
    selected = {'binary': {'path': '/synthetic', 'sha256': 'a' * 64, 'bytes': 12},
        'version': 'synthetic', 'auth': {'loggedIn': True}, 'environment_sha256': 'b' * 64}
    admitted = {'checked': True, 'passed': True, **deepcopy(selected)}
    if change == 'false': admitted['passed'] = False
    if change == 'untyped': admitted['passed'] = 1
    raw = historical_json._encoded(admitted)
    if change == 'whitespace': raw += b'\n'
    if change == 'foreign': selected['version'] = 'foreign'
    if change == 'missing': del selected['auth']
    actual = outcome(neutral.runtime_observation_result, raw, admitted, selected)
    assert actual == outcome(historical.runtime_observation_result, raw, admitted, selected)
    if actual[0] == 'returned':
        assert actual[1]['passed'] is (change == 'none')
    else:
        assert change in ('untyped', 'missing')


def cleanup_case(policy):
    registered = {'policy': policy}
    if policy == 'not_applicable':
        return registered, {'passed': True, 'policy': registered,
            'state': 'explicitly_not_applicable', 'releases': []}
    assertions = [{'type': name, 'id': number + 1}
        for number, name in enumerate(neutral.IOKIT_ASSERTIONS)]
    return registered, {'passed': True, 'policy': registered, 'state': 'released',
        'acquisition': {'policy': policy, 'pid': 123, 'acquired_at': 'synthetic start',
            'status': 'acquired', 'assertions': assertions, 'limitations': [], 'cleanup_receipt': 'synthetic'},
        'released_at': 'synthetic end', 'releases': [dict(row, return_code=0)
            for row in reversed(assertions)]}


@pytest.mark.parametrize('policy', ['not_applicable', 'macos_iokit_ims_v1'])
@pytest.mark.parametrize('change', ['none', 'false', 'whitespace', 'foreign_policy', 'bad_state', 'bool_passed'])
def test_cleanup_gate_preserves_policy_and_captured_byte_obligations(policy, change):
    registered, observed = cleanup_case(policy)
    if change == 'false': observed['passed'] = False
    if change == 'bad_state': observed['state'] = 'unknown'
    if change == 'bool_passed': observed['passed'] = 1
    raw = historical_json._encoded(observed)
    if change == 'whitespace': raw += b'\n'
    if change == 'foreign_policy': registered = {'policy': 'foreign'}
    actual = outcome(neutral.cleanup_result, raw, observed, registered)
    assert actual == outcome(historical.cleanup_result, raw, observed, registered)
    if actual[0] == 'returned':
        assert actual[1]['passed'] is (change == 'none')
    else:
        assert change == 'bool_passed'


@pytest.mark.parametrize('change', ['order', 'bool_id', 'duplicate_id', 'release_code', 'release_order'])
def test_iokit_release_accounting_parity(change):
    registered, observed = cleanup_case('macos_iokit_ims_v1')
    if change == 'order': observed['acquisition']['assertions'].reverse()
    if change == 'bool_id': observed['acquisition']['assertions'][0]['id'] = True
    if change == 'duplicate_id': observed['acquisition']['assertions'][1]['id'] = 1
    if change == 'release_code': observed['releases'][0]['return_code'] = 1
    if change == 'release_order': observed['releases'].reverse()
    assert neutral._released_assertions(observed, registered) is False
    assert neutral._released_assertions(observed, registered) == historical._released_assertions(observed, registered)
