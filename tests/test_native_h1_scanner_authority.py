"""H1 authority source review, 2026-11-12: render proof, not launch acceptance.

The reviewed source adds import-fact reuse and snapshot source attestation,
then #5966's explicit v2 helper-cache declaration and closed path validator.
Offline source-copy mutations must still refuse before any render is accepted.
"""
import hashlib

import pytest

from tests.test_native_u5_scanner import copied_route, RUNNER, scan


AUTHORITY = 'src/data_sheets_schema/native_execution_authority_v2.py'
# Lead-authorized review fix, 2026-11-16: include the narrowed pre-import
# package-root reuse while preserving fresh loader-exit origin checks.
# D159 (owner, 2026-11-17): its two git subprocess timeouts 30 -> 60 s; nothing else changed.
# PR 6302, 2026-11-21: four fixed modules join the same consumer restrictions.
PRE_STAGE_GRANT_REVIEWED = '9593574b74353be270b47cf866022d09c6c70f329b65e1272a65244d5a72418c'
STAGE_GRANT_REVIEWED = '822c276651532dd582e30c62f45cf8270cba98edbbc8c4628be44c604f87d7ad'
REVIEWED = '3ebc9277c40c2ca76f16bb8830d2d268391936f5778a7fda0042d9a4c81fa970'
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


def test_stage_grant_authority_delta_is_only_four_fixed_consumer_modules(tmp_path):
    root = copied_route(tmp_path)
    raw = (root / AUTHORITY).read_bytes()
    current = (
        b"    'native_shared_permission_protocol', 'native_shared_permission_wire', 'native_stage_root_grant',\n"
        b"    'native_stage_root_diagnostic', 'native_wire_2_1_325',\n"
        b"    'native_shared_runtime_constants',\n")
    predecessor = b"    'native_shared_permission_protocol', 'native_shared_runtime_constants',\n"
    assert raw.count(current) == 1
    assert hashlib.sha256(raw.replace(current, predecessor, 1)).hexdigest() == PRE_STAGE_GRANT_REVIEWED
    assert scan._NATIVE_V3_RENDER_SOURCES[AUTHORITY] == REVIEWED


def test_production_wire_authority_delta_is_only_one_fixed_consumer_module(tmp_path):
    raw = (copied_route(tmp_path) / AUTHORITY).read_bytes()
    current = b"'native_stage_root_diagnostic', 'native_wire_2_1_325',"
    predecessor = b"'native_stage_root_diagnostic',"
    assert raw.count(current) == 1
    assert hashlib.sha256(raw.replace(current, predecessor, 1)).hexdigest() == STAGE_GRANT_REVIEWED


def test_production_wire_callee_and_attribution_drift_refuse_render_proof(tmp_path):
    mutations = (
        ('native_wire_2_1_325', "return type(executable) is dict and (", "return True or ("),
        ('native_attribution_registration_v2', 'self.runtime = None', 'self.runtime = {}'),
    )
    for number, (module, before, after) in enumerate(mutations):
        root = copied_route(tmp_path / str(number))
        assert scan.derive_native_shared_route(root, scan._tree(root / RUNNER))['renderer'] == 26
        relative = 'src/data_sheets_schema/' + module + '.py'
        path = root / relative
        raw = path.read_text()
        assert raw.count(before) == 1
        path.write_text(raw.replace(before, after, 1))
        with pytest.raises(scan.ConfigError, match='v2 envelope authority source changed: ' + relative):
            scan.derive_native_shared_route(root, scan._tree(root / RUNNER))


def test_stage_grant_consumer_module_drift_refuses_render_proof(tmp_path):
    for number, module in enumerate(('native_shared_permission_wire', 'native_stage_root_grant',
                                     'native_stage_root_diagnostic', 'native_wire_2_1_325')):
        root = copied_route(tmp_path / str(number))
        assert scan.derive_native_shared_route(root, scan._tree(root / RUNNER))['renderer'] == 26
        path = root / AUTHORITY
        source = path.read_text()
        before = repr(module)
        assert source.count(before) == 1
        path.write_text(source.replace(before, repr('native_unreviewed_consumer'), 1))
        with pytest.raises(scan.ConfigError, match='v2 envelope authority source changed: ' + AUTHORITY):
            scan.derive_native_shared_route(root, scan._tree(root / RUNNER))


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
