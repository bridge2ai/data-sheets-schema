"""PR #5213 independent recorder probes, 2026-11-02.
Inputs: synthetic corpus and exact rendered instructions, at both pinned heads.
Outputs: scratch-only records; no provider or network. Retain failing-before evidence.
"""
import hashlib
from pathlib import Path
import unicodedata

import pytest
import yaml
from click.testing import CliRunner
from data_sheets_schema.cli import cli
from data_sheets_schema.resources import resource_path
from tests.test_manifest_corpus_root import project_tree  # noqa: F401
from round2_recorder_source import _render, _record


def command(spec, manifest, bundle, chunks, prompt=None, condition=True):
    return ['provenance', 'record', '--project', spec.project, '--method', spec.method,
            '--label', spec.label, '--manifest', str(manifest), '--input-bundle', str(bundle),
            '--chunk-manifest', str(chunks), '--runtime', spec.runtime, '--provider', 'offline',
            *(['--condition', spec.condition, '--run-date', spec.run_date] if condition else []),
            *(['--prompt-text', str(prompt)] if prompt else []),
            *[arg for path in spec.prompt_files for arg in ('--prompt', str(resource_path(path)))]]


@pytest.mark.parametrize('same_bytes', [True, False])
def test_explicit_rendering_bundle_cannot_hide_a_different_recorded_input(project_tree, monkeypatch, same_bytes):
    root, _, manifest, bundle, chunks, spec, _, _, prompt, paths = _render(project_tree, monkeypatch, 'nested', True)
    other = root / ('other-' + bundle.name)
    other.write_bytes(bundle.read_bytes() if same_bytes else b'different selected bytes\n')
    monkeypatch.chdir(root)
    result = CliRunner().invoke(cli, command(spec, manifest, other, chunks, prompt)
                               + ['--bundle-for-spec', str(bundle)])
    assert result.exit_code != 0, result.output
    assert not paths['provenance'].exists()


@pytest.mark.parametrize('render_cwd', ['root', 'nested'])
@pytest.mark.parametrize('condition', [False, True])
def test_no_supplied_instruction_never_verifies_consumption(project_tree, monkeypatch, render_cwd, condition):
    root, _, manifest, bundle, chunks, spec, _, _, _, paths = _render(project_tree, monkeypatch, render_cwd, True)
    monkeypatch.chdir(root)
    result = CliRunner().invoke(cli, command(spec, manifest, bundle, chunks, condition=condition))
    assert result.exit_code == 0, (result.output, result.exception)
    record = yaml.safe_load(paths['provenance'].read_text())
    assert record['inputs']['bundle_md5'] == hashlib.md5(bundle.read_bytes()).hexdigest()
    assert 'asserted' in record['inputs']['hash_basis']
    assert any(row['field'] == 'inputs.bundle_md5' and 'consumed' in row['reason'] for row in record['unverified'])


@pytest.mark.parametrize('alias', ['dotdot', 'case', 'unicode'])
def test_shadow_alias_cannot_promote_an_owner_file(project_tree, monkeypatch, alias):
    if alias == 'unicode':
        root, manifest, bundle = project_tree
        named = bundle.with_name('café-input.txt')
        named.write_bytes(bundle.read_bytes())
        project_tree = root, manifest, named
    root, nested, manifest, bundle, chunks, spec, _, _, prompt, paths = _render(project_tree, monkeypatch, 'nested', True)
    relative = bundle.relative_to(root)
    shadow = nested / relative
    shadow.parent.mkdir(parents=True)
    spelling = relative
    if alias == 'case':
        shadow = shadow.with_name(shadow.name.swapcase())
        spelling = relative.with_name(relative.name.swapcase())
    if alias == 'unicode':
        shadow = shadow.with_name(unicodedata.normalize('NFD', shadow.name))
        spelling = relative.with_name(unicodedata.normalize('NFD', relative.name))
    shadow.write_bytes(bundle.read_bytes())
    assert shadow.lstat().st_ino != bundle.lstat().st_ino
    if alias == 'dotdot':
        deeper = nested / 'deeper'
        deeper.mkdir()
        monkeypatch.chdir(deeper)
        spelling = Path('..') / spelling
    else:
        monkeypatch.chdir(nested)
    result = _record(spec, prompt, manifest, spelling, chunks, True)
    assert result.exit_code != 0, (result.output, result.exception)
    assert not paths['provenance'].exists()
