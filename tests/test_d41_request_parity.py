"""D41 wire/identity boundaries; offline only, refs #5138 and #5142."""
from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest

from scripts.adhoc import d41_request_parity_20261026 as parity
from tests.test_source_heading_runtime_api import draft_files, selected_spec  # noqa: F401

ROOT = Path(__file__).resolve().parents[1]


def test_package_authority_refuses_a_late_foreign_module(tmp_path):
    selected = tmp_path / 'selected'
    path = selected / 'src/data_sheets_schema/late.py'
    path.parent.mkdir(parents=True)
    path.write_text('# selected fixture\n')
    module = SimpleNamespace(__file__=str(path))
    modules = {'data_sheets_schema.late': module}
    assert parity._module_authority(ROOT, selected, baseline=False, modules=modules)
    foreign = tmp_path / 'other/src/data_sheets_schema/late.py'
    foreign.parent.mkdir(parents=True)
    foreign.write_bytes(path.read_bytes())
    module.__file__ = str(foreign)
    with pytest.raises(ValueError, match='foreign package module origin'):
        parity._module_authority(ROOT, selected, baseline=False, modules=modules)


def test_package_authority_refuses_recalculated_namespace_paths(tmp_path):
    selected = tmp_path / 'selected'
    path = selected / 'src/data_sheets_schema'
    locations = [str(path)]
    module = SimpleNamespace(__file__=None, __path__=locations,
        __spec__=SimpleNamespace(submodule_search_locations=locations))
    modules = {'data_sheets_schema': module}
    assert parity._module_authority(ROOT, selected, baseline=False, modules=modules)
    locations.insert(0, str(tmp_path / 'other/src/data_sheets_schema'))
    with pytest.raises(ValueError, match='foreign package namespace origin'):
        parity._module_authority(ROOT, selected, baseline=False, modules=modules)


def test_chorus_shared_v1_exact_baseline_sdk_bytes(tmp_path):
    available = subprocess.run(['git', 'cat-file', '-e', parity.BASE + '^{commit}'], cwd=ROOT,
                               capture_output=True).returncode == 0
    if not available:
        pytest.skip('Pinned f8c5ac73c Git object unavailable; local D41 parity artifact is still required.')
    result = parity.compare(ROOT, tmp_path / 'parity')
    assert result['passed']
    assert {'full', 'reconcile_full', 'report', 'report_regate', 'full_receipt_completion',
            'typed_audit_omission', 'typed_audit_integration'} <= result['rows'].keys()
    assert any(name.startswith('typed_audit_worker:') for name in result['rows'])
    assert all(row['identical'] and row['bytes'] > 0 for row in result['rows'].values())


def test_shared_v2_keeps_strict_controller_code_freshness(tmp_path, draft_files, monkeypatch):
    from data_sheets_schema import resources, shared_generation as sg
    spec = selected_spec(tmp_path, draft_files)
    registration = spec.shared_generation_registration.encode()
    before = sg.parse_registration(registration)
    name = 'src/data_sheets_schema/api_runner.py'
    assert name in sg.ROUTING_CODE
    source = resources.resource_path
    copy = tmp_path / 'api_runner_identity_copy.py'
    copy.write_bytes(source(name).read_bytes())
    monkeypatch.setattr(resources, 'resource_path', lambda path: copy if str(path) == name else source(path))
    assert sg.parse_registration(registration) == before
    copy.write_bytes(copy.read_bytes() + b'\n# offline controller identity mutation\n')
    after = sg.descriptor(version=2, condition=spec.condition)
    assert before['selection']['routing_code'][name] != after['routing_code'][name]
    with pytest.raises(ValueError, match='different protocol or selected assets'):
        sg.parse_registration(registration)
