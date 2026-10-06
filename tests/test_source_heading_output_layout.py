"""Selected output identities are fixed before any count or SDK request."""
from dataclasses import replace
import json
from pathlib import Path

import pytest

from data_sheets_schema import api_runner as api, shared_generation as sg
from data_sheets_schema.cli import api as cli
from tests.test_evidence_generation_gate import specification
from tests.test_shared_generation_selection import registration_for, selected_spec as shared_v1
from tests.test_source_heading_runtime_api import draft_files, selected_spec


def _paths(spec):
    paths = {key: str(getattr(spec, key + '_path'))
             for key in ('full', 'core', 'report', 'provenance')}
    for value in paths.values():
        sg._path(value, 'completed selection path')
    return paths


def _forbid(*args, **kwargs):
    raise AssertionError('output selection must not execute or dispatch')


@pytest.fixture
def no_dispatch(monkeypatch):
    monkeypatch.setattr(api, 'execute', _forbid)
    monkeypatch.setattr(api, '_call_with_usage', _forbid)
    monkeypatch.setattr(api, '_call_with_retry', _forbid)


def _cli_spec(base, **kwargs):
    return cli._spec(project=base.project, arm='baseline', label=base.label,
                     condition=None, shared_generation_version=2,
                     shared_generation_registration=json.loads(base.shared_generation_registration)['registration_path'],
                     **kwargs)


def test_cli_default_identity_is_rooted_and_stable(tmp_path, draft_files, monkeypatch, no_dispatch):
    base = selected_spec(tmp_path, draft_files, cli_arm=True)
    launch = tmp_path / 'launch'; launch.mkdir()
    monkeypatch.chdir(launch)
    spec = _cli_spec(base)
    assert spec.out_dir is None and spec.manifest is None
    expected = launch / api.CONCAT_DIR
    assert spec.output_root == expected
    assert spec.full_path == expected / base.method / base.label / 'EXAMPLE_d4d.yaml'
    before = _paths(spec)
    elsewhere = tmp_path / 'elsewhere'; elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    assert _paths(spec) == before
    assert not expected.exists()


@pytest.mark.parametrize('kind', ['relative', 'absolute', 'relative_dotdot', 'absolute_dotdot', 'symlink_dotdot'])
def test_cli_explicit_output_is_normalized_before_calls(tmp_path, draft_files, monkeypatch, no_dispatch, kind):
    base = selected_spec(tmp_path, draft_files, cli_arm=True)
    launch = tmp_path / 'launch'; launch.mkdir()
    (launch / 'parent').mkdir()
    real = tmp_path / 'real'; real.mkdir(); (real / 'nested').mkdir()
    (launch / 'alias').symlink_to(real / 'nested', target_is_directory=True)
    monkeypatch.chdir(launch)
    choices = {'relative': Path('selected'), 'absolute': launch / 'selected',
               'relative_dotdot': Path('parent/../selected'),
               'absolute_dotdot': launch / 'parent/../selected',
               'symlink_dotdot': Path('alias/../selected')}
    supplied = choices[kind]
    expected = real / 'selected' if kind == 'symlink_dotdot' else launch / 'selected'
    spec = _cli_spec(base, out_dir=supplied)
    assert spec.out_dir == expected
    assert spec.full_path == expected / 'EXAMPLE_d4d.yaml'
    before = _paths(spec)
    monkeypatch.chdir(tmp_path)
    assert _paths(spec) == before
    assert not expected.exists()


@pytest.mark.parametrize('layout', ['conventional', 'external'])
def test_selected_default_uses_frozen_manifest_root(tmp_path, draft_files, monkeypatch, no_dispatch, layout):
    base = selected_spec(tmp_path, draft_files, source_naming={})
    root = tmp_path / 'corpus'; root.mkdir()
    manifest = root / ('data/preprocessed/source_manifest.yaml' if layout == 'conventional' else 'external.yaml')
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_bytes(base.manifest.read_bytes())
    reg = json.loads(base.shared_generation_registration)
    reg['inputs']['source_manifest'] = sg.file_pin(manifest)
    raw = sg.canonical(reg)
    Path(reg['registration_path']).write_bytes(raw)
    monkeypatch.chdir(root)
    spec = replace(base, out_dir=None, manifest=manifest,
                   manifest_line=api.RunSpec.__dataclass_fields__['manifest_line'].default,
                   shared_generation_registration=raw.decode())
    assert spec.output_root == root / api.CONCAT_DIR
    before = _paths(spec)
    monkeypatch.chdir(tmp_path)
    assert _paths(spec) == before
    assert not (root / api.CONCAT_DIR).exists()


@pytest.mark.parametrize('version', [0, 1])
def test_legacy_default_and_explicit_spellings_unchanged(tmp_path, monkeypatch, no_dispatch, version):
    base = specification(tmp_path)
    if version == 1:
        base = shared_v1(base, registration_for(base))
    monkeypatch.chdir(tmp_path)
    spec = replace(base, out_dir=None)
    assert spec.output_root == api.CONCAT_DIR
    assert not spec.full_path.is_absolute()
    (tmp_path / 'parent').mkdir()
    explicit = replace(base, out_dir=Path('parent/../legacy'))
    assert str(explicit.out_dir) == str(tmp_path / 'parent/../legacy')
    elsewhere = tmp_path / 'elsewhere'; elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    assert spec.output_root == tmp_path / api.CONCAT_DIR
