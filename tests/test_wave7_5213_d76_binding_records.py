"""D76 explicit binding reaches the direct builder and recorder (2026-10-31)."""
from pathlib import Path

import pytest

from data_sheets_schema import provenance
from tests.test_generation_manifest_identity import external, offline  # noqa: F401
from tests.test_audit_recall_leak_rendered import direct_registration  # noqa: F401


def test_direct_preparation_records_absolute_registered_inputs(direct_registration):
    job = direct_registration.registration['generation']['jobs'][0]
    rendered = job['render_spec']
    assert rendered['bundle'] == job['bundle']
    assert rendered['manifest'] == job['manifest']
    assert rendered['chunk_manifest'] == job['chunks']
    assert all(Path(rendered[key]).is_absolute() for key in ('bundle', 'manifest', 'chunk_manifest'))
    assert rendered['registered_input_paths'] is True


@pytest.mark.parametrize('binding', [False, True])
def test_explicit_record_binding_controls_input_spelling(external, monkeypatch, binding):
    root = external.bundle.parent
    monkeypatch.chdir(root)
    # The conventional output location gives the recorder a known corpus owner.
    output = root / 'data/d4d_concatenated'
    full = output / 'custom' / external.label / 'EXTERNAL_d4d.yaml'
    core = output / 'custom_core' / external.label / 'EXTERNAL_d4d_core.yaml'
    for path in (full, core):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('id: urn:synthetic\n')
    recorded = external.render_spec()
    if binding:
        recorded['registered_input_paths'] = True
    record = provenance.build_record(external.project, external.method, external.label, mode='live',
        input_bundle=external.bundle, input_verified=True, manifest=external.manifest,
        chunk_manifest=external.chunk_manifest, prompt_request_spec=recorded,
        outputs={'full': full, 'core': core})
    inputs = record.data['inputs']
    for actual, selected in ((inputs['bundle_path'], external.bundle),
            (inputs['source_manifest']['path'], external.manifest),
            (inputs['chunks']['path'], external.chunk_manifest)):
        expected = selected if binding else selected.relative_to(root)
        assert actual == str(expected)
