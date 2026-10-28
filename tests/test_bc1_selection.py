"""BC1 selection/replay and UNAPPLIED hook simulation; never a launch proof.

The fixture compiles the exact proposed protected-source changes in memory.
Disk source and its identity remain unmodified: these tests exercise interface
composition, not installed-hook/source-attestation acceptance (Wave2, 2026-10-27).
"""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace

import pytest

import data_sheets_schema
from data_sheets_schema import api_runner as api, bc1_selection as bc
from data_sheets_schema import shared_generation as original_shared
from scripts.adhoc import make_bc1_shared_generation_patch_20261027 as proposal
from tests import test_shared_generation_selection as parent_tests
from tests.test_generation_manifest_identity import external  # noqa: F401


@pytest.fixture
def simulated_hooks(monkeypatch):
    """Execute proposal in memory if unapplied, or yield installed module directly."""
    path = Path(original_shared.__file__)
    before = path.read_bytes()
    if getattr(original_shared, 'BC1_HOOK_VERSION', None) == bc.VERSION:
        yield original_shared
        assert path.read_bytes() == before
        return
    name = original_shared.__name__
    shadow = ModuleType(name)
    shadow.__file__, shadow.__package__ = str(path), original_shared.__package__
    monkeypatch.setitem(sys.modules, name, shadow)
    monkeypatch.setattr(data_sheets_schema, 'shared_generation', shadow)
    exec(compile(proposal.proposed_source(before.decode()), str(path) + ' [BC1 simulation]', 'exec'), shadow.__dict__)
    for modname, module in tuple(sys.modules.items()):
        if modname.startswith('data_sheets_schema.') or modname == parent_tests.__name__:
            for key, value in tuple(vars(module).items()):
                if value is original_shared:
                    monkeypatch.setattr(module, key, shadow)
    yield shadow
    # Dynamic imports during the test must not leave simulated aliases behind
    # for the following legacy tests. Earlier aliases also restore to original.
    for modname, module in tuple(sys.modules.items()):
        if modname.startswith('data_sheets_schema.'):
            for key, value in tuple(vars(module).items()):
                if value is shadow:
                    setattr(module, key, original_shared)
    assert path.read_bytes() == before


@pytest.fixture
def registered(external, simulated_hooks):
    reg = parent_tests.registration_for(external)
    reg['bounded_carry'] = bc.registration_block(fan_in=2)
    limits = reg['audit_limits']
    limits.update(worker_output_tokens=64000, integration_output_tokens=64000)
    required = bc.allowances(limits['max_workers'], 2,
                            omission_output_tokens=limits['omission_output_tokens'])
    limits.update({k: required[k] for k in ('max_calls', 'aggregate_output_tokens')})
    raw = simulated_hooks.canonical(reg)
    Path(reg['registration_path']).write_bytes(raw)
    return replace(external, condition='generic_v10', render_version=25,
        shared_generation_version=1, shared_generation_registration=raw.decode(),
        bounded_carry_version=1, api_playbook_version=2, receipt_completion_version=2,
        receipt_completion_registration=simulated_hooks.canonical(reg['receipt']).decode(),
        provider=reg['runtime']['provider'])


def test_uninstalled_hook_refuses_before_generation(external, monkeypatch):
    monkeypatch.delattr(original_shared, 'BC1_HOOK_VERSION', raising=False)
    reg = parent_tests.registration_for(external)
    reg['bounded_carry'] = bc.registration_block()
    with pytest.raises(ValueError, match='hook is not installed'):
        replace(external, bounded_carry_version=1,
                shared_generation_registration=json.dumps(reg))


@pytest.mark.parametrize('flag', [True, False, '1', None, 2, -1])
def test_flag_is_a_strict_integer(external, flag):
    with pytest.raises(ValueError, match='integer 0 or 1'):
        replace(external, bounded_carry_version=flag)


def test_escaped_key_cannot_enable_a_mode_implicitly(external):
    raw = '{"bounded\\u005fcarry": {"version": 1}}'
    with pytest.raises(ValueError, match='selection differ'):
        replace(external, shared_generation_registration=raw)
    with pytest.raises(ValueError, match='selection differ'):
        replace(external, bounded_carry_version=1)


def test_simulated_hook_parser_and_replay_preserve_closed_selection(registered, simulated_hooks):
    recorded = registered.render_spec()
    assert recorded['bounded_carry']['contract'] == bc.contract_identity()
    assert registered.instruction.count(bc.PROCEDURE) == 1
    replay = api.RunSpec.from_render_spec(recorded, project=registered.project,
                                        method=registered.method, label=registered.label)
    assert replay.render_spec() == recorded
    for key, value in [('bounded_carry_extra', {}), ('bounded_carry_version', 0),
                       ('bounded_carry', {'version': 1})]:
        mutated = deepcopy(recorded)
        mutated[key] = value
        with pytest.raises(ValueError):
            api.RunSpec.from_render_spec(mutated, project=registered.project,
                                        method=registered.method, label=registered.label)
    reg = json.loads(registered.shared_generation_registration)
    reg['bounded_carry']['contract']['procedure_sha256'] = '0' * 64
    with pytest.raises(ValueError, match='identity differs'):
        simulated_hooks.parse_registration(simulated_hooks.canonical(reg))


@pytest.mark.parametrize('key', ['max_calls', 'aggregate_output_tokens'])
def test_missing_final_allowance_refuses(registered, simulated_hooks, key):
    reg = json.loads(registered.shared_generation_registration)
    reg['audit_limits'][key] -= 1
    with pytest.raises(ValueError, match='every registered worker, group and final'):
        simulated_hooks.parse_registration(simulated_hooks.canonical(reg))


@pytest.mark.parametrize('changes', [dict(runtime='Claude Code'), dict(shared_generation_version=2),
    dict(condition='generic_v9'), dict(api_playbook_version=1), dict(receipt_completion_version=1),
    dict(render_version=24)])
def test_other_parent_or_native_axes_refuse(registered, changes):
    with pytest.raises(ValueError):
        replace(registered, **changes)


def test_legacy_serialization_and_hook_parser_stay_unselected(external, simulated_hooks):
    reg = parent_tests.registration_for(external)
    raw = original_shared.canonical(reg)
    assert simulated_hooks.parse_registration(raw) == original_shared.parse_registration(raw)
    recorded = external.render_spec()
    assert not any(k.startswith('bounded_carry') for k in recorded)
    mutated = dict(recorded, bounded_carry_version=0)
    with pytest.raises(ValueError, match='historical specs omit BC1'):
        api.RunSpec.from_render_spec(mutated, project=external.project,
                                    method=external.method, label=external.label)


def test_proposal_is_exact_and_does_not_modify_protected_source():
    raw = Path(original_shared.__file__).read_bytes()
    expected = Path(proposal.ROOT / 'notes/bc1_shared_generation_patch_2026-10-27.diff').read_bytes()
    manifest = json.loads((proposal.ROOT / 'notes/bc1_shared_generation_patch_2026-10-27.json').read_bytes())
    assert manifest['proposal_sha256'] == hashlib.sha256(expected).hexdigest()
    if manifest['applied']:
        assert getattr(original_shared, 'BC1_HOOK_VERSION', None) == bc.VERSION
        assert manifest['proposed_source_sha256'] == hashlib.sha256(raw).hexdigest()
    else:
        assert proposal.proposal_bytes(raw) == expected
        assert manifest['base_sha256'] == hashlib.sha256(raw).hexdigest()
