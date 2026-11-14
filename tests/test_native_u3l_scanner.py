"""U3-L closed runtime-profile source proofs, 2026-11-09 (#4354).

Inputs are copied source bytes; mutations never import a generation module or
invoke a runtime. Each negative calibrates the unchanged integrated route first.
"""
import ast

import pytest

from tests.test_native_u5_scanner import copied_route, PREPARER, RUNNER, scan


FUNCTIONS = {'prepare', '_prepare', 'prepare_synthetic', 'verify_preparer', '_read', '_wire',
             'require_production', 'validate_runtime_v2'}
PROFILES = 'src/data_sheets_schema/native_runtime_profiles.py'
VALUES = 'src/data_sheets_schema/native_shared_runtime_values.py'
CURRENT_IMPORT = 'from .native_shared_runtime_values import validate_runtime_v2 as validate_runtime'
LEGACY_IMPORT = 'from .native_execution_registration import validate_runtime'


def _parts(path, function):
    original = path.read_bytes()
    if function is None:
        return b'', original, b''
    assert function in FUNCTIONS
    definitions = [node for node in ast.parse(original).body
                   if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                   and node.name == function]
    assert len(definitions) == 1 and isinstance(definitions[0], ast.FunctionDef)
    node = definitions[0]
    lines = original.splitlines(keepends=True)
    return (b''.join(lines[:node.lineno - 1]),
            b''.join(lines[node.lineno - 1:node.end_lineno]),
            b''.join(lines[node.end_lineno:]))


def _change(path, function, before, after):
    prefix, body, suffix = _parts(path, function)
    before, after = before.encode('utf-8'), after.encode('utf-8')
    assert before != after and body.count(before) == 1
    changed = body.replace(before, after, 1)
    path.write_bytes(prefix + changed + suffix)
    assert path.read_bytes() == prefix + changed + suffix


def _derive(root):
    return scan.derive_native_shared_route(root, scan._tree(root / RUNNER))


@pytest.fixture
def route_root(tmp_path):
    root = copied_route(tmp_path)
    assert _derive(root)['enabled_values'] == [1]
    return root


def test_integrated_profile_route_derives(route_root):
    route = _derive(route_root)
    assert route['enabled_values'] == [1]
    assert route['renderer'] == 26
    assert {PROFILES, VALUES} <= set(route['evidence'])
    source = route_root / PREPARER
    for name in ('prepare', '_prepare', 'prepare_synthetic', 'verify_preparer', '_read', '_wire'):
        prefix, body, suffix = _parts(source, name)
        assert prefix + body + suffix == source.read_bytes()
        assert PREPARER + ':' + str(prefix.count(b'\n') + 1) in route['evidence']


@pytest.mark.parametrize('function,before,after', [
    ('prepare', '    require_production(declared_runtime)\n', ''),
    ('prepare',
     '    require_production(declared_runtime)\n    runtime = validate_runtime(declared_runtime)\n'
     '    captured = selection.capture(selection_path)\n',
     '    runtime = validate_runtime(declared_runtime)\n'
     '    captured = selection.capture(selection_path)\n    require_production(declared_runtime)\n'),
    ('prepare_synthetic',
     "    require_synthetic(c.strict_json(_read(str(runtime_path), 'runtime declaration',\n"
     "                                        c.HARD_LIMITS['input_bytes']).raw, 'runtime declaration'))\n", ''),
    ('prepare_synthetic', 'require_synthetic(c.strict_json(', 'require_production(c.strict_json('),
    ('prepare_synthetic', 'return _prepare(selection_path, runtime_path,',
     'return prepare(selection_path, runtime_path,'),
    ('prepare_synthetic', 'expected_profile=SYNTHETIC_PROFILE', "expected_profile='production'"),
    ('prepare_synthetic', ', expected_profile=SYNTHETIC_PROFILE', ''),
    ('_prepare',
     '    if profile_name(runtime) != expected_profile:\n'
     "        raise ValueError('preparation entry differs from the explicitly selected runtime profile')\n", ''),
    ('_prepare', 'if profile_name(runtime) != expected_profile:',
     'if profile_name(runtime) == expected_profile:'),
])
def test_profile_entry_guards_and_dispatch_refuse_changes(route_root, function, before, after):
    _change(route_root / PREPARER, function, before, after)
    with pytest.raises(scan.ConfigError, match='unsupported v2 render producer: ' + function):
        _derive(route_root)


@pytest.mark.parametrize('before,after', [
    ('profile_name(runtime) == SYNTHETIC_PROFILE', 'profile_name(runtime) != SYNTHETIC_PROFILE'),
    ('prepare_synthetic if profile_name(runtime) == SYNTHETIC_PROFILE else prepare',
     'prepare if profile_name(runtime) == SYNTHETIC_PROFILE else prepare_synthetic'),
    ("preparer(body['selection']['path'], body['runtime']['path'],",
     "preparer(body['runtime']['path'], body['selection']['path'],"),
    ("max_draft_checks=body['max_draft_checks']", 'max_draft_checks=1'),
    ("if c.canonical(body) != c.canonical(expected['registration']):",
     "if c.canonical(body) == c.canonical(expected['registration']):"),
    ("if body['dependencies'] != dependencies:", 'if False:'),
    ("c.exact(body, _PREPARATION_KEYS, 'shared-native v2 preparation')", 'pass'),
    ("_read(body['runtime']['path'], 'runtime declaration',",
     "_read(body['selection']['path'], 'runtime declaration',"),
])
def test_verify_preparer_selector_arguments_and_comparison_are_exact(route_root, before, after):
    _change(route_root / PREPARER, 'verify_preparer', before, after)
    with pytest.raises(scan.ConfigError, match='unsupported v2 render producer: verify_preparer'):
        _derive(route_root)


@pytest.mark.parametrize('statement,producer', [
    ('escaped = prepare', 'prepare'),
    ('escaped = prepare_synthetic', 'prepare_synthetic'),
    ('escaped = prepare if condition else replacement', 'prepare'),
    ('escaped = prepare_synthetic if condition else replacement', 'prepare_synthetic'),
    ('escaped = prepare_synthetic if profile_name(runtime) == SYNTHETIC_PROFILE else prepare', 'prepare'),
    ('escaped = prepare.__call__', 'prepare'),
    ('escaped = prepare_synthetic.__call__', 'prepare_synthetic'),
])
def test_only_the_two_proved_dispatcher_references_may_escape(route_root, statement, producer):
    _change(route_root / PREPARER, None, '\ndef required_checks(event):',
            '\n' + statement + '\n\ndef required_checks(event):')
    with pytest.raises(scan.ConfigError,
                       match='v2 render function escapes its fixed direct callers: ' + producer):
        _derive(route_root)


@pytest.mark.parametrize('function,before,after', [
    ('_read', 'max_bytes=maximum', 'max_bytes=1'),
    ('_read', ').captured', ')'),
    ('_wire', "value['registration']['schema_version'] != VERSION",
     "value['registration']['schema_version'] == VERSION"),
    ('_wire', "value['controller_sources_sha256'] != authority.neutral.composition.SOURCES_SHA256",
     "value['controller_sources_sha256'] == authority.neutral.composition.SOURCES_SHA256"),
    ('_wire', 'identity = authority.dependency_identity()', 'identity = {}'),
    ('_wire', 'authority.require_committed(identity)', 'pass'),
    ('_wire', "controls['prepare_registration_v2'].require_envelope(value)",
     "controls['prepare_registration_v2'].envelope(value)"),
])
def test_profile_wire_and_reader_helpers_are_exact(route_root, function, before, after):
    _change(route_root / PREPARER, function, before, after)
    with pytest.raises(scan.ConfigError, match='unsupported v2 render producer: ' + function):
        _derive(route_root)


def test_profile_reader_requires_its_bound_current_import(route_root):
    _change(route_root / PREPARER, None, 'from .native_shared_evidence import read_regular\n',
            'from .foreign_evidence import read_regular\n')
    with pytest.raises(scan.ConfigError, match='v2 producer import is not exact: read_regular'):
        _derive(route_root)


@pytest.mark.parametrize('name,before,after', [
    ('MAX_WIRE_BYTES', "MAX_WIRE_BYTES = c.HARD_LIMITS['request_bytes']", 'MAX_WIRE_BYTES = 1'),
    ('_PREPARATION_KEYS', "'instruction_sha256', 'outputs', 'pinned_files'))",
     "'instruction_sha256', 'pinned_files'))"),
    ('MAX_WIRE_BYTES', '\ndef required_checks(event):',
     '\nMAX_WIRE_BYTES = 1\n\ndef required_checks(event):'),
    ('_PREPARATION_KEYS', '\ndef required_checks(event):',
     '\n_PREPARATION_KEYS = frozenset()\n\ndef required_checks(event):'),
])
def test_profile_wire_constants_cannot_change_or_be_rebound(route_root, name, before, after):
    _change(route_root / PREPARER, None, before, after)
    with pytest.raises(scan.ConfigError, match='v2 preparation identity is not exact: ' + name):
        _derive(route_root)


@pytest.mark.parametrize('statement', [
    'import data_sheets_schema.native_runtime_profiles as unchecked_profiles',
    'from . import native_shared_runtime_values as unchecked_values',
    'from .native_runtime_profiles import require_production as unchecked_production',
    'from .native_shared_runtime_values import validate_runtime_v2 as unchecked_runtime',
    'import data_sheets_schema as unchecked_package\n'
    'unchecked_package.native_shared_runtime_values.validate_runtime_v2.__code__ = (lambda value: value).__code__',
    'import data_sheets_schema.native_shared_contract',
    'from src import data_sheets_schema as unchecked',
    'from data_sheets_schema import __dict__ as unchecked',
])
def test_extra_profile_authority_alias_imports_refuse(route_root, statement):
    _change(route_root / PREPARER, None, '\ndef required_checks(event):',
            '\n' + statement + '\n\ndef required_checks(event):')
    with pytest.raises(scan.ConfigError,
                       match='v2 preparation profile authority has an unsupported import'):
        _derive(route_root)


@pytest.mark.parametrize('relative,function,before,after', [
    (PROFILES, 'require_production', 'profile_name(runtime) != PRODUCTION_PROFILE',
     'profile_name(runtime) == PRODUCTION_PROFILE'),
    (VALUES, 'validate_runtime_v2', 'profiles.profile_name(value) == profiles.SYNTHETIC_PROFILE',
     'profiles.profile_name(value) != profiles.SYNTHETIC_PROFILE'),
])
def test_both_profile_authority_sources_are_pinned(route_root, relative, function, before, after):
    _change(route_root / relative, function, before, after)
    with pytest.raises(scan.ConfigError, match='v2 envelope authority source changed: ' + relative):
        _derive(route_root)


def test_integrated_producer_cannot_borrow_legacy_runtime_validator(route_root):
    _change(route_root / PREPARER, None, CURRENT_IMPORT, LEGACY_IMPORT)
    with pytest.raises(scan.ConfigError, match='v2 producer import is not exact: validate_runtime'):
        _derive(route_root)


@pytest.mark.parametrize('legacy_import', [False, True])
def test_legacy_producer_cannot_borrow_integrated_dispatcher(route_root, legacy_import):
    path = route_root / PREPARER
    _, legacy, _ = _parts(path, '_prepare')
    for before, after in (
        (b'def _prepare(', b'def prepare('),
        (b', expected_profile):', b'):'),
        (b'    from .native_runtime_profiles import profile_name\n'
         b'    if profile_name(runtime) != expected_profile:\n'
         b"        raise ValueError('preparation entry differs from the explicitly selected runtime profile')\n", b''),
    ):
        assert legacy.count(before) == 1
        legacy = legacy.replace(before, after, 1)
    prefix, original, suffix = _parts(path, 'prepare')
    assert legacy != original
    path.write_bytes(prefix + legacy + suffix)
    if legacy_import:
        _change(path, None, CURRENT_IMPORT, LEGACY_IMPORT)
    diagnostic = ('v2 render function escapes its fixed direct callers: prepare' if legacy_import
                  else 'v2 producer import is not exact: validate_runtime')
    with pytest.raises(scan.ConfigError, match=diagnostic):
        _derive(route_root)
