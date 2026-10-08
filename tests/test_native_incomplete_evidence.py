"""Stopped capture diagnostics, without native/provider execution or timing claims."""
from copy import deepcopy
import json
from types import SimpleNamespace

import pytest

from data_sheets_schema import api_runner as api
from data_sheets_schema import native_execution_gates as execution
from data_sheets_schema import native_supervisor_gates as neutral


@pytest.fixture
def captured(tmp_path, monkeypatch):
    """Use the actual incomplete-capture reader with a missing final artifact."""
    monkeypatch.chdir(tmp_path)
    full_schema, core_schema = tmp_path / 'full-schema.yaml', tmp_path / 'core-schema.yaml'
    for path in (full_schema, core_schema):
        path.write_text('name: invented_schema\n')
    monkeypatch.setattr(api, 'FULL_SCHEMA_PATH', full_schema)
    monkeypatch.setattr(api, 'CORE_SCHEMA_PATH', core_schema)
    attempt = tmp_path / 'attempt'
    attempt.mkdir()
    composition = tmp_path / 'composition.json'
    composition.write_text('{}\n')
    (attempt / 'transcript.jsonl').write_text(json.dumps({'type': 'system', 'subtype': 'init'}) + '\n')
    (attempt / 'control.jsonl').write_text('{}\n')
    (attempt / 'stderr.txt').write_text('Synthetic stopped capture\n')
    spec = SimpleNamespace(_agentic_artifact_paths={
        'full': tmp_path / 'missing-full.yaml', 'core': tmp_path / 'missing-core.yaml',
        'receipt': tmp_path / 'missing-receipt.yaml'}, bundle=tmp_path / 'missing-bundle.txt',
        chunk_manifest=tmp_path / 'missing-chunks.yaml')
    adapter = SimpleNamespace(spec=spec, state=SimpleNamespace(reg={'working_directory': str(tmp_path)}),
        policy={'post_final_recorder': {'destination': str(tmp_path / 'missing-provenance.json')}})
    return neutral.incomplete_capture(composition, attempt, adapter, 'original deadline stop')


def check(consumer, prepared):
    # Unrelated missing authorities fail independently; nothing here can launch
    # a child, purchase a response, or certify a complete native attempt.
    controls = {'run_direct_canary': SimpleNamespace()}
    options = {'exit_code': None, 'shutdown': {'control_initialized': True,
               'control_shutdown_complete': False, 'unfinished_control_workers': 1},
               'live': {}, 'first_stop': 'original deadline stop'}
    if consumer == 'neutral':
        return neutral.check(prepared, {}, {}, controls, **options)
    return execution.check(prepared, {}, {}, controls, **options,
                           runtime_authority={}, keep_awake={})


@pytest.mark.parametrize('consumer', ['neutral', 'execution'])
def test_actual_incomplete_capture_reports_unavailable_without_losing_other_gates(captured, consumer, monkeypatch):
    assert captured['replay_complete'] is False and captured['final_result'] is None
    assert captured['snapshot'].sealed
    original_problems = deepcopy(captured['capture_problems'])
    actual = check(consumer, captured)
    assert actual['evidence'] == {
        'checked': False, 'passed': False,
        'reason': 'final evidence unavailable: capture is explicitly incomplete',
        'result': None, 'capture_problems': original_problems}
    assert actual['first_stop'] == {'checked': True, 'passed': False, 'reason': 'original deadline stop'}
    assert actual['shutdown']['passed'] is False

    # Compare the remaining public gates against the exact previous expression,
    # using the same captured bytes and stop/shutdown evidence.
    def prior_evidence(prepared):
        return {'passed': prepared['final_result'].get('checked') is True
                and prepared['final_result'].get('findings') == [],
                'result': deepcopy(prepared['final_result'])}
    with monkeypatch.context() as patch:
        patch.setattr(neutral, 'final_evidence_gate', prior_evidence)
        previous = check(consumer, captured)
    assert previous['evidence']['checked'] is False
    assert previous['evidence']['reason'].startswith('AttributeError:')
    assert {key: row for key, row in actual.items() if key != 'evidence'} == {
        key: row for key, row in previous.items() if key != 'evidence'}
    if consumer == 'execution':
        assert set(actual) == set(execution.GATES)
        assert len(actual) == 15
    else:
        assert len(actual) == 13
    actual['evidence']['capture_problems'].append('caller mutation')
    assert captured['capture_problems'] == original_problems
    captured['capture_problems'].append('later caller mutation')
    assert actual['evidence']['capture_problems'] == original_problems + ['caller mutation']
    assert captured['final_result'] is None


@pytest.mark.parametrize('consumer', ['neutral', 'execution'])
@pytest.mark.parametrize('complete', [True, False])
@pytest.mark.parametrize('result,passed', [
    ({'checked': True, 'findings': [], 'context': {'source': ['invented']}}, True),
    ({'checked': False, 'findings': []}, False),
    ({'checked': True, 'findings': [{'reason': 'invented defect'}]}, False),
    ({'checked': 1, 'findings': []}, False),
    ({'checked': True, 'findings': None}, False),
    ({}, False),
])
def test_existing_mapping_semantics_and_detachment_unchanged(captured, consumer, complete, result, passed):
    captured.update(replay_complete=complete, final_result=deepcopy(result))
    actual = check(consumer, captured)['evidence']
    assert actual == {'checked': True, 'passed': passed, 'result': result}
    actual['result']['caller_mutation'] = True
    if 'context' in actual['result']:
        actual['result']['context']['source'].append('caller mutation')
    assert captured['final_result'] == result


@pytest.mark.parametrize('consumer', ['neutral', 'execution'])
@pytest.mark.parametrize('change', ['complete', 'missing_complete', 'zero_complete', 'null_complete',
    'string_complete', 'missing_result', 'list_result', 'false_result', 'string_result',
    'missing_problems', 'wrong_problems', 'wrong_problem_entry'])
def test_other_malformed_states_do_not_gain_an_incomplete_diagnostic(captured, consumer, change):
    if change == 'complete':
        captured['replay_complete'] = True
    elif change == 'missing_complete':
        del captured['replay_complete']
    elif change == 'zero_complete':
        captured['replay_complete'] = 0
    elif change == 'null_complete':
        captured['replay_complete'] = None
    elif change == 'string_complete':
        captured['replay_complete'] = 'false'
    elif change == 'missing_result':
        del captured['final_result']
    elif change == 'list_result':
        captured['final_result'] = []
    elif change == 'false_result':
        captured['final_result'] = False
    elif change == 'string_result':
        captured['final_result'] = 'unavailable'
    elif change == 'missing_problems':
        del captured['capture_problems']
    elif change == 'wrong_problems':
        captured['capture_problems'] = 'claimed stopped'
    elif change == 'wrong_problem_entry':
        captured['capture_problems'] = [{'claimed': 'stopped'}]
    actual = check(consumer, captured)['evidence']
    assert actual['checked'] is False and actual['passed'] is False
    assert not actual['reason'].startswith('final evidence unavailable:')
    assert 'capture_problems' not in actual
