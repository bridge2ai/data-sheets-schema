# Claude r3 copy (2026-11-02) of the Codex round-2 probe; unchanged except this line.
"""Independent PR #5213 round-2 probes, 2026-11-01.
Inputs: synthetic scratch corpus and unchanged fixtures; output: pytest evidence.
Run this same file against 0460 and 0fa; no checkout writes or providers.
"""
from dataclasses import make_dataclass, replace
import importlib
from pathlib import Path
from types import SimpleNamespace

from click.testing import CliRunner
import pytest
import yaml

from data_sheets_schema import api_runner as api, shared_generation as sg, runs
from data_sheets_schema.cli import cli
from tests.test_generation_manifest_identity import external  # noqa: F401
from tests.test_shared_generation_runtime import offline  # noqa: F401
from tests.test_source_heading_runtime_api import draft_files, client  # noqa: F401
from tests.test_manifest_corpus_root import project_tree  # noqa: F401
from tests.test_wave7_5213_d76_registration import _registered_at_root
from round2_binding_source import _tree
import round2_binding_source as classification
from round2_recorder_source import _render, _record


class SpendReached(BaseException):
    pass


def traps(spec, monkeypatch):
    fake = client(spec)
    seen = []
    def count(**kwargs):
        seen.append('count')
        raise SpendReached('count reached')
    def create(**kwargs):
        seen.append('create')
        raise SpendReached('create reached')
    monkeypatch.setattr(fake.messages, 'count_tokens', count)
    monkeypatch.setattr(fake.messages, 'create', create)
    monkeypatch.setattr(api, '_client', lambda: fake)
    return fake, seen


@pytest.mark.parametrize('field', ['bundle', 'manifest', 'chunk_manifest'])
@pytest.mark.parametrize('entry', ['execute-resume', 'execute-fresh', 'plan', 'dry-run', 'run', 'batch'])
def test_absolute_alias_mutation_precedes_authority_and_every_side_effect(
        tmp_path, draft_files, monkeypatch, field, entry):
    spec, reg = _registered_at_root(tmp_path, draft_files, monkeypatch, 'explicit')
    original = getattr(spec, field)
    alias = original.with_name('alias-' + original.name)
    alias.symlink_to(original)
    setattr(spec, field, alias)
    fake, seen = traps(spec, monkeypatch)
    authorities = []
    def forbidden(*args, **kwargs):
        authorities.append('authority/lock/date')
        raise AssertionError('later boundary reached before spelling refusal')
    monkeypatch.setattr(sg, 'assert_current', forbidden)
    monkeypatch.setattr(api, '_exclusive_run', forbidden)
    monkeypatch.setattr(api, '_restore_resume_date', forbidden)
    module = importlib.import_module('data_sheets_schema.cli.api')
    monkeypatch.setattr(module, '_spec', lambda *a, **k: spec)
    common = ['--shared-generation-version', '2', '--shared-generation-registration', reg['registration_path']]
    if entry == 'batch':
        roster = tmp_path / 'one-run-roster.json'
        roster.write_bytes(sg.canonical({'format': 'shared_generation_batch_roster_v1',
            'registrations': [{'project': spec.project, 'label': spec.label,
                               'registration_path': reg['registration_path']}]}))
        common[-1] = str(roster)
    before = _tree(tmp_path)
    result, error = None, None
    try:
        if entry == 'plan':
            api.plan(spec)
        elif entry in ('execute-resume', 'execute-fresh', 'dry-run'):
            api.execute(spec, client=fake, dry_run=entry == 'dry-run', resume=entry != 'execute-fresh')
        elif entry == 'run':
            result = CliRunner().invoke(cli, ['api', 'run', '--project', spec.project,
                '--label', spec.label, '--bundle', str(original), '--yes', *common])
        else:
            result = CliRunner().invoke(cli, ['api', 'batch', '--projects', spec.project,
                '--label-prefix', spec.label.removesuffix('_rep1'), '--replicates', '1',
                '--project-bundle', f"{spec.project}={reg['inputs']['bundle']['path']}",
                '--no-branch-guard', '--yes', *common])
    except BaseException as exc:
        error = exc
    assert not authorities and not seen, (authorities, seen, error, result)
    assert _tree(tmp_path) == before
    diagnostic = str(error) if result is None else result.output
    assert 'registered input spelling changed after construction' in diagnostic


@pytest.mark.parametrize('kind', ['empty', 'replaced'])
def test_private_anchor_replacement_cannot_restore_spend(tmp_path, draft_files, monkeypatch, kind):
    spec, reg = _registered_at_root(tmp_path, draft_files, monkeypatch, 'explicit')
    spec.bundle = Path(spec.bundle.name)
    spec._registered_input_spellings = () if kind == 'empty' else tuple(
        (name, str(getattr(spec, name))) for name in ('bundle', 'manifest', 'chunk_manifest'))
    fake, seen = traps(spec, monkeypatch)
    error = None
    try:
        api.execute(spec, client=fake)
    except BaseException as exc:
        error = exc
    assert not seen, (seen, repr(error))
    assert isinstance(error, ValueError), repr(error)


@pytest.mark.parametrize('all_selectors', [False, True])
def test_uncaptured_binding_selectors_cannot_disable_a_captured_anchor(
        tmp_path, draft_files, monkeypatch, all_selectors):
    spec, reg = _registered_at_root(tmp_path, draft_files, monkeypatch, 'explicit')
    spec.bundle = Path(spec.bundle.name)
    spec.shared_generation_version = 0
    if all_selectors:
        spec.shared_generation_registration = None
        spec.registered_input_paths = False
    fake, seen = traps(spec, monkeypatch)
    before = _tree(tmp_path)
    with pytest.raises(ValueError, match='registered input spelling changed after construction'):
        api.execute(spec, client=fake)
    assert not seen and _tree(tmp_path) == before


@pytest.mark.parametrize('field', ['new_registration', 'new_version'])
def test_new_dataclass_axis_breaks_the_actual_classification_test(monkeypatch, field):
    new_class = make_dataclass('FutureRunSpec', [(field, object, None)], bases=(api.RunSpec,))
    monkeypatch.setattr(api, 'RunSpec', new_class)
    with pytest.raises(AssertionError):
        classification.test_all_runspec_registration_and_version_axes_have_a_binding_classification()


def test_replace_revalidates_and_does_not_copy_cached_instruction_or_binding(external, monkeypatch):
    monkeypatch.chdir(external.bundle.parent)
    spec = replace(external, registered_input_paths=True)
    _ = spec.instruction
    relative = Path(spec.bundle.name)
    rebuilt = replace(spec, bundle=relative)
    assert rebuilt is not spec and rebuilt.bundle.is_absolute()
    assert rebuilt.bundle == spec.bundle
    assert 'instruction' in vars(spec) and 'instruction' not in vars(rebuilt)
    if hasattr(rebuilt, '_registered_input_spellings'):
        assert rebuilt._registered_input_spellings == spec._registered_input_spellings
        with pytest.raises(ValueError, match='init=False'):
            replace(spec, _registered_input_spellings=())
    recorded = {**external.render_spec(), 'registered_input_paths': True}
    replay = api.RunSpec.from_render_spec(recorded, project=external.project,
                                         method=external.method, label=external.label)
    assert replace(replay)._replay_only is True
    with pytest.raises(ValueError, match='historical prompt replay cannot execute'):
        api.execute(replace(replay))


@pytest.mark.parametrize('renderer', [19, 20, 21, 22, 23, 24, 27])
def test_historical_or_native_refusal_precedes_missing_binding(renderer):
    stub = SimpleNamespace(_replay_only=False, render_version=renderer,
                           native_source_attribution_version=int(renderer == 27))
    with pytest.raises(ValueError, match='renderer|native source attribution is offline-only'):
        api.execute(stub)


@pytest.mark.parametrize('same_bytes', [True, False])
def test_owner_counterpart_cannot_select_a_different_file(project_tree, monkeypatch, same_bytes):
    (root, nested, manifest, bundle, chunks, spec, original_spec, instruction,
     prompt, paths) = _render(project_tree, monkeypatch, 'nested', True)
    relative = bundle.relative_to(root)
    different = nested / relative
    different.parent.mkdir(parents=True)
    different.write_bytes(bundle.read_bytes() if same_bytes else b'DIFFERENT INPUT\n')
    assert different != bundle and different.is_file() and bundle.is_file()
    monkeypatch.chdir(nested)
    assert relative.absolute() == different
    result = _record(spec, prompt, manifest, relative, chunks, True)
    if result.exit_code == 0:
        record = yaml.safe_load(paths['provenance'].read_text())
        print('WRONG_FILE_ACCEPTED', {'selected_cli_file': str(different),
            'record_inputs': record['inputs'], 'render_bundle': record['prompts']['request']['spec']['bundle']})
        monkeypatch.chdir(root)
        print('VERIFY_REQUEST', runs.verify_request(spec.method, spec.label, spec.project))
    assert result.exit_code != 0, (result.output, result.exception)
    assert not paths['provenance'].exists()
