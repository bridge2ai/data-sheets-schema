"""H1 authority source review, 2026-11-12: render proof, not launch acceptance.

The reviewed source adds import-fact reuse and snapshot source attestation,
then #5966's explicit v2 helper-cache declaration and closed path validator.
Offline source-copy mutations must still refuse before any render is accepted.
"""
import hashlib

import pytest

from tests.test_native_u5_scanner import copied_route, RUNNER, scan


AUTHORITY = 'src/data_sheets_schema/native_execution_authority_v2.py'
REVIEWED = '00b0f717bc0398b905cfcb81de47c4434f70c2909bbbffb0b92789dbf867047c'
HELPER_CACHE = 'src/data_sheets_schema/native_helper_cache.py'
REVIEWED_HELPER_CACHE = '0934f71630ab45e4670ffa0d14f90c1cfbb23a132a23ca8c6ccfcc0c58a52a95'


def test_reviewed_authority_preserves_integrated_render_proof(tmp_path):
    root = copied_route(tmp_path)
    assert hashlib.sha256((root / AUTHORITY).read_bytes()).hexdigest() == REVIEWED
    result = scan.derive_native_shared_route(root, scan._tree(root / RUNNER))
    assert result['enabled_values'] == [1]
    assert result['renderer'] == 26
    assert AUTHORITY in result['evidence']
    assert hashlib.sha256((root / HELPER_CACHE).read_bytes()).hexdigest() == REVIEWED_HELPER_CACHE
    assert HELPER_CACHE in result['evidence']


@pytest.mark.parametrize('before,after', [
    ('    return tuple(facts)\n', '    return ()\n'),
    ('        snapshots._metadata.cache_clear()\n', '        pass\n'),
    ('                snapshot_identity = _verified_snapshot_identity(snapshots, package_sources)\n',
     '                snapshot_identity = {}\n'),
])
def test_new_authority_regions_remain_bound_to_reviewed_bytes(tmp_path, before, after):
    root = copied_route(tmp_path)
    assert scan.derive_native_shared_route(root, scan._tree(root / RUNNER))['renderer'] == 26
    path = root / AUTHORITY
    original = path.read_text()
    assert before in original and before != after
    changed = original.replace(before, after, 1)
    assert changed != original
    path.write_text(changed)
    with pytest.raises(scan.ConfigError, match='v2 envelope authority source changed: ' + AUTHORITY):
        scan.derive_native_shared_route(root, scan._tree(root / RUNNER))


@pytest.mark.parametrize('before,after', [
    ("ENVIRONMENT_KEY = 'PYSTOW_HOME'", "ENVIRONMENT_KEY = 'HOME'"),
    ('if cache == home or home in cache.parents or cache in home.parents:', 'if False:'),
    ('if cache != Path(attempt) / DIRECTORY:', 'if False:'),
])
def test_helper_cache_callee_drift_refuses_render_proof(tmp_path, before, after):
    root = copied_route(tmp_path)
    assert scan.derive_native_shared_route(root, scan._tree(root / RUNNER))['renderer'] == 26
    path = root / HELPER_CACHE
    original = path.read_text()
    assert original.count(before) == 1
    path.write_text(original.replace(before, after, 1))
    with pytest.raises(scan.ConfigError, match='v2 envelope authority source changed: ' + HELPER_CACHE):
        scan.derive_native_shared_route(root, scan._tree(root / RUNNER))
