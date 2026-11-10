"""A5 D114 source-proof regression, 2026-11-09 (#4354); no generation imports."""
import pytest

from tests.test_native_u5_scanner import copied_route, _producer_source, PREPARER, RUNNER, scan
from tests.test_native_u4b_a4_producer import helper


@pytest.mark.parametrize('producer', ['prepare', '_prepare'])
@pytest.mark.parametrize('with_u4b_hook', [False, True])
def test_exact_current_reader_and_u4b_producers_derive(tmp_path, with_u4b_hook, producer):
    root = copied_route(tmp_path)
    if not with_u4b_hook:
        path = root / PREPARER
        prefix, source, suffix = _producer_source(path, producer)
        assert source.count(helper.ANCHOR + helper.INSERTION) == 1
        path.write_bytes(prefix + source.replace(
            helper.ANCHOR + helper.INSERTION, helper.ANCHOR, 1) + suffix)
    assert scan.derive_native_shared_route(root, scan._tree(root / RUNNER))['enabled_values'] == [1]


def test_frozen_historical_producer_does_not_replace_current_reader_proof(tmp_path):
    root = copied_route(tmp_path)
    assert scan.derive_native_shared_route(root, scan._tree(root / RUNNER))['enabled_values'] == [1]
    # Keep the A4 artifact pinned; it predates the required current-reader and
    # registered-input binding, so it is no longer a valid integrated producer.
    (root / PREPARER).write_bytes(helper.committed_preimage())
    with pytest.raises(scan.ConfigError, match='unsupported v2 render producer: prepare'):
        scan.derive_native_shared_route(root, scan._tree(root / RUNNER))


@pytest.mark.parametrize('producer', ['prepare', '_prepare'])
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
def test_d114_discriminator_bound_roster_and_order_are_exact(tmp_path, before, after, producer):
    root = copied_route(tmp_path)
    assert scan.derive_native_shared_route(root, scan._tree(root / RUNNER))['enabled_values'] == [1]
    path = root / PREPARER
    prefix, source, suffix = _producer_source(path, producer)
    before, after = before.encode('utf-8'), after.encode('utf-8')
    assert source.count(before) == 1
    path.write_bytes(prefix + source.replace(before, after, 1) + suffix)
    with pytest.raises(scan.ConfigError, match='unsupported v2 render producer: ' + producer):
        scan.derive_native_shared_route(root, scan._tree(root / RUNNER))


@pytest.mark.parametrize('producer', ['prepare', '_prepare'])
def test_d114_binding_before_runtime_is_not_an_allowed_alternative(tmp_path, producer):
    root = copied_route(tmp_path)
    path = root / PREPARER
    prefix, original, suffix = _producer_source(path, producer)
    assert original.count(helper.ANCHOR + helper.INSERTION) == 1
    path.write_bytes(prefix + original.replace(helper.ANCHOR + helper.INSERTION,
                                               helper.INSERTION + helper.ANCHOR, 1) + suffix)
    with pytest.raises(scan.ConfigError, match='unsupported v2 render producer: ' + producer):
        scan.derive_native_shared_route(root, scan._tree(root / RUNNER))
