"""PR 6302 exact grant construction and host identity checks, 2026-11-21.

No native binary or provider executes. Temporary directories exercise actual
filesystem aliases; saved argv construction must not inspect those paths.
"""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from data_sheets_schema import native_stage_root_grant as grant
from data_sheets_schema import native_shared_permission_protocol as protocol
from data_sheets_schema import native_shared_permissions as permissions
from data_sheets_schema.native_shared_evidence import require_physical_directory


def test_exact_grant_preserves_frozen_protocol_and_input_policy():
    policy = {'allowed_tools': ['Write', 'Read', 'Write', 'Bash(selected helper)']}
    before = deepcopy(policy)
    original = protocol.permission_arguments(policy)
    arguments = grant.permission_arguments(policy, '/attempt/stage')
    assert arguments[:-1] == original[:-1] == ['--input-format', 'stream-json', '--settings']
    assert arguments.count('--settings') == 1
    assert json.loads(arguments[-1]) == {'permissions': {
        'allow': before['allowed_tools'], 'additionalDirectories': ['/attempt/stage']}}
    assert json.loads(original[-1]) == {'permissions': {'allow': before['allowed_tools']}}
    assert protocol.permission_arguments(policy) == original
    assert policy == before


def test_grant_rejects_noncanonical_or_unbounded_directory_spellings():
    invalid = ('/', '', 'relative/stage', '//attempt/stage', '/attempt//stage',
               '/attempt/stage/', '/attempt/./stage', '/attempt/../stage',
               '/attempt/stage\n', '/attempt/sta\x00ge', None, True, ['/attempt/stage'])
    for root in invalid:
        with pytest.raises(ValueError):
            grant.permission_arguments({'allowed_tools': ['Read', 'Write']}, root)


def test_probe_grants_explicit_effect_root_and_retains_isolation_flags():
    expected = {'runtime': {'executable': {'path': '/fixed/native'}, 'model': 'fixed-model',
                           'effort': 'high', 'budget_guard_usd': '01.50'}}
    policy = {'allowed_tools': ['Read', 'Write']}
    argv = permissions.probe_argv(expected, policy, effect_root='/probe/trace/effect_root')
    assert argv[0] == '/fixed/native'
    assert argv.count('--settings') == 1
    settings = json.loads(argv[argv.index('--settings') + 1])
    assert settings == {'permissions': {
        'allow': ['Read', 'Write'], 'additionalDirectories': ['/probe/trace/effect_root']}}
    assert all(argv.count(flag) == 1 for flag in (
        '--restricted', '--safe-mode', '--strict-mcp-config', '--disable-slash-commands'))
    assert '--add-dir' not in argv
    assert argv[argv.index('--max-budget-usd') + 1] == '01.50'
    with pytest.raises(TypeError):
        permissions.probe_argv(expected, policy)


def test_grant_and_probe_argv_replay_never_resolve_recorded_paths(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail('pure grant construction inspected a recorded filesystem path')
    for name in ('resolve', 'stat', 'lstat', 'open', 'read_bytes', 'read_text'):
        monkeypatch.setattr(Path, name, forbidden)
    root = '/recorded/host/attempt/stage'
    policy = {'allowed_tools': ['Read']}
    assert json.loads(grant.permission_arguments(policy, root)[-1])[
        'permissions']['additionalDirectories'] == [root]
    expected = {'runtime': {'executable': {'path': '/fixed/native'}, 'model': 'fixed-model',
                           'effort': 'high', 'budget_guard_usd': '1'}}
    argv = permissions.probe_argv(expected, policy, effect_root=root)
    assert json.loads(argv[argv.index('--settings') + 1])[
        'permissions']['additionalDirectories'] == [root]


def test_host_check_accepts_only_exact_physical_stage_directory(tmp_path):
    root = tmp_path.resolve() / 'stage'
    assert require_physical_directory(str(root), must_exist=False) == str(root)
    with pytest.raises(ValueError):
        require_physical_directory(str(root), must_exist=True)
    root.mkdir()
    assert require_physical_directory(str(root), must_exist=True) == str(root)
    alias = root.parent / 'alias'
    alias.symlink_to(root, target_is_directory=True)
    for must_exist in (False, True):
        with pytest.raises(ValueError, match='alias'):
            require_physical_directory(str(alias), must_exist=must_exist)
        with pytest.raises(ValueError):
            require_physical_directory(str(alias / 'child'), must_exist=must_exist)


def test_host_check_refuses_file_dangling_alias_and_invalid_choice(tmp_path):
    root = tmp_path.resolve()
    file = root / 'file'
    file.write_bytes(b'not a stage directory')
    alias = root / 'dangling'
    alias.symlink_to(root / 'absent', target_is_directory=True)
    for target in (file, alias):
        for must_exist in (False, True):
            with pytest.raises(ValueError):
                require_physical_directory(str(target), must_exist=must_exist)
    for choice in (None, 0, 1, 'true'):
        with pytest.raises(ValueError):
            require_physical_directory(str(root), must_exist=choice)
    with pytest.raises(ValueError):
        require_physical_directory('/', must_exist=True)
