"""PR 6302 exact grant construction and host identity checks, 2026-11-21.

No native binary or provider executes. Temporary directories exercise actual
filesystem aliases; saved argv construction must not inspect those paths.
"""
from copy import deepcopy
import json
from pathlib import Path
import sys
from types import ModuleType

import pytest

from data_sheets_schema import native_stage_root_grant as grant
from data_sheets_schema import native_shared_permission_protocol as protocol
from data_sheets_schema import native_shared_permissions as permissions
from data_sheets_schema.native_shared_evidence import require_physical_directory
from tests.test_native_execution_registration_v2 import isolated_modules  # noqa: F401


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


def _verified_permission_graph():
    from data_sheets_schema import native_execution_authority_v2 as authority
    identity = authority.dependency_identity()
    return authority.refuse_legacy_consumer_imports(Path(permissions.__file__).read_bytes(),
        name='data_sheets_schema.native_shared_permissions',
        package_sources=identity['base']['package_sources'])


def test_verified_consumer_import_graph_keeps_diagnostic_execution_in_host(isolated_modules):
    graph = _verified_permission_graph()
    assert 'data_sheets_schema.native_stage_root_diagnostic' in graph
    assert 'data_sheets_schema.native_permission_probe' not in graph


def test_graph_fixture_removes_prior_alias_but_preserves_real_origin_refusal(tmp_path, monkeypatch, request):
    """Software ordering control; only the test fixture may clear old aliases."""
    from data_sheets_schema import native_execution_authority_v2 as authority
    foreign = ModuleType('prepare_registration')
    foreign.__file__ = str(tmp_path / 'foreign-prepare-registration.py')
    monkeypatch.setitem(sys.modules, foreign.__name__, foreign)
    # Request the actual common fixture after installing prior-test pollution.
    # Production dependency_identity remains unpatched throughout this control.
    isolated = request.getfixturevalue('isolated_modules')
    assert foreign.__name__ in isolated
    assert sys.modules.get(foreign.__name__) is not foreign
    graph = _verified_permission_graph()
    assert 'data_sheets_schema.native_stage_root_diagnostic' in graph
    assert 'data_sheets_schema.native_permission_probe' not in graph
    with monkeypatch.context() as patch:
        patch.setitem(sys.modules, foreign.__name__, foreign)
        with pytest.raises(ValueError, match='native controller dependency imported from another origin: prepare_registration'):
            authority.dependency_identity()
        assert sys.modules[foreign.__name__] is foreign
    assert _verified_permission_graph() == graph


def test_grant_rejects_noncanonical_or_unbounded_directory_spellings():
    invalid = ('/', '', 'relative/stage', '//attempt/stage', '/attempt//stage',
               '/attempt/stage/', '/attempt/./stage', '/attempt/../stage',
               '/attempt/stage\n', '/attempt/stage ', ' /attempt/stage',
               '/attempt/sta\x00ge', None, True, ['/attempt/stage'])
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
    with pytest.raises(ValueError):
        require_physical_directory(str(root / 'stage '), must_exist=False)
