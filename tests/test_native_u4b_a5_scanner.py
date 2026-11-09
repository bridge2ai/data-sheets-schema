"""A5 D114 source-proof regression, 2026-11-09 (#4354); no generation imports."""
import pytest

from tests.test_native_u5_scanner import copied_route, PREPARER, RUNNER, scan
from tests.test_native_u4b_a4_producer import helper


@pytest.mark.parametrize('historical', [False, True])
def test_exact_historical_and_u4b_producers_derive(tmp_path, historical):
    root = copied_route(tmp_path)
    if historical:
        (root / PREPARER).write_bytes(helper.committed_preimage())
    assert scan.derive_native_shared_route(root, scan._tree(root / RUNNER))['enabled_values'] == [1]


@pytest.mark.parametrize('before,after', [
    ("basis = runtime['limits_basis']", "basis = runtime['provider']"),
    ("if basis.lstrip().startswith('{'):", 'if True:'),
    ("'runtime profile basis', 16384", "'runtime profile basis', 32768"),
    ("declared.get('kind') == 'd4d_native_u4b_runtime_basis'", "declared.get('kind') is not None"),
    ('from .agentic_runtime import toolchain', 'from .foreign_runtime import toolchain'),
    ('toolchain(native_shared=True)', 'toolchain(native_shared=False)'),
    ('toolchain(native_shared=True)', 'toolchain()'),
    ('    instruction = spec.instruction', '    spec._agentic_toolchain = replacement\n    instruction = spec.instruction'),
])
def test_d114_discriminator_bound_roster_and_order_are_exact(tmp_path, before, after):
    root = copied_route(tmp_path)
    assert scan.derive_native_shared_route(root, scan._tree(root / RUNNER))['enabled_values'] == [1]
    path = root / PREPARER
    source = path.read_text()
    assert source.count(before) == 1
    path.write_text(source.replace(before, after))
    with pytest.raises(scan.ConfigError, match='unsupported exact v2 render producer/consumer: prepare'):
        scan.derive_native_shared_route(root, scan._tree(root / RUNNER))


def test_d114_binding_before_runtime_is_not_an_allowed_alternative(tmp_path):
    root = copied_route(tmp_path)
    path = root / PREPARER
    original = path.read_bytes()
    assert original.count(helper.ANCHOR + helper.INSERTION) == 1
    path.write_bytes(original.replace(helper.ANCHOR + helper.INSERTION,
                                      helper.INSERTION + helper.ANCHOR, 1))
    with pytest.raises(scan.ConfigError, match='unsupported exact v2 render producer/consumer: prepare'):
        scan.derive_native_shared_route(root, scan._tree(root / RUNNER))
