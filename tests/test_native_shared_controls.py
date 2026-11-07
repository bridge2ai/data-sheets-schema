"""C-only pure source projections; every oracle is offline and never launched."""
from copy import deepcopy
from pathlib import Path
import shlex
import sys
from types import MappingProxyType

import pytest

from data_sheets_schema import native_execution_authority_v2 as authority
from data_sheets_schema import native_shared_controls as controls
from data_sheets_schema import native_shared_controls_orchestration as orchestration
from tests.test_native_execution_authority_v2 import isolated_modules


def test_real_pinned_pure_projection_excludes_launchers_and_restores_aliases(isolated_modules):
    identity = authority.dependency_identity()
    old_path, old_meta = list(sys.path), list(sys.meta_path)
    with orchestration.loaded_controls(identity) as projected:
        assert set(projected) == {'native_command_policy', 'native_readonly',
            'native_phase_history', 'native_control', 'budgeted_cborg'}
        for name in ('run_native_canary', 'run_api_canary', 'prepare_registration_v2',
                     'run_direct_canary_awake', 'native_proxy'):
            with pytest.raises(KeyError):
                projected[name]
        for name in projected:
            module = sys.modules[name]
            pin = identity['base']['modules'][name]
            assert authority.module_source_identity(module) == {
                'name': name, 'path': str(authority.ROOT / pin['path']), 'sha256': pin['sha256']}
            assert module.__cached__ is None
            with pytest.raises(AttributeError):
                projected[name].main
        assert projected['native_readonly'].PROGRAMS == ('cat', 'grep', 'head', 'tail', 'wc', 'sed')
        assert issubclass(projected['budgeted_cborg'].BudgetStop, RuntimeError)
        guidance = projected['native_readonly'].lookup_guidance
        assert guidance()
        history = projected['native_control'].HISTORY_CONTRACT
        history['version'] = -1
        assert projected['native_control'].HISTORY_CONTRACT['version'] == 3
    with pytest.raises(ValueError, match='scope is closed'):
        guidance()
    assert sys.path == old_path and sys.meta_path == old_meta
    assert not isolated_modules.intersection(sys.modules)


def test_ordinary_classifier_matches_independent_pinned_oracle(isolated_modules, tmp_path):
    identity = authority.dependency_identity()
    python = sys.executable
    source = tmp_path / 'selected input.txt'
    output = tmp_path / 'outputs'
    policy = {'readonly_lookups': {'version': 1, 'repository': str(tmp_path),
        'inputs': [str(source)], 'output_directories': [str(output)]},
        'lookup_literal_admission': 1, 'programs': [{'code': 'print(1)', 'arguments': False}],
        'manifest_paths': []}
    commands = [shlex.join(['cat', str(source)]), shlex.join(['grep', '-n', 'word', str(source)]),
        shlex.join(['head', '-n', '2', str(source)]) + ' | wc -l',
        'cat /unregistered/path', 'cat "' + str(source) + '"',
        'cat ' + str(output / '*'), 'cat $(pwd)', 'cat /proc/1/environ',
        shlex.join([python, '-c', 'print(1)']), shlex.join([python, '-c', 'print(2)']),
        shlex.join([python, '-c', 'print(1)', '--help']),
        shlex.join([python, '-m', 'unregistered.module']), '', 'cat a; echo b']
    with orchestration.loaded_controls(identity) as projected:
        oracle = sys.modules['run_native_canary']
        pin = identity['base']['modules']['run_native_canary']
        assert authority.module_source_identity(oracle)['sha256'] == pin['sha256']
        expected = [oracle._classify_command(command, python, set(), policy) for command in commands]
        actual = [controls.classify_ordinary(command, python, set(), policy, projected)
                  for command in commands]
        assert actual == expected
        assert {row[0] for row in actual} == {'prescribed', 'not_prescribed'}


@pytest.mark.parametrize('change', ['function', 'nested_constant'])
def test_projection_refuses_mutated_helper_before_use(isolated_modules, change):
    identity = authority.dependency_identity()
    with orchestration.loaded_controls(identity) as projected:
        name = 'native_readonly' if change == 'function' else 'native_control'
        module = sys.modules[name]
        original = module.lookup_guidance if change == 'function' else deepcopy(module.HISTORY_CONTRACT)
        try:
            if change == 'function':
                module.lookup_guidance = lambda: 'foreign'
            else:
                module.HISTORY_CONTRACT['version'] = -1
            with pytest.raises(ValueError, match='identity or callable code changed|member changed'):
                controls.require_controls(projected)
        finally:
            if change == 'function':
                module.lookup_guidance = original
            else:
                module.HISTORY_CONTRACT.clear()
                module.HISTORY_CONTRACT.update(original)


def test_caller_module_map_cannot_replace_fixed_projection():
    with pytest.raises(ValueError, match='fixed pure-control projection'):
        controls.require_controls({'native_command_policy': object()})


def test_constructed_carrier_cannot_claim_loader_provenance(isolated_modules):
    with orchestration.loaded_controls() as projected:
        assert controls.require_controls(projected) is projected
        assert projected['native_readonly'].lookup_guidance()
        # Even an exact copy of the genuine mapping is a different lifetime.
        copied = controls._PureControls(dict(projected))
        with pytest.raises(ValueError, match='not minted by the active loader'):
            controls.require_controls(copied)
        with pytest.raises(ValueError, match='not minted by the active loader'):
            copied['native_readonly']
        class Forged:
            def _check(self):
                pass
        forged = controls._PureControls({name: Forged() for name in controls._MEMBERS})
        with pytest.raises(ValueError, match='not minted by the active loader'):
            controls.require_controls(forged)
    with pytest.raises(ValueError, match='not minted by the active loader'):
        controls.require_controls(projected)


@pytest.mark.parametrize('change', ['missing_module', 'extra_module', 'value_type',
    'replacement_projection', 'members', 'name', 'path', 'sha256'])
def test_minted_projection_requires_exact_rosters_and_source_pins(isolated_modules, change):
    with orchestration.loaded_controls() as projected:
        assert controls.require_controls(projected) is projected
        original_map = projected._modules
        member = projected['native_readonly']
        identity, values = dict(member._identity), dict(member._values)
        try:
            if change in ('missing_module', 'extra_module', 'value_type', 'replacement_projection'):
                altered = dict(original_map)
                if change == 'missing_module':
                    del altered['native_readonly']
                elif change == 'extra_module':
                    altered['run_native_canary'] = member
                elif change == 'value_type':
                    altered['native_readonly'] = object()
                else:
                    altered['native_readonly'] = controls._PureProjection(
                        member._module, member._identity, controls._MEMBERS['native_readonly'])
                projected._modules = MappingProxyType(altered)
            elif change == 'members':
                del member._values['lookup_command']
            else:
                member._identity[change] = {'name': 'native_control',
                    'path': '/foreign/native_readonly.py', 'sha256': '0' * 64}[change]
            with pytest.raises(ValueError, match='roster changed|projection changed|source pin changed'):
                controls.require_controls(projected)
        finally:
            projected._modules = original_map
            member._identity = identity
            member._values = values
        assert controls.require_controls(projected) is projected


def test_successful_helper_call_rechecks_midcall_member_mutation(isolated_modules):
    with orchestration.loaded_controls() as projected:
        grammar = projected['native_command_policy']
        literal_rule = grammar._literal_rule
        assert literal_rule('printf') == 'Bash(printf)'
        module = sys.modules['native_command_policy']
        original = module.POLICY_VERSION
        class MutatingText(str):
            def replace(self, *args, **kwargs):
                module.POLICY_VERSION = original + 1
                return super().replace(*args, **kwargs)
        try:
            with pytest.raises(ValueError, match='member changed: POLICY_VERSION'):
                literal_rule(MutatingText('printf'))
        finally:
            module.POLICY_VERSION = original
        assert literal_rule('printf') == 'Bash(printf)'
