"""Real native26 public lifetime using ordinary Python and invented authority.

The model/permission/runtime observations below are expressly synthetic. All
stage, schema, receipt, attribution and recorder helper commands are genuine.
No paid provider, native binary, authentication or scientific claim is made.
"""
from dataclasses import replace
from copy import deepcopy
from pathlib import Path
import json
import sys

import pytest

from tests.native_shared_fixture import build_native_fixture
from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_controller_orchestration as composition
from data_sheets_schema import native_shared_registration_orchestration as registration
from data_sheets_schema import native_shared_execution_orchestration as execute
from data_sheets_schema import native_shared_policy as policy
from data_sheets_schema import native_execution_authority_v2 as authority
from data_sheets_schema import native_execution_registration_v2 as preparation
from tests.utils.native_shared_consumer_scope import command_guidance, observe_consumer_calls
from tests.utils.native_synthetic_evidence import runtime_for, bound_permission_for, authority_for


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
    runtime = runtime_for(data, root)
    runtime_path = parent / 'runtime-execution.json'; runtime_path.write_bytes(c.canonical(runtime))
    with authority.launch_derivations():
        prepared = preparation.prepare_synthetic(data['selection'].registration.pin.path, runtime_path,
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
            system.read_text() + command_guidance(selected['policy']), attempt / 'cli_config', dependencies)
        probe = bound_permission_for(expected, data['selection'].document(), spec.bundle.read_bytes())
        envelope = registration.synthetic_registration(comp, system, permission_probe_path=probe,
            attempt_id=attempt.name, attempt_directory=attempt, evidence_directory=output, max_draft_checks=3,
            receipt_origin_version=receipt_origin_version)
        raw = c.canonical(envelope)
        value = registration.verified(raw)
        binding = {'registration_sha256': c.sha(raw), 'attempt_id': value['attempt_id'],
            'source_commit': value['dependencies']['base']['source_commit'],
            'dependencies_sha256': c.sha(c.canonical(value['dependencies']))}
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
        ci_path = parent / 'invented-ci.json'; ci_path.write_bytes(c.canonical(ci))
        kwargs = authority_for(raw, ci_path, parent)
    return {**data, 'root': root, 'spec': spec, 'value': value, 'raw': raw,
        'kwargs': kwargs}


def launch_case(case, monkeypatch):
    """Use the actual public lifetime; only runtime/review/provider data is synthetic."""
    forbidden = {key: () for key in (
        ('prepare_direct', 'auth_evidence'), ('run_direct_canary', 'main'),
        ('run_api_canary', 'main'), ('budgeted_cborg', 'cborg_client'))}
    with observe_consumer_calls(forbidden, forbid=True):
        result = execute.synthetic_launch(case['raw'], **case['kwargs'])
    (case['root'] / 'actual-result.json').write_bytes(c.canonical(result))
    return result


def assert_completed_case(case, result):
    """Both data variants require the same actual gates, readback and spent refusal."""
    assert result['runtime_gates_passed'], json.dumps(result, indent=2)
    assert result['profile'] == 'synthetic-software-test'
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
        execute.synthetic_launch(case['raw'], **case['kwargs'])
    return records


def test_actual_public_correction_three_workers_and_saved_completion(tmp_path, monkeypatch):
    monkeypatch.chdir(authority.ROOT)
    case = make_case(tmp_path / 'native26')
    result = launch_case(case, monkeypatch)
    assert_completed_case(case, result)
