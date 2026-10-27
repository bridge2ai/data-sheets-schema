"""Pure per-call path validation; no native observations or filesystem effects."""
from copy import deepcopy
from pathlib import PurePosixPath

import pytest

from data_sheets_schema import native_shared_permissions as p


def _parent_roots(expected, selection, launch):
    # Literal 7a2e8b5 _roots body, changing only function name and p. namespace.
    roots = [p._path(launch[name]) for name in ('config_root', 'stub_root', 'effect_root', 'evidence_root')]
    protected = [expected['policy']['readonly_lookups']['repository'], expected['selection']['path'],
                 expected['source']['path'], selection['stage_root'],
                 *expected['policy']['readonly_lookups']['inputs'],
                 *expected['policy']['readonly_lookups']['output_directories']]
    protected += [value for key,value in expected['permission_environment'].items()
                  if key in ('CLAUDE_CONFIG_DIR', 'D4D_LAUNCH_INSTRUCTION') and value.startswith('/')]
    for number, root in enumerate(roots):
        for other in roots[number+1:] + [p._path(x) for x in protected]:
            p._need(root != other and root not in other.parents and other not in root.parents, 'neutral roots overlap authority')
    return roots


def _case():
    expected = {
        'policy': {'readonly_lookups': {
            'repository': '/authority/repository',
            'inputs': ['/authority/bundle', '/authority/chunks'],
            'output_directories': ['/authority/output'],
        }},
        'selection': {'path': '/authority/selection.json'},
        'source': {'path': '/authority/source'},
        'permission_environment': {
            'CLAUDE_CONFIG_DIR': '/authority/config',
            'D4D_LAUNCH_INSTRUCTION': '/authority/instruction',
            'IGNORED': '/neutral/config',
        },
    }
    selection = {'stage_root': '/authority/stage'}
    launch = {name: '/neutral/' + name for name in (
        'config_root', 'stub_root', 'effect_root', 'evidence_root')}
    return expected, selection, launch


def _outcome(fn, inputs):
    try:
        return ('returned', fn(*inputs))
    except Exception as error:
        return ('raised', type(error), str(error))


def _assert_parity(inputs):
    before = deepcopy(inputs)
    actual = _outcome(p._roots, inputs)
    assert actual == _outcome(_parent_roots, inputs)
    assert inputs == before
    return actual


@pytest.mark.parametrize('variation', ['ordinary', 'duplicate', 'unicode', 'relative_environment'])
def test_disjoint_results_preserve_order_and_inputs(variation):
    inputs = _case()
    expected, selection, launch = inputs
    lookup = expected['policy']['readonly_lookups']
    if variation == 'duplicate':
        lookup['inputs'].append(lookup['repository'])
    elif variation == 'unicode':
        lookup['inputs'].append('/authority/μικρό')
    elif variation == 'relative_environment':
        expected['permission_environment']['CLAUDE_CONFIG_DIR'] = 'relative/ignored'
    result = _assert_parity(inputs)
    assert result == ('returned', [PurePosixPath(value) for value in launch.values()])
    assert type(result[1]) is list
    assert all(type(value) is PurePosixPath for value in result[1])


@pytest.mark.parametrize('target', ['config_root', 'evidence_root'])
@pytest.mark.parametrize('protected_path', [
    '/neutral/{target}', '/neutral/{target}/child', '/neutral',
])
def test_equal_ancestor_and_descendant_authority_refuses(target, protected_path):
    inputs = _case()
    inputs[0]['policy']['readonly_lookups']['inputs'].append(protected_path.format(target=target))
    result = _assert_parity(inputs)
    assert result[0] == 'raised'
    assert result[2] == 'native shared permission: neutral roots overlap authority'


@pytest.mark.parametrize('second_root', ['/neutral/config_root', '/neutral/config_root/child', '/neutral'])
def test_root_pair_overlap_refuses(second_root):
    inputs = _case()
    inputs[2]['stub_root'] = second_root
    result = _assert_parity(inputs)
    assert result[0] == 'raised'
    assert result[2] == 'native shared permission: neutral roots overlap authority'


def test_invalid_launch_precedes_invalid_protected():
    inputs = _case()
    inputs[2]['evidence_root'] = None
    inputs[0]['policy']['readonly_lookups']['inputs'].append('relative')
    result = _assert_parity(inputs)
    assert result[0] == 'raised'
    assert result[2] == 'native shared permission: path is not text'


@pytest.mark.parametrize('late_invalid', ['relative', '/authority//alias', None, '/authority/\ud800'])
def test_complete_protected_validation_precedes_overlapping_roots(late_invalid):
    inputs = _case()
    inputs[2]['stub_root'] = inputs[2]['config_root']
    inputs[0]['policy']['readonly_lookups']['output_directories'].append(late_invalid)
    result = _assert_parity(inputs)
    assert result[0] == 'raised'
    if late_invalid is None:
        assert result[2] == 'native shared permission: path is not text'
    elif '\ud800' in late_invalid:
        assert result[1] is UnicodeEncodeError
    else:
        assert result[2] == 'native shared permission: path is not canonical absolute'


def test_each_protected_entry_is_parsed_once_without_deduplication(monkeypatch):
    inputs = _case()
    lookup = inputs[0]['policy']['readonly_lookups']
    lookup['inputs'].append(lookup['repository'])
    real_path = p._path
    calls = []

    def counted(value):
        calls.append(value)
        return real_path(value)

    monkeypatch.setattr(p, '_path', counted)
    old_result = _parent_roots(*inputs)
    old_calls = calls[:]
    calls.clear()
    assert p._roots(*inputs) == old_result
    launch_values = list(inputs[2].values())
    protected = [
        '/authority/repository', '/authority/selection.json', '/authority/source',
        '/authority/stage', '/authority/bundle', '/authority/chunks',
        '/authority/repository', '/authority/output', '/authority/config',
        '/authority/instruction',
    ]
    assert old_calls == launch_values + protected * 4
    assert calls == launch_values + protected


def test_changed_second_call_revalidates_current_protected_input(monkeypatch):
    inputs = _case()
    assert p._roots(*inputs)
    inputs[0]['policy']['readonly_lookups']['inputs'][0] = '/neutral/config_root/changed'
    real_path = p._path
    calls = []

    def counted(value):
        calls.append(value)
        return real_path(value)

    monkeypatch.setattr(p, '_path', counted)
    result = _assert_parity(inputs)
    assert result[0] == 'raised'
    assert result[2] == 'native shared permission: neutral roots overlap authority'
    assert '/neutral/config_root/changed' in calls
