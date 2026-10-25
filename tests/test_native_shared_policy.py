"""Actual selected helpers composed with the restrictive pure stage overlay."""
from copy import deepcopy
from dataclasses import replace

import pytest
from tests.test_native_shared_controller import bound, native_spec, declaration
from tests.test_native_shared_effects import view
from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_effects as effects
from data_sheets_schema import native_shared_policy as policy


@pytest.fixture
def selected(bound):
    spec, _, instruction = bound
    commands = policy.command_policy(spec, str(instruction))
    cap = spec._native_shared_generation_capture
    stage = replace(view(), stage_root=cap.role('stage_root'),
        protected_roles=c.role_paths(cap.registration.pin.path, cap.role('stage_root')),
        stage_command=commands['native_shared_helpers']['advance'],
        static_policy_sha256=c.sha(c.canonical(commands)), state='assembly_complete',
        cursor=None, request=None, response=None, sealed=())
    return commands, stage


def route(selected, name, payload):
    commands, stage = selected
    return policy.stage_overlay_governs(stage, tool_name=name, tool_input=payload, policy=commands)


@pytest.mark.parametrize('name', sorted(policy.HELPERS))
def test_selected_helpers_use_command_policy_and_advance_retains_stage_checks(selected, name):
    commands, stage = selected
    command = commands['native_shared_helpers'][name]
    assert policy.classify_bash(command, commands['python'], set(), commands)[0] == 'prescribed'
    assert route(selected, 'Bash', {'command': command}) is (name == 'advance')
    if name == 'advance':
        assert effects.classify_effect(stage, tool_name='Bash', tool_input={'command': command})[0] == 'prescribed'
        assert effects.classify_effect(stage, tool_name='Bash',
            tool_input={'command': command, 'run_in_background': True})[0] == 'not_prescribed'


@pytest.mark.parametrize('name', ['original_source_inventory', 'audit_evidence', 'final_evidence'])
@pytest.mark.parametrize('suffix', [' --unregistered', ' > {root}/unregistered', '; cat {root}/journal.json'])
def test_modified_stage_reading_helpers_cannot_bypass_overlay(selected, name, suffix):
    commands, stage = selected
    command = commands['native_shared_helpers'][name] + suffix.format(root=stage.stage_root)
    payload = {'command': command}
    assert route(selected, 'Bash', payload) is True
    assert effects.classify_effect(stage, tool_name='Bash', tool_input=payload)[0] == 'not_prescribed'
    assert policy.classify_bash(command, commands['python'], set(), commands)[0] == 'not_prescribed'


@pytest.mark.parametrize('tool,relative', [('Read', 'requests/000002.json'),
    ('Write', 'sealed/full.yaml'), ('Write', 'outputs/audit.json'), ('Write', 'journal.json')])
def test_helper_routing_does_not_widen_stage_file_access(selected, tool, relative):
    _, stage = selected
    payload = {'file_path': stage.stage_root + '/' + relative}
    if tool == 'Write':
        payload['content'] = 'changed'
    assert route(selected, tool, payload) is True
    assert effects.classify_effect(stage, tool_name=tool, tool_input=payload)[0] == 'not_prescribed'


@pytest.mark.parametrize('changed', ['policy', 'view'])
def test_helper_exception_requires_exact_policy_and_valid_view(selected, changed):
    commands, stage = selected
    if changed == 'policy':
        commands = deepcopy(commands)
        commands['readonly_lookups']['inputs'].append('/another/authority')
    else:
        stage = replace(stage, protected_roles=())
    with pytest.raises(ValueError):
        policy.stage_overlay_governs(stage, tool_name='Bash',
            tool_input={'command': commands['native_shared_helpers']['audit_evidence']}, policy=commands)
