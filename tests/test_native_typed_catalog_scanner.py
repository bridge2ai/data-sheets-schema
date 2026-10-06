"""Finite scanner bindings for the private catalog handoff and public wrapper."""
import pytest
from tests.test_generation_specificity_skill import TestNativeSharedProcedure as Procedure, scan


@pytest.mark.parametrize('module,before,after', [
    ('native_shared_stage', '_catalog_lookup=catalog_reuse._CatalogLookup(self.catalogs, self.s)',
     '_catalog_lookup=catalog_reuse._CatalogLookup(self.catalogs, other)'),
    ('native_shared_stage', '_catalog_lookup=catalog_reuse._CatalogLookup(self.catalogs, self.s)',
     '_catalog_lookup=foreign(self.catalogs, self.s)'),
    ('native_shared_stage', 'from . import native_catalog_reuse as catalog_reuse',
     'from . import foreign as catalog_reuse'),
    ('typed_audit', 'return _prepare(protocol=protocol, original_full=original_full, bundle=bundle,',
     'return foreign(protocol=protocol, original_full=original_full, bundle=bundle,'),
    ('typed_audit', 'return _prepare(protocol=protocol, original_full=original_full, bundle=bundle,',
     'return _prepare(protocol=protocol, original_full=other, bundle=bundle,'),
])
def test_private_handoff_and_public_forwarding_mutations_refuse(tmp_path, module, before, after):
    root = Procedure.fixture(tmp_path)
    target = root/'src/data_sheets_schema'/(module+'.py')
    raw = target.read_text()
    assert raw.count(before) == 1
    target.write_text(raw.replace(before,after))
    with pytest.raises(scan.ConfigError, match='not derived'):
        scan.derive_native_shared_procedure(root)
