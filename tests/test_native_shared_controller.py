"""Offline selection/composition, never native/auth/provider execution."""
from copy import deepcopy
from pathlib import Path
import shlex
import subprocess

import pytest

from tests.test_native_shared_selection import declaration
from tests.test_native_shared_render import native_spec
from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_controller as controller
from data_sheets_schema import native_shared_policy as policy
from data_sheets_schema import native_shared_render as render
from data_sheets_schema import native_execution_registration as runtime_registration


@pytest.fixture
def bound(native_spec, tmp_path, monkeypatch):
    binary = tmp_path.resolve() / 'declared-never-invoked'
    binary.write_bytes(b'#!/bin/sh\nexit 99\n')
    binary.chmod(0o700)
    runtime = c.strict_json(native_spec._native_shared_runtime_capture.raw)
    runtime['executable'].update(path=str(binary), sha256=c.sha(binary.read_bytes()))
    runtime['auth'] = {'loggedIn': True, 'authMethod': 'claude.ai', 'apiProvider': 'firstParty',
        'subscriptionType': 'synthetic-software-test', 'expected_api_key_source': 'none'}
    runtime['environment'] = {'PATH': '/usr/bin:/bin', 'HOME': str(tmp_path.resolve()),
        'CLAUDE_SECURESTORAGE_CONFIG_DIR': '', 'CLAUDE_CODE_DISABLE_1M_CONTEXT': '1'}
    path = tmp_path.resolve() / 'selected-runtime.json'
    path.write_bytes(c.canonical(runtime))
    native_spec._native_shared_runtime_capture = None
    native_spec._native_shared_max_draft_checks = None
    def forbidden(*a, **k): pytest.fail('offline binding invoked a process')
    monkeypatch.setattr(subprocess, 'run', forbidden)
    monkeypatch.setattr(subprocess, 'Popen', forbidden)
    monkeypatch.setattr(subprocess, 'check_output', forbidden)
    assert controller.bind_runtime(native_spec, path, 3) is native_spec
    instruction = tmp_path.resolve() / 'instruction.md'
    instruction.write_bytes(native_spec.instruction.encode('utf-8'))
    return native_spec, path, instruction


def test_real_offline_composition_roundtrip_and_policy(bound):
    spec, runtime, instruction = bound
    value = controller.compose(spec, runtime_path=runtime, instruction_path=instruction, max_draft_checks=3)
    assert controller.verified_composition(c.canonical(value)) == value
    assert value['max_draft_checks'] == value['render_spec']['native_shared_max_draft_checks'] == 3
    assert value['runtime_raw_json'].encode() == runtime.read_bytes()
    commands = render.commands(spec)
    assert set(value['policy']['native_shared_helpers']) == policy.HELPERS
    for argv in commands.values():
        assert policy.classify_bash(shlex.join(argv), value['policy']['python'], set(), value['policy'])[0] == 'prescribed'
    assert spec._native_shared_generation_capture.role('stage_root') in value['policy']['readonly_lookups']['output_directories']
    assert 'write_paths' not in value['policy']['readonly_lookups']
    for cap in spec._native_shared_generation_capture.authority:
        assert cap.pin.path in value['policy']['readonly_lookups']['inputs']


@pytest.mark.parametrize('name', sorted(policy.HELPERS))
def test_changed_helper_arguments_cannot_fall_through_to_old_classifier(bound, name):
    spec, _, instruction = bound
    actual = policy.command_policy(spec, str(instruction))
    command = actual['native_shared_helpers'][name] + ' --unregistered'
    assert policy.classify_bash(command, actual['python'], set(), actual)[0] == 'not_prescribed'


def test_preserves_actual_readonly_shell_grammar(bound):
    spec, _, instruction = bound
    actual = policy.command_policy(spec, str(instruction))
    for command, expected in [(shlex.join(['cat', str(spec.bundle)]), 'prescribed'),
                              ('cat /unregistered/path', 'not_prescribed'),
                              (shlex.join([actual['python'], '-c', 'print(1)']), 'not_prescribed')]:
        assert policy.classify_bash(command, actual['python'], set(), actual)[0] == expected


@pytest.mark.parametrize('mutation', ['provider', 'effort', 'binary', 'bool', 'rebind', 'instruction', 'policy'])
def test_offline_identity_and_allowance_refusals(bound, mutation):
    spec, runtime, instruction = bound
    if mutation in {'provider', 'effort', 'binary'}:
        raw = c.strict_json(runtime.read_bytes())
        if mutation == 'binary': raw['executable']['sha256'] = '0' * 64
        else: raw[mutation] = 'another'
        runtime.write_bytes(c.canonical(raw))
    elif mutation == 'instruction': instruction.write_bytes(instruction.read_bytes() + b'\n')
    if mutation == 'policy':
        value = controller.compose(spec, runtime_path=runtime, instruction_path=instruction, max_draft_checks=3)
        value['policy']['native_shared_helpers']['draft'] += ' --unknown'
        value['policy_sha256'] = c.sha(c.canonical(value['policy']))
        with pytest.raises(ValueError): controller.verified_composition(c.canonical(value))
    else:
        with pytest.raises(ValueError):
            controller.compose(spec, runtime_path=runtime, instruction_path=instruction,
                               max_draft_checks=True if mutation == 'bool' else 4 if mutation == 'rebind' else 3)
