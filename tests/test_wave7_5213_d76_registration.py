"""D76: input-pinning registrations retain their absolute input identities.

Derived from the independent #5213 probes dated 2026-10-31. These fixtures
use invented SDK replies and fabricated native permission observations; they
never launch a native executable or contact a provider.
"""
from dataclasses import replace
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys

import pytest
import yaml

from data_sheets_schema import api_runner as api, provenance, shared_generation as sg
from data_sheets_schema import native_attribution_registration as native_draft
from data_sheets_schema import native_execution_permissions as permissions
from data_sheets_schema import native_execution_registration as native_registration
from tests.test_generation_manifest_identity import external  # noqa: F401
from tests.test_shared_generation_selection import registration_for, selected_spec as shared_v1
from tests.test_shared_generation_runtime import offline  # noqa: F401
from tests.test_source_heading_runtime_api import draft_files, selected_spec, client  # noqa: F401
from tests.test_receipt_completion_runtime import registration as receipt_registration


def _registered_at_root(tmp_path, draft_files, monkeypatch, layout):
    base = selected_spec(tmp_path, draft_files, source_naming=None if layout == 'none' else {})
    root = tmp_path
    manifest = base.manifest
    reg = json.loads(base.shared_generation_registration)
    if layout == 'conventional':
        # Same inputs, with the actual conventional source-manifest namespace.
        # The registered bundle and chunks remain under the root too.
        manifest = root / 'data/preprocessed/source_manifest.yaml'
        manifest.parent.mkdir(parents=True)
        manifest.write_bytes(base.manifest.read_bytes())
        reg['inputs']['source_manifest'] = sg.file_pin(manifest)
    raw = sg.canonical(reg)
    Path(reg['registration_path']).write_bytes(raw)
    monkeypatch.chdir(root)
    spec = replace(base, out_dir=None, manifest=manifest,
                   manifest_line=api.RunSpec.__dataclass_fields__['manifest_line'].default,
                   shared_generation_registration=raw.decode())
    assert spec._corpus_root == root
    return spec, reg


@pytest.mark.parametrize('layout', ['none', 'explicit', 'conventional'])
def test_sg2_root_launch_completes_and_records_registered_paths(tmp_path, request, layout):
    # This expensive full-publication/replay case must have a finite failure
    # mode in ordinary CI too, without depending on the local review harness.
    marker = os.environ.get('D4D_SG2_CHILD_CASE')
    if marker is not None:
        assert marker == request.node.nodeid
        assert os.environ.get('D4D_SG2_CHILD_PID') == str(os.getpid())
        _assert_sg2_root_launch(tmp_path, request.getfixturevalue('draft_files'),
                              request.getfixturevalue('monkeypatch'), layout)
        return
    root = Path(__file__).resolve().parents[1]
    output = tmp_path / 'isolated-sg2'
    log = tmp_path / 'isolated-sg2.log'
    env = {key: value for key, value in os.environ.items() if key not in
           {'PYTHONPATH', 'PYTHONHOME', 'PYTEST_CURRENT_TEST', 'PYTEST_PLUGINS',
            'PYTEST_DISABLE_PLUGIN_AUTOLOAD', 'D4D_SG2_CHILD_CASE', 'D4D_SG2_CHILD_PID'}
           and not key.startswith(('PYTEST_XDIST_', 'D76_', 'ANTHROPIC_', 'CBORG_', 'OPENAI_',
                                   'AZURE_', 'AWS_', 'GOOGLE_API_', 'GEMINI_', 'VERTEX_'))
           and not re.search(r'(API_KEY|ACCESS_KEY|SECRET|TOKEN|CREDENTIAL)', key, re.I)
           and not key.upper().endswith('_PROXY')}
    env.update(PYTHONDONTWRITEBYTECODE='1', PYTEST_ADDOPTS='')
    command = [sys.executable, '-S', '-P', '-B',
        str(root / 'scripts/adhoc/run_d76_sg2_case_20261102.py'),
        '--layout', layout, '--output', str(output)]
    helper = importlib.util.spec_from_file_location('_d4d_sg2_deadline',
        root / 'scripts/adhoc/d76_process_deadline_20261102.py')
    supervisor = importlib.util.module_from_spec(helper)
    sys.modules[helper.name] = supervisor
    helper.loader.exec_module(supervisor)
    with log.open('wb') as stream:
        completed = supervisor.run(command, cwd=root, env=env, stream=stream,
                        evidence=tmp_path / 'isolated-sg2-supervisor', seconds=1800)
    assert not completed.expired, f'SG2 {layout} exceeded the 1800-second subprocess deadline; retained log: {log}'
    assert completed.returncode == 0, log.read_text(errors='replace')[-20000:]
    report = json.loads((output / 'outcome.json').read_text())
    assert report['nodeid'] == request.node.nodeid
    assert report['passed'] is True
    assert (output / 'pytest.xml').stat().st_size > 0


def _assert_sg2_root_launch(tmp_path, draft_files, monkeypatch, layout):
    spec, reg = _registered_at_root(tmp_path, draft_files, monkeypatch, layout)
    fake = client(spec)
    # Exercise publication before checking paths: the original regression
    # happens after seven fake deliveries, not merely during construction.
    result = api.execute(spec, client=fake)
    assert result['validation_problems'] == []
    assert 'routing_completed_capture' in result
    assert len(fake.messages.calls) == 7
    for attribute, pin in (('bundle', 'bundle'), ('chunk_manifest', 'chunk_manifest'),
                           ('manifest', 'source_manifest')):
        expected = reg['inputs'][pin]
        assert getattr(spec, attribute) == (Path(expected['path']) if expected else None)
    record = yaml.safe_load(spec.provenance_path.read_bytes())
    inputs = record['inputs']
    assert inputs['bundle_path'] == reg['inputs']['bundle']['path']
    assert inputs['chunks']['path'] == reg['inputs']['chunk_manifest']['path']
    assert inputs['source_manifest']['path'] == (
        reg['inputs']['source_manifest']['path'] if reg['inputs']['source_manifest'] else None)
    # A completed replay independently rechecks the retained capture and makes
    # no fake deliveries or count requests.
    replay = client(spec)
    again = api.execute(replace(spec), client=replay)
    assert again['already_complete'] is True
    assert replay.messages.calls == []
    assert replay.messages.count_calls == []


def test_sg1_instruction_sha_is_launch_directory_independent(external, tmp_path, monkeypatch):
    base = shared_v1(external, registration_for(external))
    elsewhere = tmp_path / 'launch'; elsewhere.mkdir()
    rows = []
    for cwd in (elsewhere, external.bundle.parent):
        monkeypatch.chdir(cwd)
        spec = replace(base)
        sg.capture(spec)
        rows.append((spec.render_spec(), hashlib.sha256(spec.instruction.encode()).hexdigest()))
    assert rows[0] == rows[1]
    assert rows[1][0]['bundle'] == str(external.bundle)


def test_native_execution_registration_from_corpus_root_verifies_saved_probe(tmp_path, monkeypatch):
    # Build the ordinary fixture first, then make its final selection at the
    # corpus root, matching native_attribution_registration's absolute inputs.
    # The subsequent composition, permission expectation, saved-probe verifier
    # and execution registration are genuine; no validation guard is patched.
    from tests import test_native_execution as native_fixture
    original_make_case = native_fixture.make_case

    def make_case_at_root(root):
        case = original_make_case(root)
        monkeypatch.chdir(root / 'corpus')
        case['spec'] = replace(case['spec'])
        return case

    monkeypatch.setattr(native_fixture, 'make_case', make_case_at_root)
    case = native_fixture.make_native_case(tmp_path / 'native')
    value, spec = case['value'], case['spec']
    assert Path.cwd() == spec._corpus_root == case['root'] / 'corpus'
    assert spec.bundle.is_absolute() and spec.manifest.is_absolute() and spec.chunk_manifest.is_absolute()
    _, selected, replay, _ = native_registration._selection(value['composition'], value['runtime'])
    expected = native_registration.permission_expectation(value['runtime'], selected, replay,
        value['effective_system'], Path(value['attempt_directory']) / 'cli_config')
    result = permissions.verify_saved_probe(Path(value['permission_probe']).read_bytes(), expected=expected)
    assert result['checked'] is True and result['passed'] is True
    assert expected['source']['path'] == str(spec.bundle)
    assert value['selection']['render_spec']['bundle'] == str(spec.bundle)
    assert not Path(value['attempt_directory']).exists()
    assert not Path(value['evidence_directory']).exists()


@pytest.mark.parametrize('registered_kind', ['shared', 'native'])
def test_registered_record_keeps_absolute_inputs_at_owner(external, tmp_path, monkeypatch, registered_kind):
    if registered_kind == 'shared':
        base = shared_v1(external, registration_for(external))
    else:
        from tests.test_native_attempt_supervisor import make_case
        base = make_case(tmp_path / 'native-record')['spec']
    monkeypatch.chdir(base.bundle.parent)
    spec = replace(base, out_dir=None)
    for path in (spec.full_path, spec.core_path):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('id: urn:synthetic\n')
    record = provenance.build_record(spec.project, spec.method, spec.label, mode='live',
        input_bundle=spec.bundle, input_verified=True, manifest=spec.manifest,
        selected_manifest=spec.manifest, chunk_manifest=spec.chunk_manifest,
        prompt_request=spec.instruction, prompt_request_spec=spec.render_spec(),
        outputs={'full': spec.full_path, 'core': spec.core_path, 'report': spec.report_path})
    inputs = record.data['inputs']
    assert inputs['bundle_path'] == str(base.bundle)
    assert inputs['chunks']['path'] == str(base.chunk_manifest)
    assert inputs['source_manifest']['path'] == str(base.manifest)
    assert inputs['bundle_md5'] == hashlib.md5(base.bundle.read_bytes()).hexdigest()
    assert inputs['source_manifest']['md5'] == hashlib.md5(base.manifest.read_bytes()).hexdigest()
    assert inputs['chunks']['sha256'] == hashlib.sha256(base.chunk_manifest.read_bytes()).hexdigest()


@pytest.mark.parametrize('receipt_only', [False, True])
def test_no_input_pinning_registration_retains_relative_spelling(external, monkeypatch, receipt_only):
    monkeypatch.chdir(external.bundle.parent)
    changes = {'condition': 'generic_v8', 'out_dir': None}
    if receipt_only:
        changes.update(receipt_completion_version=1, receipt_completion_registration=receipt_registration())
    spec = replace(external, **changes)
    assert spec.bundle == Path(external.bundle.name)
    assert spec.manifest == Path(external.manifest.name)
    assert spec.chunk_manifest == Path(external.chunk_manifest.name)


@pytest.mark.parametrize('version', [True, '1', -1, 3])
def test_invalid_shared_selection_still_refuses_before_input_policy(external, version):
    with pytest.raises(ValueError, match='shared_generation_version'):
        replace(external, shared_generation_version=version)
