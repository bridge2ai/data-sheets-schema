"""Real native26 public lifetime using ordinary Python and invented authority.

The model/permission/runtime observations below are expressly synthetic. All
stage, schema, receipt, attribution and recorder helper commands are genuine.
No paid provider, native binary, authentication or scientific claim is made.
"""
from dataclasses import replace
from pathlib import Path
import json
import sys

import pytest

from tests.native_shared_fixture import build_native_fixture
from tests.test_native_shared_permissions import fabricated_manifest
from tests.test_native_execution import fake_observation
from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_controller as composition
from data_sheets_schema import native_shared_registration as registration
from data_sheets_schema import native_shared_execution as execute
from data_sheets_schema import native_shared_policy as policy
from data_sheets_schema import native_execution_authority as authority
from data_sheets_schema import native_attribution_registration as inherited_registration


def make_case(root):
    data = build_native_fixture(root, registered_python=sys.executable)
    spec = replace(data['spec'])
    parent = data['runtime_path'].parent
    fake = root / 'ordinary-python-test-peer'
    fake.write_bytes(('#!' + sys.executable + '\n').encode() + (
        Path(__file__).parent / 'fixtures/native_shared_execution/fake_cli.py').read_bytes())
    fake.chmod(0o700)
    runtime = c.strict_json(data['runtime_path'].read_bytes())
    runtime['executable'] = {'path': str(fake), 'sha256': c.sha(fake.read_bytes()),
        'version': 'SYNTHETIC PYTHON SOFTWARE TEST', 'init_version': 'synthetic-python-1'}
    runtime['environment']['PATH'] = str(Path(sys.executable).parent) + ':/usr/bin:/bin'
    runtime['keep_awake']['host_platform'] = sys.platform
    # Bounded test allowance for >30 genuine offline helper processes on CI.
    runtime['deadline_seconds'] = 900
    runtime_path = parent / 'runtime-execution.json'; runtime_path.write_bytes(c.canonical(runtime))
    composition.bind_runtime(spec, runtime_path, 3)
    instruction = parent / 'instruction-execution.md'; instruction.write_text(spec.instruction)
    selected = composition.compose(spec, runtime_path=runtime_path,
        instruction_path=instruction, max_draft_checks=3)
    comp = parent / 'composition-execution.json'; comp.write_bytes(c.canonical(selected))
    (parent / 'synthetic-seeds.json').write_bytes(c.canonical({'full': data['full_raw'].decode(),
        'receipt': data['receipt_raw'].decode(), 'source_text': data['source_text'],
        'chunk_id': data['chunk_id'], 'correction': True}))
    system = parent / 'system.txt'; system.write_text('Explicitly synthetic Python software test. No actual native or provider.\n')
    attempt = root / 'native-attempt'; output = root / 'native-evidence'
    dependencies = authority.dependency_identity()
    expected = registration.permission_expectation(runtime, selected, spec,
        system.read_text() + policy.command_guidance(selected['policy']), attempt / 'cli_config', dependencies)
    manifest = fabricated_manifest(expected, data['selection'].document(), root / 'invented-probe', spec.bundle.read_bytes())
    probe = parent / 'invented-permissions.json'; probe.write_bytes(c.canonical(manifest))
    value = registration.registration(comp, system, permission_probe_path=probe,
        attempt_id=attempt.name, attempt_directory=attempt, evidence_directory=output, max_draft_checks=3)
    raw = c.canonical(value)
    binding = {'registration_sha256': c.sha(raw), 'attempt_id': value['attempt_id'],
        'source_commit': value['dependencies']['base']['source_commit'],
        'dependencies_sha256': c.sha(inherited_registration._encoded(value['dependencies']))}
    review = {**binding, 'kind': 'd4d_native_execution_review', 'version': 1,
        'reviewer': 'invented-independent-reviewer', 'author': 'invented-author',
        'independent': True, 'decision': 'approved', 'reviewed_at': 'synthetic-time',
        'evidence': 'Fabricated software test only; no actual review authority.'}
    ci = {**binding, 'kind': 'd4d_native_execution_ci', 'version': 1, 'checks': {
        name: {'head_sha': binding['source_commit'], 'status': 'completed', 'conclusion': 'success',
            'details_url': 'https://github.com/bridge2ai/data-sheets-schema/actions/SYNTHETIC-NOT-A-RUN'}
        for name in execute.REQUIRED_CHECKS}}
    review_path = parent / 'invented-review.json'; review_path.write_bytes(c.canonical(review))
    ci_path = parent / 'invented-ci.json'; ci_path.write_bytes(c.canonical(ci))
    word = {**binding, 'kind': 'd4d_native_execution_launch_authorization', 'version': 1,
        'owner': 'invented-test-owner', 'authorized_at': 'synthetic-time', 'word': 'AUTHORIZE_ONE_NATIVE_ATTEMPT',
        'review_sha256': c.sha(review_path.read_bytes()), 'ci_sha256': c.sha(ci_path.read_bytes()),
        'permission_probe_sha256': value['permission_probe_sha256']}
    word_path = parent / 'invented-owner.json'; word_path.write_bytes(c.canonical(word))
    return {**data, 'root': root, 'spec': spec, 'value': value, 'raw': raw,
        'kwargs': {'review_path': review_path, 'ci_path': ci_path, 'launch_word_path': word_path}}


def test_actual_public_correction_three_workers_and_saved_completion(tmp_path, monkeypatch):
    monkeypatch.chdir(authority.ROOT)
    case = make_case(tmp_path / 'native26')
    monkeypatch.setattr(execute, '_probe_runtime', fake_observation)
    with authority.loaded_dependencies(case['value']['dependencies']) as modules:
        def forbidden(*a, **k):
            pytest.fail('historical launcher, auth or provider factory invoked')
        for module, names in [('prepare_direct', ['auth_evidence']), ('run_direct_canary', ['main']),
                              ('run_api_canary', ['main']), ('budgeted_cborg', ['cborg_client'])]:
            for name in names:
                if hasattr(modules[module], name): monkeypatch.setattr(modules[module], name, forbidden)
        result = execute.launch(case['raw'], **case['kwargs'])
    (case['root'] / 'actual-result.json').write_bytes(c.canonical(result))
    assert result['runtime_gates_passed'], json.dumps(result, indent=2)
    assert result['state'] == 'completed_pending_independent_review'
    assert set(result['gates']) == set(execute.gates.GATES)
    assert all(row['checked'] is True and row['passed'] is True for row in result['gates'].values())
    assert result['gates']['live_attribution']['result']['checks'] == 2
    selection = case['selection']
    journal = c.strict_json(Path(selection.role('journal')).read_bytes())
    records = [c.strict_json(Path(pin['path']).read_bytes()) for pin in journal['records']]
    workers = [r for r in records if r['record_type'] == 'stage_checked' and r['payload']['cursor']['kind'] == 'worker']
    assert len(workers) == 3
    carry = c.strict_json(Path(selection.role('receipt_carry')).read_bytes())
    assert len(carry['unsupported_audit_candidates']) == 6
    assert carry['unanswered_paths'] == [] and carry['rejected_paths'] == []
    assert execute.read_final(case['raw']) == result
    assert result['scientific_acceptance'] == 'not_assessed'
    with pytest.raises(ValueError, match='new|resume'):
        execute.launch(case['raw'], **case['kwargs'])
