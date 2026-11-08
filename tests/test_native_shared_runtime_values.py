"""U3-D round-8 parity with untouched v1 runtime validation, 2026-11-07.

The executable-bit fixture is ordinary inert local data, fingerprinted but
never invoked. No native executable, provider or network request is needed.
"""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import subprocess

import pytest

from data_sheets_schema import native_attribution_registration as legacy_json
from data_sheets_schema import native_execution_registration as legacy
from data_sheets_schema import native_shared_runtime_values as neutral


@pytest.fixture(autouse=True)
def no_process_launch(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail('runtime parity must only fingerprint ordinary fixture bytes')
    for name in ('Popen', 'run', 'call', 'check_call', 'check_output'):
        monkeypatch.setattr(subprocess, name, forbidden)
    for name in ('system', 'execv', 'execve', 'execvp', 'execvpe', 'posix_spawn', 'posix_spawnp'):
        if hasattr(os, name):
            monkeypatch.setattr(os, name, forbidden)


@pytest.fixture
def runtime(tmp_path):
    root = tmp_path.resolve()
    executable = root / 'inert-fingerprint-fixture'
    executable.write_bytes(b'Ordinary inert local bytes. Never execute this file.\n')
    executable.chmod(0o700)
    return {
        'route': neutral.ROUTE,
        'executable': {'path': str(executable),
            'sha256': hashlib.sha256(executable.read_bytes()).hexdigest(),
            'version': 'LOCAL FINGERPRINT FIXTURE', 'init_version': 'fixture-1'},
        'model': 'synthetic-test-model', 'auxiliary_models': [], 'effort': 'medium',
        'limits': {'contextWindow': 100000, 'maxOutputTokens': 10000},
        'limits_basis': 'Explicit synthetic limit, never a model capability claim',
        'provider': 'synthetic-first-party-selection',
        'auth': {'loggedIn': True, 'authMethod': 'claude.ai', 'apiProvider': 'firstParty',
            'subscriptionType': 'synthetic-test', 'expected_api_key_source': 'none'},
        'environment': {'PATH': '/usr/bin:/bin', 'HOME': str(root),
            'CLAUDE_SECURESTORAGE_CONFIG_DIR': '', 'CLAUDE_CODE_DISABLE_1M_CONTEXT': '1'},
        'deadline_seconds': 180, 'budget_guard_usd': '1.00',
        'keep_awake': {'policy': 'not_applicable', 'host_platform': 'synthetic-host',
            'basis': 'Offline data validation only'},
    }


def test_neutral_runtime_constants_retain_types_values_and_argv_order():
    for name in ('ROUTE', 'RUNTIME_KEYS', 'BASE_ENV_KEYS', 'ENV_REQUIRED', 'POLICY_ENV', 'FLAGS'):
        actual, expected = getattr(neutral, name), getattr(legacy, name)
        assert type(actual) is type(expected)
        assert actual == expected
        if isinstance(actual, (dict, set, list)):
            assert actual is not expected


def test_real_fingerprint_and_validation_match_without_any_process(runtime):
    path = Path(runtime['executable']['path'])
    raw = path.read_bytes()
    expected = {'path': str(path), 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
    assert neutral.executable_identity(path) == legacy.executable_identity(path) == expected
    actual = neutral.validate_runtime(runtime)
    assert actual == legacy.validate_runtime(runtime) == runtime
    assert actual is not runtime
    assert actual['executable'] is not runtime['executable']
    assert actual['environment'] is not runtime['environment']
    assert actual['auxiliary_models'] is not runtime['auxiliary_models']
    actual['environment']['HOME'] = '/different-returned-copy'
    assert runtime['environment']['HOME'] == str(path.parent)
    assert path.read_bytes() == raw


@pytest.mark.parametrize('change', ['unicode', 'explicit_macos', 'max_deadline', 'context_zero', 'auxiliary', 'padded_text'])
def test_accepted_runtime_edges_preserve_legacy_value_and_json_copy(runtime, change):
    if change == 'unicode':
        class Text(str):
            pass
        runtime['provider'] = Text('Données — 日本語')
        runtime['limits_basis'] = 'Measured fixture α'
    elif change == 'explicit_macos':
        runtime['keep_awake'].update(policy='macos_iokit_ims_v1', host_platform='darwin')
    elif change == 'max_deadline':
        runtime['deadline_seconds'] = 86400
    elif change == 'context_zero':
        runtime['environment']['CLAUDE_CODE_DISABLE_1M_CONTEXT'] = '0'
    elif change == 'auxiliary':
        runtime['auxiliary_models'] = [f'fixture-model-{index}' for index in range(32)]
    else:
        runtime['limits_basis'] = '  preserved surrounding spaces  '
    actual = neutral.validate_runtime(runtime)
    assert actual == legacy.validate_runtime(runtime)
    assert neutral._encoded(actual) == legacy_json._encoded(actual)
    assert type(actual['provider']) is str


@pytest.mark.parametrize('key', sorted(neutral.RUNTIME_KEYS))
def test_missing_runtime_choice_has_identical_refusal(runtime, key):
    assert neutral.validate_runtime(runtime) == legacy.validate_runtime(runtime)
    del runtime[key]
    with pytest.raises(ValueError) as before:
        legacy.validate_runtime(runtime)
    with pytest.raises(ValueError) as after:
        neutral.validate_runtime(runtime)
    assert str(after.value) == str(before.value)


@pytest.mark.parametrize(('path', 'replacement'), [
    (('route',), 'other-route'),
    (('unregistered',), True),
    (('executable', 'sha256'), 'A' * 64),
    (('executable', 'sha256'), '0' * 64),
    (('executable', 'version'), ''),
    (('executable', 'extra'), True),
    (('model',), '--unregistered-option'),
    (('effort',), 'two words'),
    (('auxiliary_models',), ['duplicate', 'duplicate']),
    (('auxiliary_models',), ['synthetic-test-model']),
    (('auxiliary_models',), ('tuple-not-list',)),
    (('limits', 'contextWindow'), True),
    (('limits', 'maxOutputTokens'), 100001),
    (('limits', 'maxOutputTokens'), 0),
    (('limits_basis',), '\nnot-single-line'),
    (('provider',), None),
    (('auth', 'loggedIn'), 1),
    (('auth', 'authMethod'), 'api-key'),
    (('auth', 'apiProvider'), 'other'),
    (('auth', 'expected_api_key_source'), 'environment'),
    (('auth', 'subscriptionType'), '   '),
    (('environment', 'ANTHROPIC_API_KEY'), 'synthetic-forbidden-value'),
    (('environment', 'PATH'), 'relative:/bin'),
    (('environment', 'PATH'), '/bin:'),
    (('environment', 'HOME'), 'relative'),
    (('environment', 'HOME'), ''),
    (('environment', 'CLAUDE_CODE_DISABLE_1M_CONTEXT'), 'unknown'),
    (('environment', 'CLAUDE_SECURESTORAGE_CONFIG_DIR'), 'relative'),
    (('environment', 'LANG'), 1),
    (('deadline_seconds',), True),
    (('deadline_seconds',), 86401),
    (('budget_guard_usd',), 1),
    (('budget_guard_usd',), '-1'),
    (('budget_guard_usd',), 'NaN'),
    (('budget_guard_usd',), '1e1'),
    (('budget_guard_usd',), '0'),
    (('keep_awake', 'policy'), 'best-effort'),
    (('keep_awake', 'basis'), ''),
])
def test_malformed_runtime_has_identical_refusal(runtime, path, replacement):
    assert neutral.validate_runtime(runtime) == legacy.validate_runtime(runtime)
    changed = deepcopy(runtime)
    cursor = changed
    for component in path[:-1]:
        cursor = cursor[component]
    cursor[path[-1]] = replacement
    with pytest.raises(ValueError) as before:
        legacy.validate_runtime(changed)
    with pytest.raises(ValueError) as after:
        neutral.validate_runtime(changed)
    assert str(after.value) == str(before.value)
    assert runtime == neutral.validate_runtime(runtime)


@pytest.mark.parametrize('change', ['relative', 'symlink', 'nonexecutable', 'missing'])
def test_real_fingerprint_refusals_match(runtime, change, monkeypatch):
    original = Path(runtime['executable']['path'])
    assert neutral.executable_identity(original) == legacy.executable_identity(original)
    path = original
    if change == 'relative':
        monkeypatch.chdir(original.parent)
        path = Path(original.name)
    elif change == 'symlink':
        path = original.with_name('alias')
        path.symlink_to(original)
    elif change == 'nonexecutable':
        original.chmod(0o600)
    else:
        path = original.with_name('missing')
    with pytest.raises((ValueError, OSError)) as before:
        legacy.executable_identity(path)
    with pytest.raises((ValueError, OSError)) as after:
        neutral.executable_identity(path)
    assert type(after.value) is type(before.value)
    assert str(after.value) == str(before.value)


def test_json_roundtrip_preserves_frozen_bytes_unicode_and_normalization():
    value = {'z': ('α', {'b': 2, 'a': '日本語'}), 'a': True}
    raw = neutral._encoded(value)
    assert raw == legacy_json._encoded(value)
    assert raw.endswith(b'\n') and 'α'.encode() in raw and b'\\u03b1' not in raw
    assert raw == (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()
    assert neutral._json(raw) == legacy_json._json(raw) == {'a': True, 'z': ['α', {'a': '日本語', 'b': 2}]}


@pytest.mark.parametrize('raw', [b'{"a":1,"a":2}', b'{"a":{"x":1,"x":2}}', b'NaN', b'Infinity', b'-Infinity'])
def test_json_parser_preserves_legacy_duplicate_and_nonfinite_refusal(raw):
    with pytest.raises(ValueError) as before:
        legacy_json._json(raw)
    with pytest.raises(ValueError) as after:
        neutral._json(raw)
    assert str(after.value) == str(before.value)


@pytest.mark.parametrize('value', [float('nan'), float('inf'), float('-inf')])
def test_json_encoder_preserves_legacy_nonfinite_refusal(value):
    with pytest.raises(ValueError) as before:
        legacy_json._encoded({'value': value})
    with pytest.raises(ValueError) as after:
        neutral._encoded({'value': value})
    assert str(after.value) == str(before.value)


def test_text_closed_and_digest_helpers_preserve_legacy_edges():
    assert neutral._text('  preserved  ', 'test') == legacy._text('  preserved  ', 'test')
    for module in (neutral, legacy):
        module._closed({'b': 2, 'a': 1}, {'a', 'b'}, 'test')
        module._sha_text('0' * 64, 'test')
    for name, args in (('_text', ('\0', 'test')), ('_closed', ({'a': 1}, {'a', 'b'}, 'test')),
                       ('_sha_text', ('A' * 64, 'test'))):
        with pytest.raises(ValueError) as before:
            getattr(legacy, name)(*args)
        with pytest.raises(ValueError) as after:
            getattr(neutral, name)(*args)
        assert str(after.value) == str(before.value)
