# Purpose: independent D76 registration/discovery/resolver probes for PR #5213, 2026-11-01.
# Inputs: synthetic scratch fixtures; outputs: pytest/JUnit evidence. No providers.
from dataclasses import replace
import hashlib
from pathlib import Path

import pytest
import yaml

from data_sheets_schema import api_runner as api, chunking, shared_generation as sg
from data_sheets_schema.evaluation import arm_comparison as ac
from tests.test_generation_manifest_identity import external, offline  # noqa: F401
from tests.test_shared_generation_selection import registration_for, selected_spec
from tests.test_manifest_corpus_root import project_tree  # noqa: F401


@pytest.mark.parametrize('spelling', [
    '../root/data/preprocessed/bundle.txt',
    'data/../data/preprocessed/bundle.txt',
    'data/preprocessed/../preprocessed/bundle.txt',
    'data/preprocessed/child/../bundle.txt',
    '/old/../old/data/preprocessed/bundle.txt',
    '/old/data/../data/preprocessed/bundle.txt',
    '/old/data/preprocessed/child/../bundle.txt',
])
@pytest.mark.parametrize('aliased_root', [False, True])
def test_traversal_positions_stay_unknown_with_symlinked_root(tmp_path, spelling, aliased_root):
    root = tmp_path / 'root'
    folder = root / 'data/preprocessed'
    (folder / 'child').mkdir(parents=True)
    (folder / 'bundle.txt').write_bytes(b'historical decoy\n')
    alias = tmp_path / 'alias'
    alias.symlink_to(root, target_is_directory=True)
    called = []
    result = ac.bundle_drift({'inputs': {'bundle_path': spelling,
        'bundle_md5': hashlib.md5(b'historical decoy\n').hexdigest(),
        'chunks': {'path': spelling, 'sha256': hashlib.sha256(b'historical decoy\n').hexdigest()}}},
        alias if aliased_root else root, recover=lambda *a, **k: called.append(a))
    assert result['disk_status'] == result['manifest_status'] == 'unknown'
    assert result['disk_md5'] is None and called == []


@pytest.mark.parametrize('foreign', [False, True])
def test_plain_paths_remain_usable_with_symlinked_root(tmp_path, foreign):
    root = tmp_path / 'root'
    folder = root / 'data/preprocessed'
    folder.mkdir(parents=True)
    bundle = folder / 'bundle.txt'
    bundle.write_bytes(b'same input\n')
    alias = tmp_path / 'alias'
    alias.symlink_to(root, target_is_directory=True)
    spelling = '/foreign/data/preprocessed/bundle.txt' if foreign else str(bundle)
    result = ac.bundle_drift({'inputs': {'bundle_path': spelling,
        'bundle_md5': hashlib.md5(bundle.read_bytes()).hexdigest()}}, alias)
    assert result['disk_status'] == 'match'


@pytest.mark.parametrize('field', ['bundle', 'manifest', 'chunk_manifest'])
@pytest.mark.parametrize('kind', ['bytes', 'locator'])
def test_registered_drift_refuses_before_any_client_access(external, monkeypatch, field, kind):
    spec = selected_spec(external, registration_for(external))
    monkeypatch.chdir(external.bundle.parent)
    spec = replace(spec)
    pin = getattr(spec, field)
    if kind == 'bytes':
        pin.write_bytes(pin.read_bytes() + b'\n# changed after registration\n')
    else:
        decoy = pin.with_name('same-bytes-' + pin.name)
        decoy.write_bytes(pin.read_bytes())
        setattr(spec, field, decoy)
    accesses = []

    class ForbiddenClient:
        def __getattr__(self, name):
            accesses.append(name)
            pytest.fail('client accessed before input drift refusal: ' + name)

    with pytest.raises(ValueError, match='authority changed|source selection differs'):
        api.execute(spec, client=ForbiddenClient())
    assert accesses == []
    assert not spec.provenance_path.exists()


@pytest.mark.parametrize('selected_manifest', [False, True])
def test_cwd_dependent_chunk_discovery_cannot_silently_change_registration(external, tmp_path, monkeypatch, selected_manifest):
    root = tmp_path / 'corpus'
    folder = root / 'data/preprocessed'
    bundle = folder / 'concatenated/EXTERNAL_preprocessed.txt'
    bundle.parent.mkdir(parents=True)
    bundle.write_bytes(external.bundle.read_bytes())
    manifest = folder / 'source_manifest.yaml'
    doc = yaml.safe_load(external.manifest.read_bytes())
    doc['projects']['EXTERNAL']['bundle'] = str(bundle)
    manifest.write_text(yaml.safe_dump(doc))
    chunks = folder / 'chunks/EXTERNAL_chunks.yaml'
    chunks.parent.mkdir()
    chunks.write_text(chunking.dump_manifest(chunking.build_manifest(bundle)))
    sidecar = bundle.with_name('EXTERNAL_preprocessed_chunks.yaml')
    sidecar.write_bytes(chunks.read_bytes())
    base = replace(external, bundle=bundle, manifest=manifest if selected_manifest else None,
        chunk_manifest=chunks, manifest_line=api.RunSpec.__dataclass_fields__['manifest_line'].default)
    spec = selected_spec(base, registration_for(base))
    nested = root / 'nested'
    nested.mkdir()
    monkeypatch.chdir(root)
    if not selected_manifest:
        # API discovery is deliberately disabled without a source manifest.
        # Even though the low-level locator can depend on cwd, the registered
        # RunSpec refuses an omitted chunk locator at both working directories.
        assert chunking.manifest_for(bundle, source_manifest=None) == Path('data/preprocessed/chunks/EXTERNAL_chunks.yaml')
        with pytest.raises(ValueError, match='explicit captured chunk manifest'):
            replace(spec, chunk_manifest=None)
        monkeypatch.chdir(nested)
        assert chunking.manifest_for(bundle, source_manifest=None) == sidecar
        with pytest.raises(ValueError, match='explicit captured chunk manifest'):
            replace(spec, chunk_manifest=None)
        assert spec.chunk_manifest == chunks
        sg.assert_current(spec)
        return
    rebuilt = replace(spec, chunk_manifest=None)
    assert rebuilt.chunk_manifest == chunks
    monkeypatch.chdir(nested)
    # Frozen spec remains anchored when cwd changes after construction.
    assert rebuilt.chunk_manifest == chunks
    sg.assert_current(rebuilt)
    assert replace(spec, chunk_manifest=None).chunk_manifest == chunks


@pytest.mark.parametrize('field', ['bundle', 'chunk_manifest'])
@pytest.mark.parametrize('alias_kind', ['copy', 'symlink'])
def test_recorder_cannot_substitute_unused_input_spelling(project_tree, monkeypatch, field, alias_kind):
    from click.testing import CliRunner
    from data_sheets_schema.cli import cli
    from data_sheets_schema.cli.api import _spec
    from data_sheets_schema.resources import resource_path

    root, manifest, bundle = project_tree
    monkeypatch.chdir(root)
    chunks, _ = chunking.write_manifest_for(bundle)
    chunks = chunks.absolute()
    nested = root / 'analysis'
    nested.mkdir()
    monkeypatch.chdir(nested)
    spec = _spec('CLINICAL_X', 'baseline', 'unused-spelling', 'generic_v9',
        bundle=bundle, manifest=manifest, runtime='Claude Code', provider='offline', chunk_manifest=chunks)
    instruction = spec.instruction
    prompt = root / 'instruction.txt'
    prompt.write_text(instruction)
    for path in (spec.full_path, spec.core_path):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(spec.manifest_line + '\n# Source bundle: ' + str(bundle)
            + '\n# Provider: offline\n# Agent runtime: Claude Code\nid: https://example.org/test\n')
    spec.report_path.write_text('# Synthetic report\n')
    selected = getattr(spec, field)
    alternate = selected.with_name('unused-' + selected.name)
    if alias_kind == 'copy':
        alternate.write_bytes(selected.read_bytes())
    else:
        alternate.symlink_to(selected)
    record_path = spec.provenance_path
    monkeypatch.chdir(root)
    result = CliRunner().invoke(cli, ['provenance', 'record', '--manifest', str(manifest),
        '--project', spec.project, '--method', spec.method, '--label', spec.label,
        '--input-bundle', str(alternate if field == 'bundle' else bundle),
        '--chunk-manifest', str(alternate if field == 'chunk_manifest' else chunks),
        '--condition', spec.condition, '--runtime', spec.runtime, '--provider', 'offline',
        '--prompt-text', str(prompt), '--run-date', spec.run_date,
        *[arg for path in spec.prompt_files for arg in ('--prompt', str(resource_path(path)))]])
    assert result.exit_code != 0
    assert 'does not reproduce --prompt-text' in result.output, (result.output, result.exception)
    assert not record_path.exists()
