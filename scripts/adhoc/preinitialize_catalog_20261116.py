"""CI cache-test import-order diagnostic, 2026-11-16, PR 5968.

Use as a pytest plugin through run_lane. Before collection, initialize the
real duplicate-check loader with synthetic YAML. No cache authority is reset.
Inputs: installed loader. Output: the existing test's unchanged assertions.
"""
import sys


def pytest_configure(config):
    assert 'data_sheets_schema.native_catalog_reuse' not in sys.modules
    import yaml
    from linkml_runtime.utils.yamlutils import DupCheckYamlLoader
    assert yaml.load('key: value\n', Loader=DupCheckYamlLoader) == {'key': 'value'}
    assert 'yaml_constructors' in vars(DupCheckYamlLoader)
