"""Receipt verdicts pin the same bytes they parse and compare."""
import copy
import hashlib
from pathlib import Path
import pytest
import yaml

from data_sheets_schema import receipts, chunking
from tests.test_receipts import BUNDLE, FULL, _receipt


@pytest.fixture
def files(tmp_path):
    bundle = tmp_path / 'P_preprocessed.txt'
    bundle.write_text(BUNDLE)
    full = tmp_path / 'P_d4d.yaml'
    full.write_text(yaml.safe_dump(FULL))
    receipt = tmp_path / 'P_coverage_receipt.yaml'
    md5 = hashlib.md5(bundle.read_bytes()).hexdigest()
    receipt.write_text(yaml.safe_dump(_receipt(md5)))
    manifest = tmp_path / 'P_chunks.yaml'
    mapping = chunking.build_manifest(bundle)
    manifest.write_text(chunking.dump_manifest(mapping))
    return bundle, full, receipt, manifest, md5, mapping


def block(files, record_chunks=None):
    bundle, full, receipt, manifest, md5, _ = files
    return receipts.block_for(full, receipt, bundle, md5, True, manifest=manifest, record_chunks=record_chunks)


@pytest.mark.parametrize('target', ['manifest', 'receipt'])
def test_returned_pin_names_the_bytes_checked_before_a_concurrent_replacement(files, monkeypatch, target):
    path = files[3 if target == 'manifest' else 2]
    original = path.read_bytes()
    real = receipts.check
    def check_then_replace(*args, **kwargs):
        result = real(*args, **kwargs)
        path.write_bytes(original + b'\n# replaced after checking\n')
        return result
    monkeypatch.setattr(receipts, 'check', check_then_replace)
    result = block(files)
    assert result['checked'] and result['findings'] == []
    assert result['artifacts'][target]['sha256'] == hashlib.sha256(original).hexdigest()


def test_recorded_manifest_hash_guards_the_mapping_actually_parsed(files, monkeypatch):
    bundle, full, receipt, manifest, md5, mapping = files
    original = manifest.read_bytes()
    bad = copy.deepcopy(mapping)
    bad['chunks'][1]['lines'] = list(bad['chunks'][2]['lines'])
    manifest.write_text(chunking.dump_manifest(bad))
    real_text, real_bytes = Path.read_text, Path.read_bytes
    changed = False
    def after_read(path, raw):
        nonlocal changed
        if path == manifest and not changed:
            changed = True
            manifest.write_bytes(original)
        return raw
    def read_text(path, *args, **kwargs):
        return after_read(path, real_text(path, *args, **kwargs))
    def read_bytes(path):
        return after_read(path, real_bytes(path))
    monkeypatch.setattr(Path, 'read_text', read_text)
    monkeypatch.setattr(Path, 'read_bytes', read_bytes)
    result = block(files, {'sha256': hashlib.sha256(original).hexdigest(),
                          'rule': mapping['rule'], 'chunk_count': mapping['chunk_count']})
    assert result['checked'] and result['findings'] == []
    assert result['artifacts']['manifest']['path'] is None
