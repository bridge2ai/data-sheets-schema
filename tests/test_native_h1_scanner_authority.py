"""H1 authority source review, 2026-11-12: render proof, not launch acceptance.

The reviewed source adds import-fact reuse and snapshot source attestation.
Offline source-copy mutations must still refuse before any render is accepted.
"""
import hashlib

import pytest

from tests.test_native_u5_scanner import copied_route, RUNNER, scan


AUTHORITY = 'src/data_sheets_schema/native_execution_authority_v2.py'
REVIEWED = 'b2189db86428b5977bfcbaa72adc5f504f3449c31b583359555b074916a95558'


def test_reviewed_authority_preserves_integrated_render_proof(tmp_path):
    root = copied_route(tmp_path)
    assert hashlib.sha256((root / AUTHORITY).read_bytes()).hexdigest() == REVIEWED
    result = scan.derive_native_shared_route(root, scan._tree(root / RUNNER))
    assert result['enabled_values'] == [1]
    assert result['renderer'] == 26
    assert AUTHORITY in result['evidence']


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
