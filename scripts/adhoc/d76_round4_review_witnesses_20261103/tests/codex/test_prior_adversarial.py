# Purpose: independent PR #5213 path probes; inputs: synthetic scratch-only trees;
# outputs: pytest/JUnit evidence of resolver and portability behavior. 2026-10-31.
import hashlib
from pathlib import Path

import pytest
import yaml

from data_sheets_schema import api_runner as api, provenance as pv
from data_sheets_schema.evaluation import arm_comparison as ac


@pytest.mark.parametrize('outside', [False, True])
def test_arm_comparison_must_not_hash_a_lexically_collapsed_decoy(tmp_path, outside):
    root = tmp_path / 'checkout'
    root.mkdir()
    physical = (tmp_path / 'outside') if outside else (root / 'real')
    (physical / 'child').mkdir(parents=True)
    (root / 'link').symlink_to(physical / 'child', target_is_directory=True)
    original = b'original input\n'
    (root / 'bundle.txt').write_bytes(original)
    (physical / 'bundle.txt').write_bytes(b'changed actual input\n')
    requested = root / 'link/../bundle.txt'
    record = {'run': {'project': 'CLINICAL_X', 'label': 'probe'}, 'inputs': {
        'bundle_path': str(requested), 'bundle_md5': hashlib.md5(original).hexdigest()}}
    result = ac.bundle_drift(record, root)
    print({'requested': str(requested), 'physical': str(requested.resolve()),
           'selected': str(ac._path(root, str(requested))), 'result': result})
    acceptable = {'unknown'} if outside else {'unknown', 'drift'}
    assert result['disk_status'] in acceptable, (
        'A decoy was reported as a match instead of checking the requested input', result)


@pytest.mark.parametrize('outside', [False, True])
def test_arm_comparison_must_not_admit_a_decoy_chunk_manifest(tmp_path, outside):
    root = tmp_path / 'checkout'
    root.mkdir()
    physical = (tmp_path / 'outside') if outside else (root / 'real')
    (physical / 'child').mkdir(parents=True)
    (root / 'link').symlink_to(physical / 'child', target_is_directory=True)
    bundle = root / 'bundle.txt'
    bundle.write_bytes(b'original input\n')
    md5 = hashlib.md5(bundle.read_bytes()).hexdigest()
    original = yaml.safe_dump({'bundle': bundle.name, 'bundle_md5': md5, 'chunks': []}).encode()
    (root / 'bundle.chunks.yaml').write_bytes(original)
    (physical / 'bundle.chunks.yaml').write_bytes(b'changed physical manifest\n')
    requested = root / 'link/../bundle.chunks.yaml'
    recovered = []
    def no_history(path, **pins):
        recovered.append(path)
        return None
    record = {'inputs': {'bundle_path': str(bundle), 'bundle_md5': md5,
        'chunks': {'path': str(requested), 'sha256': hashlib.sha256(original).hexdigest()}}}
    result = ac.bundle_drift(record, root, recover=no_history)
    print({'requested': str(requested), 'physical': str(requested.resolve()),
           'selected': str(ac._path(root, str(requested))), 'recovered': recovered, 'result': result})
    assert result['manifest_status'] == 'unknown', ('A decoy manifest satisfied the historical pin', result)


def _spec(bundle, manifest):
    return api.RunSpec(project='CLINICAL_X', arm='BASELINE (input documents only)',
        method='external', label='identity', condition='generic_v9', bundle=bundle,
        manifest=manifest, chunk_manifest=bundle.with_suffix('.chunks.yaml'),
        runtime='Claude Code', provider='offline', render_version=5,
        run_date='2026-10-31', profile='neutral')


def test_plain_parent_traversal_keeps_absolute_instruction_identity(tmp_path, monkeypatch):
    root = tmp_path / 'checkout'
    folder = root / 'data/preprocessed'
    (folder / 'child').mkdir(parents=True)
    manifest = folder / 'source_manifest.yaml'
    manifest.write_text('projects: {}\n')
    bundle = folder / 'bundle.txt'
    bundle.write_bytes(b'one input\n')
    monkeypatch.chdir(root)
    direct = _spec(bundle, manifest)
    traversed = _spec(folder / 'child/../bundle.txt', manifest)
    assert direct.bundle.resolve() == traversed.bundle.resolve()
    assert not direct.bundle.is_absolute() and traversed.bundle.is_absolute()
    assert direct.instruction != traversed.instruction
    full = root / 'data/d4d_concatenated/external/identity/CLINICAL_X_d4d.yaml'
    core = root / 'data/d4d_concatenated/external_core/identity/CLINICAL_X_d4d_core.yaml'
    for path in (full, core):
        path.parent.mkdir(parents=True)
        path.write_text('id: CLINICAL_X\n')
    records = [pv.build_record('CLINICAL_X', 'external', 'identity', mode='live',
        input_verified=True, input_bundle=p, manifest=manifest,
        outputs={'full': full, 'core': core}).data
        for p in (bundle, folder / 'child/../bundle.txt')]
    assert records[0]['inputs']['bundle_md5'] == records[1]['inputs']['bundle_md5']
    assert records[0]['inputs']['bundle_path'] != records[1]['inputs']['bundle_path']
    print({'direct': str(direct.bundle), 'traversed': str(traversed.bundle),
           'direct_instruction_sha256': hashlib.sha256(direct.instruction.encode()).hexdigest(),
           'traversed_instruction_sha256': hashlib.sha256(traversed.instruction.encode()).hexdigest(),
           'record_paths': [r['inputs']['bundle_path'] for r in records]})


def test_fresh_paths_depend_on_cwd_and_checkout_alias(tmp_path, monkeypatch):
    root = tmp_path / 'checkout'
    folder = root / 'data/preprocessed'
    folder.mkdir(parents=True)
    manifest = folder / 'source_manifest.yaml'
    manifest.write_text('projects: {}\n')
    bundle = folder / 'bundle.txt'
    bundle.write_bytes(b'one input\n')
    alias = tmp_path / 'checkout-alias'
    alias.symlink_to(root, target_is_directory=True)
    monkeypatch.chdir(root)
    direct = _spec(bundle, manifest)
    aliased = _spec(alias / bundle.relative_to(root), manifest)
    monkeypatch.chdir(folder)
    nested = _spec(bundle, manifest)
    assert not direct.bundle.is_absolute()
    assert aliased.bundle.is_absolute() and nested.bundle.is_absolute()
    assert len({str(s.bundle) for s in (direct, aliased, nested)}) == 3
    assert len({s.bundle.resolve() for s in (aliased, nested)}) == 1
    print({'root_cwd': str(direct.bundle), 'alias': str(aliased.bundle), 'nested_cwd': str(nested.bundle)})
