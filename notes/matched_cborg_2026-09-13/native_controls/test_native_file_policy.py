"""Exercise file boundaries and exact provenance of runtime output files."""
import os
import re

import pytest

from budgeted_cborg import BudgetStop
from native_file_policy import FileAccess


@pytest.fixture
def files(tmp_path):
    root = tmp_path / 'work'; root.mkdir()
    output = root / 'outputs'; output.mkdir()
    source = root / 'source.txt'; source.write_text('registered source')
    config = tmp_path / 'config'; config.mkdir()
    policy = {'readonly_lookups': {'repository': str(root), 'inputs': [str(source)],
                                  'output_directories': [str(output)]}}
    access = FileAccess(policy, config)
    session = '12345678-1234-1234-1234-123456789abc'
    access.observe({'type': 'system', 'subtype': 'init', 'cwd': str(root),
                    'session_id': session}, {}, {})
    path = config / 'projects' / re.sub(r'[^a-zA-Z0-9]', '-', str(root)) / session / 'tool-results/abc.txt'
    path.parent.mkdir(parents=True); path.write_text('observed tool output')
    event = {'type': 'user', 'session_id': session,
             'message': {'content': [{'type': 'tool_result', 'tool_use_id': 'source_tool',
                                     'content': f'<persisted-output>\nFull output saved to: {path}\n',
                                     'is_error': False}]},
             'tool_use_result': {'persistedOutputPath': str(path), 'persistedOutputSize': path.stat().st_size}}
    calls = {'source_tool': {'name': 'Bash', 'input': {'command': 'prescribed helper'}}}
    decisions = {'source_tool': 'prescribed'}
    return access, source, output, path, event, calls, decisions


@pytest.mark.parametrize('tool_error', [False, True])
def test_persisted_output_is_denied_until_native_origin_is_observed(files, tool_error):
    access, source, output, path, event, calls, decisions = files
    event['message']['content'][0]['is_error'] = tool_error
    assert access.classify('Read', {'file_path': str(path)})[0] == 'not_prescribed'
    record = access.observe(event, calls, decisions)
    assert record['file']['bytes'] == path.stat().st_size
    assert access.classify('Read', {'file_path': str(path)})[0] == 'prescribed'
    assert access.classify('Write', {'file_path': str(path)})[0] == 'not_prescribed'
    assert access.classify('Read', {'file_path': str(path.parent / 'unobserved.txt')})[0] == 'not_prescribed'


def test_a_source_string_cannot_advertise_a_persisted_file(files):
    access, source, output, path, event, calls, decisions = files
    event.pop('tool_use_result')
    assert access.observe(event, calls, decisions) is None
    assert access.classify('Read', {'file_path': str(path)})[0] == 'not_prescribed'


@pytest.mark.parametrize('change', ['session', 'path', 'wrapper', 'size', 'denied', 'unknown_call', 'read_origin', 'link'])
def test_forged_or_mismatched_persisted_provenance_stops(files, change):
    access, source, output, path, event, calls, decisions = files
    if change == 'session': event['session_id'] = 'other'
    elif change == 'path': event['tool_use_result']['persistedOutputPath'] = str(source)
    elif change == 'wrapper': event['message']['content'][0]['content'] = 'some source text'
    elif change == 'size': event['tool_use_result']['persistedOutputSize'] += 1
    elif change == 'denied': decisions['source_tool'] = 'not_prescribed'
    elif change == 'unknown_call': calls.clear()
    elif change == 'read_origin': calls['source_tool']['name'] = 'Read'
    elif change == 'link': path.unlink(); path.symlink_to(source)
    with pytest.raises(BudgetStop): access.observe(event, calls, decisions)


def test_modified_persisted_output_stops_before_read(files):
    access, source, output, path, event, calls, decisions = files
    access.observe(event, calls, decisions)
    path.write_text('replacement bytes')
    with pytest.raises(BudgetStop, match='changed before its read'):
        access.classify('Read', {'file_path': str(path)})


def test_output_root_symlink_does_not_widen_frozen_scope(files, tmp_path):
    access, source, output, path, event, calls, decisions = files
    outside = tmp_path / 'outside'; outside.mkdir()
    output.rmdir(); output.symlink_to(outside, target_is_directory=True)
    assert access.classify('Write', {'file_path': str(output / 'new.txt')})[0] == 'not_prescribed'


@pytest.mark.parametrize('tool', ['Read', 'Write'])
def test_hard_link_in_outputs_cannot_alias_a_preexisting_file(files, tool):
    access, source, output, path, event, calls, decisions = files
    linked = output / 'alias'; os.link(source, linked)
    assert access.classify(tool, {'file_path': str(linked)})[0] == 'not_prescribed'


def test_source_inside_an_output_directory_cannot_be_overwritten(files):
    access, source, output, path, event, calls, decisions = files
    access.outputs.append(source.parent)
    assert access.classify('Write', {'file_path': str(source)})[0] == 'not_prescribed'


def test_native_path_normalization_never_changes_file_contents_or_read_windows(files):
    access, source, *_ = files
    assert access.matches('Read', {'file_path': source.name, 'limit': 4},
                          {'file_path': str(source), 'limit': 4})
    assert not access.matches('Read', {'file_path': source.name, 'limit': 4},
                              {'file_path': str(source), 'limit': 5})
    assert not access.matches('Write', {'file_path': source.name, 'content': 'one'},
                              {'file_path': str(source), 'content': 'two'})


@pytest.mark.parametrize('path', ['', None, 'bad\0path'])
def test_malformed_path_stops_admission(files, path):
    access, *_ = files
    with pytest.raises(BudgetStop): access.classify('Read', {'file_path': path})
