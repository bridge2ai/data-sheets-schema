"""D76 round 3: independent input bindings and ordered entry checks (#5213).

Synthetic registrations, local fixtures and immediate fake count/create traps;
no provider calls. Run unchanged at 0fa first, then the repaired source. Positive
compatibility controls are distinguished from failing-before regressions.
2026-11-02.
"""
import copy
from dataclasses import make_dataclass, replace
import importlib
import json
import os
from pathlib import Path

from click.testing import CliRunner
import pytest

from data_sheets_schema import api_runner as api, shared_generation as sg
from data_sheets_schema.cli import cli
from tests.test_generation_manifest_identity import external  # noqa: F401
from tests.test_shared_generation_runtime import offline  # noqa: F401
from tests.test_source_heading_runtime_api import draft_files  # noqa: F401
from tests.test_shared_generation_selection import registration_for, selected_spec
from tests.test_wave7_5213_d76_registration import _registered_at_root
from tests.test_wave7_5213_d76_round2_binding import _trap_client, _tree
import tests.test_wave7_5213_d76_round2_binding as classification


FIELDS = ('bundle', 'manifest', 'chunk_manifest')


def _bound(external, monkeypatch, *, shared=False):
    monkeypatch.chdir(external.bundle.parent)
    if shared:
        return selected_spec(external, registration_for(external))
    return replace(external, condition='generic_v8', registered_input_paths=True)


def _refuses_without_spend_or_write(spec, fake, reached, root, *, resume):
    before = _tree(root)
    error = None
    try:
        api.execute(spec, client=fake, resume=resume)
    except BaseException as exc:
        error = exc
    assert reached == {'count': [], 'create': []}, repr(error)
    assert _tree(root) == before
    assert isinstance(error, ValueError), repr(error)
    assert 'registered input' in str(error) or 'registration' in str(error)


@pytest.mark.parametrize('resume', [True, False])
@pytest.mark.parametrize('replacement', ['empty', 'replaced'])
def test_private_anchor_replacement_cannot_restore_spend(
        tmp_path, draft_files, monkeypatch, resume, replacement):
    spec, _ = _registered_at_root(tmp_path, draft_files, monkeypatch, 'explicit')
    fake, reached = _trap_client(spec, monkeypatch)
    spec.bundle = Path(spec.bundle.name)
    spec._registered_input_spellings = () if replacement == 'empty' else tuple(
        (name, None if getattr(spec, name) is None else os.fspath(getattr(spec, name)))
        for name in FIELDS)
    _refuses_without_spend_or_write(spec, fake, reached, tmp_path, resume=resume)


@pytest.mark.parametrize('resume', [True, False])
@pytest.mark.parametrize('replacement', ['missing', 'empty', 'equal-copy', 'wrong-roster'])
def test_invalid_private_mirror_refuses_even_without_public_path_changes(
        external, monkeypatch, resume, replacement):
    spec = _bound(external, monkeypatch)
    fake, reached = _trap_client(spec, monkeypatch)
    original = spec._registered_input_spellings
    mirrors = {'missing': None, 'empty': (), 'equal-copy': tuple(list(original)),
               'wrong-roster': tuple((name, value) for name, value in original if name != 'manifest')}
    spec._registered_input_spellings = mirrors[replacement]
    assert spec._registered_input_spellings is not original
    _refuses_without_spend_or_write(spec, fake, reached, external.bundle.parent, resume=resume)


@pytest.mark.parametrize('resume', [True, False])
@pytest.mark.parametrize('clear_anchor', [True, False])
def test_registered_status_cannot_be_demoted_by_mutation(
        external, monkeypatch, resume, clear_anchor):
    spec = _bound(external, monkeypatch)
    fake, reached = _trap_client(spec, monkeypatch)
    spec.registered_input_paths = False
    if clear_anchor:
        spec.bundle = Path(spec.bundle.name)
        spec._registered_input_spellings = None
    _refuses_without_spend_or_write(spec, fake, reached, external.bundle.parent, resume=resume)


class TwoFaced:
    def __init__(self, shown, actual):
        self.shown, self.actual = os.fspath(shown), os.fspath(actual)

    def __str__(self):
        return self.shown

    def __fspath__(self):
        return self.actual


class TwoFacedPath(type(Path())):
    def __str__(self):
        return self.shown

    def __fspath__(self):
        return self.actual


@pytest.mark.parametrize('resume', [True, False])
@pytest.mark.parametrize('shared', [True, False])
@pytest.mark.parametrize('kind', ['pathlike', 'path-subclass'])
def test_pathlike_string_cannot_hide_a_different_filesystem_locator(
        external, monkeypatch, resume, shared, kind):
    spec = _bound(external, monkeypatch, shared=shared)
    fake, reached = _trap_client(spec, monkeypatch)
    original = spec.bundle
    decoy = original.with_name('decoy-' + original.name)
    decoy.write_bytes(original.read_bytes() + b'\nDIFFERENT INPUT\n')
    if kind == 'pathlike':
        replacement = TwoFaced(original, decoy)
    else:
        replacement = TwoFacedPath(decoy)
        replacement.shown, replacement.actual = os.fspath(original), os.fspath(decoy)
    spec.bundle = replacement
    assert str(replacement) == os.fspath(original)
    assert os.fspath(replacement) == os.fspath(decoy)
    # The boundary must refuse before delegated shared authority, not merely
    # rely on that later authority discovering the two-faced object.
    authorities = []

    def forbidden(*args, **kwargs):
        authorities.append('authority')
        raise AssertionError('authority reached before input-type refusal')

    monkeypatch.setattr(sg, 'assert_current', forbidden)
    _refuses_without_spend_or_write(spec, fake, reached, external.bundle.parent, resume=resume)
    assert authorities == []


@pytest.mark.parametrize('field,pin', [('bundle', 'bundle'), ('manifest', 'source_manifest'),
                                      ('chunk_manifest', 'chunk_manifest')])
def test_shared_binding_checks_parsed_registration_paths_before_authority(
        external, monkeypatch, field, pin):
    spec = _bound(external, monkeypatch, shared=True)
    original = getattr(spec, field)
    alias = original.with_name('alias-' + original.name)
    alias.symlink_to(original)
    document = json.loads(spec.shared_generation_registration)
    document['inputs'][pin]['path'] = str(alias)
    spec.shared_generation_registration = sg.canonical(document).decode()
    reached = []

    def forbidden(*args, **kwargs):
        reached.append('authority')
        raise AssertionError('authority reached before registration-input refusal')

    monkeypatch.setattr(sg, 'assert_current', forbidden)
    before = _tree(external.bundle.parent)
    with pytest.raises(ValueError, match='registered input|registration'):
        api.plan(spec)
    assert reached == []
    assert _tree(external.bundle.parent) == before


@pytest.mark.parametrize('field', FIELDS)
@pytest.mark.parametrize('entry', ['batch', 'render'])
def test_cli_entry_refuses_mutation_before_authority_receipt_or_output(
        tmp_path, draft_files, monkeypatch, field, entry):
    spec, reg = _registered_at_root(tmp_path, draft_files, monkeypatch, 'explicit')
    original = getattr(spec, field)
    alias = original.with_name('alias-' + original.name)
    alias.symlink_to(original)
    fake, reached = _trap_client(spec, monkeypatch)
    setattr(spec, field, alias)
    module = importlib.import_module('data_sheets_schema.cli.api')
    monkeypatch.setattr(module, '_spec', lambda *args, **kwargs: spec)
    authorities = []

    def forbidden(*args, **kwargs):
        authorities.append('authority/receipt/lock/date')
        raise AssertionError('later check reached before input-integrity refusal')

    from data_sheets_schema import receipt_completion
    monkeypatch.setattr(sg, 'assert_current', forbidden)
    monkeypatch.setattr(receipt_completion, 'registration', forbidden)
    monkeypatch.setattr(api, '_exclusive_run', forbidden)
    monkeypatch.setattr(api, '_restore_resume_date', forbidden)
    common = ['--shared-generation-version', '2',
              '--shared-generation-registration', reg['registration_path']]
    output = tmp_path / 'must-not-render.txt'
    if entry == 'batch':
        roster = tmp_path / 'one-run-roster.json'
        roster.write_bytes(sg.canonical({'format': 'shared_generation_batch_roster_v1',
            'registrations': [{'project': spec.project, 'label': spec.label,
                               'registration_path': reg['registration_path']}]}))
        common[-1] = str(roster)
        args = ['api', 'batch', '--projects', spec.project,
                '--label-prefix', spec.label.removesuffix('_rep1'), '--replicates', '1',
                '--project-bundle', f"{spec.project}={reg['inputs']['bundle']['path']}",
                '--no-branch-guard', '--yes', *common]
    else:
        args = ['api', 'render-prompt', '--project', spec.project, '--label', spec.label,
                '--bundle', reg['inputs']['bundle']['path'], '--out', str(output), *common]
    before = _tree(tmp_path)
    result = CliRunner().invoke(cli, args)
    assert authorities == [], (authorities, result.output, result.exception)
    assert reached == {'count': [], 'create': []}
    assert not output.exists()
    assert _tree(tmp_path) == before
    assert result.exit_code != 0
    assert 'registered input spelling changed after construction' in result.output


@pytest.mark.parametrize('name', ['input_authority', 'registered_inputs_v2', 'pinned_input_manifest'])
def test_non_suffix_input_authority_field_breaks_the_actual_classification(monkeypatch, name):
    future = make_dataclass('FutureRunSpec', [(name, object, None)], bases=(api.RunSpec,))
    monkeypatch.setattr(classification.api, 'RunSpec', future)
    with pytest.raises(AssertionError):
        classification.test_all_runspec_registration_and_version_axes_have_a_binding_classification()


def test_library_prompt_render_checks_binding_before_shared_capture(external, monkeypatch):
    spec = _bound(external, monkeypatch, shared=True)
    original = spec.bundle
    alias = original.with_name('render-alias-' + original.name)
    alias.symlink_to(original)
    spec.bundle = alias
    authorities = []

    def forbidden(*args, **kwargs):
        authorities.append('capture')
        raise AssertionError('shared capture reached before input-integrity refusal')

    monkeypatch.setattr(sg, 'capture', forbidden)
    before = _tree(external.bundle.parent)
    with pytest.raises(ValueError, match='registered input spelling changed after construction'):
        api.resolve_prompt(spec)
    assert authorities == []
    assert _tree(external.bundle.parent) == before


# Compatibility controls: these pass before the repair and must keep passing.
@pytest.mark.parametrize('as_strings', [False, True])
def test_untouched_exact_path_types_keep_the_original_literal_binding(external, monkeypatch, as_strings):
    spec = _bound(external, monkeypatch)
    if as_strings:
        for name in FIELDS:
            value = getattr(spec, name)
            setattr(spec, name, None if value is None else os.fspath(value))
    assert api._require_registered_input_spellings(spec) is None


def test_replace_constructs_a_new_binding_without_copying_cached_instruction(external, monkeypatch):
    spec = _bound(external, monkeypatch)
    original_instruction = spec.instruction
    rebuilt = replace(spec, bundle=Path(spec.bundle.name))
    assert rebuilt is not spec and rebuilt.bundle == spec.bundle
    assert 'instruction' not in vars(rebuilt)
    assert api._require_registered_input_spellings(rebuilt) is None
    assert rebuilt.instruction == original_instruction


@pytest.mark.parametrize('mutated', [False, True])
def test_shallow_copy_preserves_binding_without_recapturing_mutated_fields(external, monkeypatch, mutated):
    spec = _bound(external, monkeypatch)
    if mutated:
        spec.bundle = Path(spec.bundle.name)
    copied = copy.copy(spec)
    if mutated:
        with pytest.raises(ValueError, match='registered input spelling changed after construction'):
            api._require_registered_input_spellings(copied)
    else:
        assert api._require_registered_input_spellings(copied) is None
