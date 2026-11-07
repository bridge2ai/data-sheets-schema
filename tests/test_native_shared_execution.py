"""Real native26 public lifetime using ordinary Python and invented authority.

The model/permission/runtime observations below are expressly synthetic. All
stage, schema, receipt, attribution and recorder helper commands are genuine.
No paid provider, native binary, authentication or scientific claim is made.
"""
from dataclasses import replace
from copy import deepcopy
from pathlib import Path
from datetime import datetime, timezone
import json
import sys

import pytest

from tests.native_shared_fixture import build_native_fixture
from tests.test_native_shared_permissions import fabricated_manifest
from tests.test_native_execution import fake_observation
from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_controller as composition
from data_sheets_schema import native_shared_registration_orchestration as registration
from data_sheets_schema import native_shared_execution_orchestration as execute
from data_sheets_schema import native_shared_policy as policy
from data_sheets_schema import native_execution_authority_v2 as authority
from data_sheets_schema import native_execution_registration_v2 as preparation


def make_case(root, *, fixture='neutral', receipt_origin_version=0):
    if fixture == 'neutral':
        builder = build_native_fixture
    elif fixture == 'omission':
        from tests.native_shared_omission_fixture import build_native_fixture as builder
    else:
        raise ValueError('unknown synthetic native fixture')
    data = builder(root, registered_python=sys.executable)
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
    prepared = preparation.prepare(data['selection'].registration.pin.path, runtime_path,
        job_id='synthetic-native-execution', run_date='2026-10-05', max_draft_checks=3)
    preparation_raw = c.canonical(prepared)
    (parent / 'preparation-execution.json').write_bytes(preparation_raw)
    instruction = parent / 'instruction-execution.md'
    instruction.write_text(prepared['registration']['instruction'])
    selected = composition.compose(preparation_raw, instruction_path=instruction)
    _, spec, captured_selection = composition.reconstruct_composition(c.canonical(selected))
    assert captured_selection == data['selection']
    comp = parent / 'composition-execution.json'; comp.write_bytes(c.canonical(selected))
    (parent / 'synthetic-seeds.json').write_bytes(c.canonical({'full': data['full_raw'].decode(),
        'receipt': data['receipt_raw'].decode(), 'source_text': data['source_text'],
        'chunk_id': data['chunk_id'], 'correction': True, 'answer_fixture': fixture}))
    system = parent / 'system.txt'; system.write_text('Explicitly synthetic Python software test. No actual native or provider.\n')
    attempt = root / 'native-attempt'; output = root / 'native-evidence'
    dependencies = authority.dependency_identity()
    expected = registration.permission_expectation(runtime, selected, spec,
        system.read_text() + policy.command_guidance(selected['policy']), attempt / 'cli_config', dependencies)
    manifest = fabricated_manifest(expected, data['selection'].document(), root / 'invented-probe', spec.bundle.read_bytes())
    probe = parent / 'invented-permissions.json'; probe.write_bytes(c.canonical(manifest))
    envelope = registration.registration(comp, system, permission_probe_path=probe,
        attempt_id=attempt.name, attempt_directory=attempt, evidence_directory=output, max_draft_checks=3,
        receipt_origin_version=receipt_origin_version)
    raw = c.canonical(envelope)
    value = registration.verified(raw)
    binding = {'registration_sha256': c.sha(raw), 'attempt_id': value['attempt_id'],
        'source_commit': value['dependencies']['base']['source_commit'],
        'dependencies_sha256': c.sha(c.canonical(value['dependencies']))}
    review = {**binding, 'kind': 'd4d_native_execution_review_v2', 'version': 2,
        'reviewer': 'invented-independent-reviewer', 'author': 'invented-author',
        'independent': True, 'decision': 'approved', 'reviewed_at': 'synthetic-time',
        'evidence': 'Fabricated software test only; no actual review authority.'}
    # Fabricated offline CI declaration only: no workflow or Actions run was
    # requested or observed. Manual CI tests the exact source commit without
    # inventing a PR merge object; separate A3 tests cover real PR Git topology.
    workflow_event = 'workflow_dispatch'
    source_commit = binding['source_commit']
    # The canonical URL is schema-conforming synthetic data, never fetched and
    # never evidence that run 1 exists or ran these tests.
    details_url = preparation._ci_repository_url() + '/actions/runs/1'
    ci = {**binding, 'kind': 'd4d_native_execution_ci_v2', 'version': 2,
        'workflow_event': workflow_event, 'workflow_ref': 'refs/heads/synthetic-native-software-test',
        'tested_commit': source_commit,
        'workflow_sha256': preparation._workflow_sha(source_commit, source_commit, workflow_event), 'checks': {
        name: {'head_sha': binding['source_commit'], 'status': 'completed', 'conclusion': 'success',
            'details_url': details_url}
        for name in preparation.required_checks(workflow_event)}}
    review_path = parent / 'invented-review.json'; review_path.write_bytes(c.canonical(review))
    ci_path = parent / 'invented-ci.json'; ci_path.write_bytes(c.canonical(ci))
    word = {**binding, 'kind': 'd4d_native_execution_launch_authorization_v2', 'version': 2,
        'owner': 'invented-test-owner', 'authorized_at': 'synthetic-time', 'word': 'AUTHORIZE_ONE_NATIVE_ATTEMPT',
        'review_sha256': c.sha(review_path.read_bytes()), 'ci_sha256': c.sha(ci_path.read_bytes()),
        'permission_probe_sha256': value['permission_probe_sha256']}
    word_path = parent / 'invented-owner.json'; word_path.write_bytes(c.canonical(word))
    # Explicitly synthetic, launch-bound quota evidence. The production route
    # has no exemption for this ordinary-Python peer.
    from data_sheets_schema import native_subscription_guard as guard
    now = datetime.now(timezone.utc)
    event = c.canonical({'type': 'rate_limit_event', 'rate_limit_info': {
        'status': 'allowed', 'isUsingOverage': False, 'rateLimitType': 'seven_day',
        'utilization': 0.2, 'resetsAt': int(now.timestamp()) + 3600}})
    guard_raw = c.canonical({'kind': guard.KIND, 'version': 1,
        'registration_sha256': c.sha(raw), 'runtime_sha256': c.sha(c.canonical(runtime)),
        'launch_word_sha256': c.sha(word_path.read_bytes()),
        'max_starting_weekly_utilization': 0.8, 'max_age_seconds': 300,
        'captured_at': now.isoformat().replace('+00:00', 'Z'),
        'event_json': event.decode(), 'event_sha256': c.sha(event)})
    guard_path = parent / 'invented-subscription.json'; guard_path.write_bytes(guard_raw)
    return {**data, 'root': root, 'spec': spec, 'value': value, 'raw': raw,
        'kwargs': {'review_path': review_path, 'ci_path': ci_path, 'launch_word_path': word_path,
            'subscription_guard_path': guard_path, 'subscription_guard_sha256': c.sha(guard_raw)}}


def launch_case(case, monkeypatch):
    """Use the actual public lifetime; only runtime/review/provider data is synthetic."""
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
    return result


def assert_completed_case(case, result):
    """Both data variants require the same actual gates, readback and spent refusal."""
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
    assert result['subscription_observation_verification']['checked'] is True
    assert result['subscription_observation_verification']['complete'] is True
    # Rehashing a completed publication cannot turn invented lifecycle or
    # authority claims into a new successful saved read. No trial is rerun.
    evidence = Path(case['value']['evidence_directory'])
    final_path, marker_path = evidence/'final.json', evidence/'published.json'
    final_raw, marker_raw = final_path.read_bytes(), marker_path.read_bytes()
    for change in ('subscription_count', 'subscription_stop', 'authority_map'):
        forged = deepcopy(result)
        if change == 'subscription_count':
            forged['subscription_guard']['observed_rate_limit_events'] += 1
        elif change == 'subscription_stop':
            forged['subscription_guard']['stop_reason'] = 'invented saved stop'
        else:
            forged['authority']['review']['sha256'] = 'f' * 64
        changed_raw = c.canonical(forged)
        marker = c.strict_json(marker_raw)
        marker['final_sha256'] = c.sha(changed_raw)
        final_path.write_bytes(changed_raw)
        marker_path.write_bytes(c.canonical(marker))
        try:
            with pytest.raises(ValueError, match='subscription|authority'):
                execute.read_final(case['raw'])
        finally:
            final_path.write_bytes(final_raw)
            marker_path.write_bytes(marker_raw)
    assert result['scientific_acceptance'] == 'not_assessed'
    with pytest.raises(ValueError, match='new|resume'):
        execute.launch(case['raw'], **case['kwargs'])
    return records


def test_actual_public_correction_three_workers_and_saved_completion(tmp_path, monkeypatch):
    monkeypatch.chdir(authority.ROOT)
    case = make_case(tmp_path / 'native26')
    result = launch_case(case, monkeypatch)
    assert_completed_case(case, result)
