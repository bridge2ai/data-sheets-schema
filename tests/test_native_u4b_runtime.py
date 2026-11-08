"""Offline U4b evidence/refusal tests, 2026-11-08; fake bytes, never a native run."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import subprocess

import pytest

from data_sheets_schema import native_u4b_runtime as subject
from data_sheets_schema import native_shared_runtime_values as historical


@pytest.fixture(autouse=True)
def no_process_launch(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail('U4b runtime evidence never executes a binary')
    for name in ('Popen', 'run', 'call', 'check_call', 'check_output'):
        monkeypatch.setattr(subprocess, name, forbidden)
    for name in ('system', 'execv', 'execve', 'execvp', 'execvpe', 'posix_spawn', 'posix_spawnp'):
        if hasattr(os, name):
            monkeypatch.setattr(os, name, forbidden)


def runtime_inputs(tmp_path, *, binary_bytes=b'Inert fingerprint fixture; never execute.\n'):
    """Shared fake fixture for U4b peers; accepts scripted local fake bytes."""
    root = tmp_path.resolve()
    updater = root / 'updater'
    updater.mkdir()
    source = updater / 'current'
    copied = root / 'durable-copy'
    for path in (source, copied):
        path.write_bytes(binary_bytes)
        path.chmod(0o700)
    init = {'type': 'system', 'subtype': 'init', 'model': subject.MODEL,
            'claude_code_version': 'fixture-1',
            'limits': {'contextWindow': 1_000_000, 'maxOutputTokens': 64_000},
            'thinking': {'type': 'adaptive'}}
    probe = root / 'saved-probe-init.jsonl'
    probe.write_text(json.dumps(init) + '\n')
    runtime = {'route': historical.ROUTE,
        'executable': {'path': str(copied), 'sha256': hashlib.sha256(binary_bytes).hexdigest(),
                       'version': 'local fixture', 'init_version': 'fixture-1'},
        'model': subject.MODEL, 'auxiliary_models': [], 'effort': 'high',
        'limits': deepcopy(init['limits']), 'limits_basis': 'not yet bound',
        'provider': 'synthetic-first-party-selection',
        'auth': {'loggedIn': True, 'authMethod': 'claude.ai', 'apiProvider': 'firstParty',
                 'subscriptionType': 'max', 'expected_api_key_source': 'none'},
        'environment': {'PATH': '/usr/bin:/bin', 'HOME': str(root),
                        'CLAUDE_SECURESTORAGE_CONFIG_DIR': '', 'CLAUDE_CODE_DISABLE_1M_CONTEXT': '0'},
        'deadline_seconds': 180, 'budget_guard_usd': '90',
        'keep_awake': {'policy': 'not_applicable', 'host_platform': 'synthetic-host',
                       'basis': 'Offline evidence test, not launch authority'}}
    arguments = {'probe_init_path': str(probe), 'updater_source': str(source),
                 'updater_root': str(updater), 'thinking_setting': {'type': 'adaptive'},
                 'thinking_basis': 'Explicit synthetic setting, not inferred from effort'}
    return runtime, arguments


@pytest.fixture
def inputs(tmp_path):
    return runtime_inputs(tmp_path)


def prepared(inputs):
    runtime, arguments = inputs
    return subject.prepare_runtime(runtime, **arguments)


def mutate_basis(runtime, change):
    result = deepcopy(runtime)
    basis = json.loads(result['limits_basis'])
    change(basis)
    result['limits_basis'] = subject._canonical(basis)
    return result


def test_real_evidence_binding_preserves_closed_runtime_and_original(inputs):
    runtime, arguments = inputs
    original = deepcopy(runtime)
    result = prepared(inputs)
    assert runtime == original
    assert set(result) == set(runtime) == historical.RUNTIME_KEYS
    assert subject.is_prepared_runtime(result)
    assert historical.validate_runtime(result) == result
    assert subject.validate_prepared_runtime(result) == result
    basis = json.loads(result['limits_basis'])
    assert basis['observed'] == {'model': subject.MODEL, 'limits': runtime['limits'], 'init_version': 'fixture-1'}
    assert basis['thinking']['observed'] == {'state': 'observed', 'field': 'thinking', 'value': {'type': 'adaptive'}}
    assert basis['durable_copy']['source']['inode'] != basis['durable_copy']['copy']['inode']
    assert basis['probe']['sha256'] == hashlib.sha256(Path(arguments['probe_init_path']).read_bytes()).hexdigest()


@pytest.mark.parametrize('field,value', [('model', 'claude-opus-5'), ('effort', 'medium'),
                                     ('budget_guard_usd', '90.00')])
def test_new_profile_refuses_changed_declaration(inputs, field, value):
    runtime, _ = inputs
    runtime[field] = value
    with pytest.raises(ValueError, match='U4b requires'):
        prepared(inputs)


@pytest.mark.parametrize('mutation', ['context', 'subscription', 'limits', 'version', 'observed_thinking'])
def test_declared_and_observed_identity_must_agree(inputs, mutation):
    runtime, arguments = inputs
    if mutation == 'context':
        runtime['environment']['CLAUDE_CODE_DISABLE_1M_CONTEXT'] = '1'
    elif mutation == 'subscription':
        runtime['auth']['subscriptionType'] = 'other'
    elif mutation == 'limits':
        runtime['limits']['maxOutputTokens'] -= 1
    elif mutation == 'version':
        runtime['executable']['init_version'] = 'other'
    else:
        arguments['thinking_setting'] = False
    with pytest.raises(ValueError):
        prepared(inputs)


@pytest.mark.parametrize('declared', [False, {'type': 'adaptive'}])
def test_missing_thinking_refuses_even_with_an_explicit_declared_setting(inputs, declared):
    _, arguments = inputs
    path = Path(arguments['probe_init_path'])
    init = json.loads(path.read_text())
    del init['thinking']
    path.write_text(json.dumps(init) + '\n')
    arguments['thinking_setting'] = declared
    with pytest.raises(ValueError, match='must expose an observed thinking setting'):
        prepared(inputs)


def test_observed_false_is_preserved_and_is_not_missing_thinking(inputs):
    _, arguments = inputs
    path = Path(arguments['probe_init_path'])
    init = json.loads(path.read_text())
    init['thinking'] = False
    path.write_text(json.dumps(init) + '\n')
    arguments['thinking_setting'] = False
    result = prepared(inputs)
    thinking = json.loads(result['limits_basis'])['thinking']
    assert thinking == {'declared': False, 'basis': arguments['thinking_basis'],
                        'observed': {'state': 'observed', 'field': 'thinking', 'value': False}}
    assert subject.validate_prepared_runtime(result) == result


@pytest.mark.parametrize('change', ['absent', 'null'])
def test_revalidation_refuses_unobserved_thinking_even_when_evidence_is_repinned(inputs, change):
    runtime = prepared(inputs)
    path = Path(inputs[1]['probe_init_path'])
    init = json.loads(path.read_text())
    if change == 'absent':
        del init['thinking']
    else:
        init['thinking'] = None
    raw = (json.dumps(init) + '\n').encode('utf-8')
    path.write_bytes(raw)

    def repin(basis):
        basis['probe'].update(sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw),
                              init_sha256=hashlib.sha256(raw.splitlines()[0]).hexdigest())
        basis['thinking']['observed'] = {'state': 'not_emitted', 'field': None, 'value': None}

    with pytest.raises(ValueError, match='observed thinking setting|explicit boolean'):
        subject.validate_prepared_runtime(mutate_basis(runtime, repin))


@pytest.mark.parametrize('field', ['thinking', 'declared', 'basis', 'observed'])
def test_registered_thinking_fields_are_required(inputs, field):
    runtime = prepared(inputs)

    def remove(basis):
        del (basis if field == 'thinking' else basis['thinking'])[field]

    with pytest.raises(ValueError, match='U4b runtime basis|thinking basis'):
        subject.validate_prepared_runtime(mutate_basis(runtime, remove))


@pytest.mark.parametrize('field', ['thinking', 'declared', 'basis', 'observed'])
def test_registered_thinking_fields_cannot_be_null(inputs, field):
    runtime = prepared(inputs)

    def clear(basis):
        (basis if field == 'thinking' else basis['thinking'])[field] = None

    with pytest.raises(ValueError):
        subject.validate_prepared_runtime(mutate_basis(runtime, clear))


def test_registered_not_emitted_state_cannot_replace_observed_probe_thinking(inputs):
    runtime = prepared(inputs)
    changed = mutate_basis(runtime, lambda basis: basis['thinking'].update(
        observed={'state': 'not_emitted', 'field': None, 'value': None}))
    with pytest.raises(ValueError, match='saved probe differs'):
        subject.validate_prepared_runtime(changed)


def test_preparation_requires_an_explicit_registered_thinking_setting(inputs):
    runtime, arguments = inputs
    del arguments['thinking_setting']
    with pytest.raises(TypeError, match='thinking_setting'):
        subject.prepare_runtime(runtime, **arguments)


@pytest.mark.parametrize('declared', [True, 'false', {'enabled': False}])
def test_observed_false_must_equal_the_registered_thinking_value(inputs, declared):
    _, arguments = inputs
    path = Path(arguments['probe_init_path'])
    init = json.loads(path.read_text())
    init['thinking'] = False
    path.write_text(json.dumps(init) + '\n')
    arguments['thinking_setting'] = declared
    with pytest.raises(ValueError, match='observed thinking differs'):
        prepared(inputs)


@pytest.mark.parametrize('change', ['missing_limits', 'duplicate_init', 'no_init', 'duplicate_key',
                                  'boolean_limit', 'wrong_model', 'unknown_thinking_alias', 'null_thinking'])
def test_saved_probe_refuses_missing_ambiguous_or_conflicting_evidence(inputs, change):
    _, arguments = inputs
    path = Path(arguments['probe_init_path'])
    original = path.read_text()
    init = json.loads(original)
    if change == 'missing_limits':
        del init['limits']
    elif change == 'boolean_limit':
        init['limits']['maxOutputTokens'] = True
    elif change == 'wrong_model':
        init['model'] = 'other'
    elif change == 'unknown_thinking_alias':
        init['thinkingEnabled'] = True
    elif change == 'null_thinking':
        init['thinking'] = None
    elif change == 'no_init':
        init['subtype'] = 'other'
    text = json.dumps(init) + '\n'
    if change == 'duplicate_init':
        text += original
    if change == 'duplicate_key':
        text = text.replace('"model":', '"model": "shadow", "model":')
    path.write_text(text)
    with pytest.raises(ValueError):
        prepared(inputs)


@pytest.mark.parametrize('kind', ['same_path', 'hardlink', 'symlink', 'inside_updater', 'different_bytes'])
def test_durable_copy_must_be_distinct_unaliased_same_bytes_outside_updater(inputs, kind):
    runtime, arguments = inputs
    source, copied = Path(arguments['updater_source']), Path(runtime['executable']['path'])
    if kind == 'same_path':
        runtime['executable']['path'] = str(source)
    elif kind in ('hardlink', 'symlink'):
        copied.unlink()
        os.link(source, copied) if kind == 'hardlink' else copied.symlink_to(source)
    elif kind == 'inside_updater':
        target = source.parent / 'other'
        copied.rename(target)
        runtime['executable']['path'] = str(target)
    else:
        copied.write_bytes(b'Different inert executable bytes')
        runtime['executable']['sha256'] = hashlib.sha256(copied.read_bytes()).hexdigest()
    with pytest.raises(ValueError):
        prepared(inputs)


def test_updater_changes_do_not_replace_registered_durable_bytes(inputs):
    runtime = prepared(inputs)
    source = Path(inputs[1]['updater_source'])
    source.write_bytes(b'New updater bytes, not the registered copy')
    assert subject.validate_prepared_runtime(runtime) == runtime
    source.unlink()
    assert subject.validate_prepared_runtime(runtime) == runtime
    Path(runtime['executable']['path']).write_bytes(b'Changed pinned copy')
    with pytest.raises(ValueError):
        subject.validate_prepared_runtime(runtime)


def test_saved_probe_changes_are_not_allowed(inputs):
    runtime = prepared(inputs)
    with Path(inputs[1]['probe_init_path']).open('a') as stream:
        stream.write('{"type":"result"}\n')
    with pytest.raises(ValueError, match='saved probe differs'):
        subject.validate_prepared_runtime(runtime)


@pytest.mark.parametrize('mutation', ['kind', 'version', 'extra', 'thinking', 'source_inode', 'probe_hash'])
def test_registered_basis_refuses_mutation(inputs, mutation):
    runtime = prepared(inputs)
    def change(basis):
        if mutation in ('kind', 'version'):
            basis[mutation] = 'unknown'
        elif mutation == 'extra':
            basis['extra'] = True
        elif mutation == 'thinking':
            basis['thinking']['declared'] = False
        elif mutation == 'source_inode':
            basis['durable_copy']['source']['inode'] = basis['durable_copy']['copy']['inode']
        else:
            basis['probe']['sha256'] = '0' * 64
    with pytest.raises(ValueError):
        subject.validate_prepared_runtime(mutate_basis(runtime, change))


def test_historical_basis_is_unchanged_but_never_satisfies_new_profile(inputs):
    runtime, _ = inputs
    assert historical.validate_runtime(runtime) == runtime
    assert subject.is_prepared_runtime(runtime) is False
    with pytest.raises(ValueError):
        subject.validate_prepared_runtime(runtime)
    recognized = prepared(inputs)
    recognized = mutate_basis(recognized, lambda b: b.update(version=2))
    assert subject.is_prepared_runtime(recognized) is True
    with pytest.raises(ValueError, match='unknown U4b'):
        subject.validate_prepared_runtime(recognized)


def test_malformed_or_duplicate_json_basis_cannot_select_historical_fallback(inputs):
    runtime, _ = inputs
    for raw in ('{"kind":', '{"kind":"one","kind":"two"}'):
        runtime['limits_basis'] = raw
        with pytest.raises(ValueError, match='ambiguous'):
            subject.is_prepared_runtime(runtime)


def test_saved_line_number_boolean_is_not_integer_identity(inputs):
    runtime = prepared(inputs)
    changed = mutate_basis(runtime, lambda basis: basis['probe'].update(init_line=True))
    with pytest.raises(ValueError, match='saved probe differs'):
        subject.validate_prepared_runtime(changed)


def test_observed_thinking_boolean_is_not_a_number(inputs):
    _, arguments = inputs
    path = Path(arguments['probe_init_path'])
    init = json.loads(path.read_text())
    init['thinking'] = {'enabled': True}
    path.write_text(json.dumps(init) + '\n')
    arguments['thinking_setting'] = {'enabled': 1}
    with pytest.raises(ValueError, match='observed thinking differs'):
        prepared(inputs)

