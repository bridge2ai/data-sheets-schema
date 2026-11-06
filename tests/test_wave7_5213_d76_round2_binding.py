"""D76 round 2: bound inputs refuse mutation before admission, PR #5213.

Inputs are synthetic registrations and local fixtures; outputs are pytest
assertions only. Fake count/create endpoints abort immediately if reached.
These regressions retain the real CLI planning, authority and execution gates.
2026-11-01.
"""
from dataclasses import fields, replace
import importlib
from pathlib import Path

from click.testing import CliRunner
import pytest

from data_sheets_schema import api_runner as api, provenance, shared_generation as sg
from data_sheets_schema import receipt_completion_policy
from data_sheets_schema.cli import cli
from tests.test_generation_manifest_identity import external  # noqa: F401
from tests.test_receipt_completion_runtime import registration as receipt_registration
from tests.test_shared_generation_runtime import offline  # noqa: F401
from tests.test_source_heading_runtime_api import draft_files, client  # noqa: F401
from tests.test_wave7_5213_d76_registration import _registered_at_root


class SpendReached(BaseException):
    """Stop baseline execution without retries, accounting recovery or spend."""


def _tree(root):
    """Include directory creation, file contents and symlinks, including hidden files."""
    result = {}
    for path in root.rglob('*'):
        key = str(path.relative_to(root))
        result[key] = ('symlink', str(path.readlink())) if path.is_symlink() else (
            ('directory', None) if path.is_dir() else ('file', path.read_bytes()))
    return result


def _trap_client(spec, monkeypatch):
    fake = client(spec)
    reached = {'count': [], 'create': []}

    def count(**kwargs):
        reached['count'].append(kwargs)
        raise SpendReached('registered input mutation reached count_tokens')

    def create(**kwargs):
        reached['create'].append(kwargs)
        raise SpendReached('registered input mutation reached create')

    monkeypatch.setattr(fake.messages, 'count_tokens', count)
    monkeypatch.setattr(fake.messages, 'create', create)
    monkeypatch.setattr(api, '_client', lambda: fake)
    return fake, reached


@pytest.mark.parametrize('field', ['bundle', 'manifest', 'chunk_manifest'])
@pytest.mark.parametrize('entry', ['execute-resume', 'execute-fresh', 'run', 'batch'])
def test_bound_spelling_mutation_refuses_before_any_spend_or_write(
        tmp_path, draft_files, monkeypatch, field, entry):
    spec, reg = _registered_at_root(tmp_path, draft_files, monkeypatch, 'explicit')
    original = getattr(spec, field)
    frozen_instruction = spec.instruction
    setattr(spec, field, original.relative_to(tmp_path))
    assert getattr(spec, field).absolute() == original
    assert getattr(spec, field).read_bytes() == original.read_bytes()
    fake, reached = _trap_client(spec, monkeypatch)
    module = importlib.import_module('data_sheets_schema.cli.api')
    # Model a caller handing the actual CLI a spec mutated after construction.
    # Do not stub plan(), assert_current(), locks, execute() or any input guard.
    monkeypatch.setattr(module, '_spec', lambda *args, **kwargs: spec)
    common = ['--shared-generation-version', '2',
              '--shared-generation-registration', reg['registration_path']]
    if entry == 'batch':
        roster = tmp_path / 'one-run-roster.json'
        roster.write_bytes(sg.canonical({'format': 'shared_generation_batch_roster_v1',
            'registrations': [{'project': spec.project, 'label': spec.label,
                               'registration_path': reg['registration_path']}]}))
        common[-1] = str(roster)
    before = _tree(tmp_path)
    error = None
    result = None
    try:
        if entry.startswith('execute-'):
            api.execute(spec, resume=entry == 'execute-resume', client=fake)
        elif entry == 'run':
            result = CliRunner().invoke(cli, ['api', 'run', '--project', spec.project,
                '--label', spec.label, '--bundle', str(Path(reg['inputs']['bundle']['path'])),
                '--yes', *common])
        else:
            assert spec.label.endswith('_rep1')
            result = CliRunner().invoke(cli, ['api', 'batch', '--projects', spec.project,
                '--label-prefix', spec.label.removesuffix('_rep1'), '--replicates', '1',
                '--project-bundle', f"{spec.project}={reg['inputs']['bundle']['path']}",
                '--no-branch-guard', '--yes', *common])
    except BaseException as exc:
        error = exc
    assert reached == {'count': [], 'create': []}, f'{entry} reached a spend endpoint: {error!r}'
    assert _tree(tmp_path) == before, f'{entry} wrote artifacts before refusing a bound input'
    if result is None:
        assert isinstance(error, ValueError), repr(error)
        diagnostic = str(error)
    else:
        assert result.exit_code != 0, result.output
        diagnostic = result.output
    assert 'registered input spelling changed after construction' in diagnostic
    assert field in diagnostic
    # Refusal must not normalize the path or invalidate/re-render a cached instruction.
    assert getattr(spec, field) == original.relative_to(tmp_path)
    assert spec.instruction == frozen_instruction


@pytest.mark.parametrize('field', ['bundle', 'manifest', 'chunk_manifest'])
def test_explicit_binding_cannot_be_disabled_after_mutating_a_locator(external, monkeypatch, field):
    monkeypatch.chdir(external.bundle.parent)
    spec = replace(external, registered_input_paths=True)
    original = getattr(spec, field)
    frozen_instruction = spec.instruction
    setattr(spec, field, Path(original.name))
    spec.registered_input_paths = False
    fake, reached = _trap_client(spec, monkeypatch)
    before = _tree(external.bundle.parent)
    with pytest.raises(ValueError, match='registered input spelling changed after construction'):
        api.execute(spec, client=fake)
    assert reached == {'count': [], 'create': []}
    assert _tree(external.bundle.parent) == before
    assert getattr(spec, field) == Path(original.name)
    assert spec.instruction == frozen_instruction


# Every version/registration axis needs an explicit input-authority disposition.
# A newly introduced field fails this closed roster until its behavior is reviewed.
REGISTRATION_AXES = {
    'native_shared_generation_version': ('native capture pins inputs independently; the legacy provenance predicate does not select it',
                                         {'native_shared_generation_version': 1}, False),
    'native_shared_generation_registration': ('native capture validates its own input registration; not a legacy provenance selector',
                                              {'native_shared_generation_version': 1, 'native_shared_generation_registration': '{}'}, False),
    'render_version': ('not input-pinning: prompt renderer only', {'render_version': 27}, False),
    'api_playbook_version': ('not input-pinning: enclosing shared-generation selection owns inputs',
                             {'api_playbook_version': 3}, False),
    'bounded_carry_version': ('not input-pinning: BC1 requires shared generation 1, whose registration owns inputs',
                             {'bounded_carry_version': 1}, False),
    'removal_repair_version': ('not input-pinning: restore-only procedure axis',
                              {'removal_repair_version': 1}, False),
    'native_source_attribution_version': ('input-pinning: native attribution prepares registration',
                                         {'native_source_attribution_version': 1}, True),
    'shared_generation_version': ('input-pinning with captured registration',
                                  {'shared_generation_version': 1, 'shared_generation_registration': '{}'}, True),
    'shared_generation_registration': ('input-pinning with nonzero shared-generation selection',
                                       {'shared_generation_version': 1, 'shared_generation_registration': '{}'}, True),
    'receipt_completion_version': ('standalone v1 not input-pinning: receipt_completion_policy.py:69 closed keys',
                                   {'receipt_completion_version': 1, 'receipt_completion_registration': '{}'}, False),
    'receipt_completion_registration': ('standalone v1 not input-pinning: receipt_completion_policy.py:69 closed keys',
                                        {'receipt_completion_version': 1, 'receipt_completion_registration': '{}'}, False),
}


# Every dataclass field is reviewed, regardless of its name. True identifies an
# input locator, a registration selector or retained input identity; it does not
# mean that the field alone grants execution authority.
RUNSPEC_FIELDS = {
    'native_shared_generation_version': (True, 'native captured-input registration selector'),
    'native_shared_generation_registration': (True, 'native registration binds declared input paths and bytes'),
    '_native_shared_generation_capture': (True, 'immutable captured native input authority'),
    '_native_shared_generation_metadata': (True, 'recorded native input identities for non-executing replay'),
    '_native_shared_runtime_capture': (False, 'runtime declaration, not source-input authority'),
    '_native_shared_max_draft_checks': (False, 'draft-check limit, not source-input authority'),
    'project': (False, 'dataset identifier; a shared registration independently binds it'),
    'arm': (False, 'display/method selection, not an input registration'),
    'method': (False, 'output and runtime method, not input authority'),
    'bundle': (True, 'the selected factual input locator'),
    'label': (False, 'run/output identifier, not an input registration'),
    'condition': (False, 'procedure selection; registration axes own input authority'),
    'condition_stated': (False, 'records whether the caller chose the condition'),
    'condition_mismatch_allowed': (False, 'label/condition policy, not input authority'),
    'manifest_line': (False, 'rendered header; the manifest locator supplies the input'),
    'manifest': (True, 'selected source-manifest locator or explicit absence'),
    'chunk_manifest': (True, 'selected chunk mapping locator or explicit absence'),
    'profile': (False, 'profile selection is independently pinned by shared registration'),
    'profile_basis': (False, 'explanation of profile selection, not authority'),
    'render_version': (False, 'historical renderer/procedure version only'),
    'run_date': (False, 'frozen display date, not input authority'),
    'out_dir': (False, 'output destination, not an input registration'),
    'runtime': (False, 'execution runtime declaration'),
    'provider': (False, 'provider declaration, not input authority'),
    'reasoning_effort': (False, 'model invocation parameter'),
    'prompt_text_env': (False, 'recorder command syntax, not input authority'),
    'api_playbook_version': (False, 'enclosing shared selection owns the input registration'),
    'bounded_carry_version': (False, 'BC1 mode/contract selector; enclosing shared-generation 1 registration owns input paths'),
    'native_source_attribution_version': (True, 'native attribution input registration selector'),
    'native_source_attribution_max_checks': (False, 'native observation limit, not input identity'),
    'removal_repair_version': (False, 'restore-only procedure axis'),
    'receipt_completion_version': (False, 'v1 pins policy; v2/v3 inherit shared input authority'),
    'receipt_completion_registration': (False, 'standalone receipt policy/limits, not input pins'),
    'shared_generation_version': (True, 'input registration selector when registration is present'),
    'shared_generation_registration': (True, 'parsed registration pins the shared input paths'),
    'registered_input_paths': (True, 'explicit binding for older registration constructors'),
    '_registered_input_spellings': (True, 'input identity mirror; independent registry is authoritative'),
    '_shared_generation_capture': (True, 'captured shared input/authority bytes'),
    '_replay_only': (False, 'literal historical inspection; execution is refused'),
    '_automatic_run_date': (False, 'implicit-clock recovery marker'),
    '_agentic_artifact_paths': (False, 'frozen output destinations'),
    '_agentic_toolchain': (False, 'agent toolchain identity, not source-input registration'),
    '_chunk_check_uses_manifest': (False, 'chunk validation discovery flag, not a pinned locator'),
    '_corpus_root': (False, 'corpus/output owner; does not itself bind registered input identity'),
    '_api_header_values': (False, 'frozen model/provider header values'),
}


def test_all_runspec_registration_and_version_axes_have_a_binding_classification():
    names = {field.name for field in fields(api.RunSpec)}
    assert names == set(RUNSPEC_FIELDS)
    for name, (input_pinning, reason) in RUNSPEC_FIELDS.items():
        assert type(input_pinning) is bool and reason, name
    axes = {name for name in names if name.endswith(('_registration', '_version'))}
    assert axes == set(REGISTRATION_AXES)
    for name, (reason, selection, expected) in REGISTRATION_AXES.items():
        assert reason
        assert provenance.registered_input_paths(selection) is expected, name


@pytest.mark.parametrize('version', [-1, 1, 2, 3, 99])
@pytest.mark.parametrize('mechanism', ['shared_generation', 'native_source_attribution'])
def test_registration_spelling_policy_is_version_agnostic(mechanism, version):
    selection = {mechanism + '_version': version}
    if mechanism == 'shared_generation':
        selection['shared_generation_registration'] = '{}'
    assert provenance.registered_input_paths(selection) is True


@pytest.mark.parametrize('version', [0, False, True, None, '1', 1.0])
@pytest.mark.parametrize('mechanism', ['shared_generation', 'native_source_attribution'])
def test_invalid_or_disabled_versions_do_not_select_a_binding(mechanism, version):
    selection = {mechanism + '_version': version}
    if mechanism == 'shared_generation':
        selection['shared_generation_registration'] = '{}'
    assert provenance.registered_input_paths(selection) is False


def test_shared_generation_requires_registration_to_select_binding():
    assert provenance.registered_input_paths({'shared_generation_version': 3}) is False
    assert provenance.registered_input_paths({
        'shared_generation_version': 3, 'shared_generation_registration': None}) is False


def test_standalone_receipt_registration_has_no_input_authority():
    raw = receipt_registration().encode()
    parsed = receipt_completion_policy.parse_registration(raw)
    assert set(parsed) == {'format', 'registration_id', 'condition', 'runtime_policy_sha256',
        'receipt_instrument_version', 'max_output_tokens', 'max_request_bytes',
        'context_limit_tokens', 'context_limit_basis', 'coverage_floor'}
    assert provenance.registered_input_paths({
        'receipt_completion_version': 1, 'receipt_completion_registration': raw.decode()}) is False
    for shared_version, receipt_version in ((1, 2), (2, 3)):
        assert provenance.registered_input_paths({'shared_generation_version': shared_version,
            'shared_generation_registration': '{}', 'receipt_completion_version': receipt_version,
            'receipt_completion_registration': '{}'}) is True


def test_literal_historical_replay_stays_literal_and_cannot_execute(external, monkeypatch):
    monkeypatch.chdir(external.bundle.parent)
    unregistered = replace(external)
    recorded = {**unregistered.render_spec(), 'registered_input_paths': True}
    replay = api.RunSpec.from_render_spec(recorded, project=unregistered.project,
        method=unregistered.method, label=unregistered.label)
    assert replay.render_spec() == recorded
    assert not replay.bundle.is_absolute()
    before = _tree(external.bundle.parent)
    with pytest.raises(ValueError, match='historical prompt replay cannot execute'):
        api.execute(replay)
    assert _tree(external.bundle.parent) == before
    assert replay.render_spec() == recorded


@pytest.mark.parametrize('field', ['bundle', 'manifest', 'chunk_manifest'])
@pytest.mark.parametrize('change', ['missing', 'absolute-alias'])
def test_bound_locator_removal_or_alias_requires_fresh_construction(external, monkeypatch, field, change):
    monkeypatch.chdir(external.bundle.parent)
    spec = replace(external, registered_input_paths=True)
    original = getattr(spec, field)
    if change == 'absolute-alias':
        alias = original.with_name('alias-' + original.name)
        alias.symlink_to(original)
        replacement = alias
        assert alias.read_bytes() == original.read_bytes()
    else:
        replacement = None
    setattr(spec, field, replacement)
    fake, reached = _trap_client(spec, monkeypatch)
    before = _tree(external.bundle.parent)
    with pytest.raises(ValueError, match='registered input spelling changed after construction'):
        api.execute(spec, client=fake)
    assert reached == {'count': [], 'create': []}
    assert _tree(external.bundle.parent) == before
    assert getattr(spec, field) == replacement
