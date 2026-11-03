"""BC1 registered-code/write-footprint isolation; offline, Wave2 2026-10-27.

Private copies and real filesystem guards exercise the selected resource
boundary. These synthetic specs do not claim installed-hook or run admission.
"""
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from data_sheets_schema import bc1_selection, resources, shared_generation as shared
from data_sheets_schema import shared_generation_resources as closure
from data_sheets_schema.shared_write_footprint import for_run, require_separate


def spec_at(root, *, shared_version=1, selected=None):
    fields = dict(shared_generation_version=shared_version, render_version=25,
                  full_path=root / 'full' / 'record.yaml',
                  core_path=root / 'core' / 'record.yaml',
                  report_path=root / 'metadata' / 'report.md',
                  provenance_path=root / 'metadata' / 'provenance.json',
                  metadata_dir=root / 'metadata')
    if selected is not None:
        fields['bounded_carry_version'] = selected
    return SimpleNamespace(**fields)


@pytest.mark.parametrize('name', [
    'src/data_sheets_schema/bc1_codec.py',
    'src/data_sheets_schema/api_runner.py',
])
def test_selected_registered_code_cannot_alias_real_run_output(tmp_path, monkeypatch, name):
    monkeypatch.chdir(tmp_path)
    original = resources.resource_path
    authority = tmp_path / 'private-code' / Path(name).name
    authority.parent.mkdir()
    authority.write_bytes(original(name).read_bytes())
    monkeypatch.setattr(resources, 'resource_path',
                        lambda path: authority if str(path) == name else original(path))
    spec = spec_at(tmp_path / 'run', selected=1)
    spec.full_path.parent.mkdir(parents=True)
    os.link(authority, spec.full_path)
    before = authority.read_bytes()

    selected_paths = closure.resource_paths((spec,))
    expected_code = {resources.resource_path(path) for path in
                     (*shared.ROUTING_CODE, *bc1_selection.EXTRA_CODE)}
    assert expected_code <= set(selected_paths)
    with pytest.raises(ValueError, match='authority aliases a run output/write destination'):
        require_separate(selected_paths, (for_run(spec),))
    assert authority.samefile(spec.full_path)
    assert authority.read_bytes() == spec.full_path.read_bytes() == before
    assert not spec.metadata_dir.exists()

    # Causal contrast: the historical unselected shared-v1 boundary does not
    # claim that these private code copies are selected input authorities.
    legacy = spec_at(tmp_path / 'run', selected=0)
    legacy_paths = closure.resource_paths((legacy,))
    assert authority not in legacy_paths
    require_separate(legacy_paths, (for_run(legacy),))


@pytest.mark.parametrize('version', [1, 2])
def test_zero_selection_preserves_existing_resource_order(tmp_path, monkeypatch, version):
    monkeypatch.chdir(tmp_path)
    old = spec_at(tmp_path / 'run', shared_version=version)
    off = spec_at(tmp_path / 'run', shared_version=version, selected=0)
    assert closure.resource_paths((old,)) == closure.resource_paths((off,))
    assert resources.resource_path('src/data_sheets_schema/bc1_codec.py') not in closure.resource_paths((off,))
