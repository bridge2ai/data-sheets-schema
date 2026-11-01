# Purpose: negative/positive acceptance tests for the D76 evidence summarizer.
# Inputs: explicitly synthetic JSON ledgers built in tmp_path; outputs: pytest evidence.
# Serves #5213/D76 findings H2/H3; 2026-10-31. No provider/network/source writes.
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

SUMMARY = Path(__file__).with_name('summarize_d76_validation_20261031.py')
FINAL = '1' * 40
BASELINE = '2' * 40
NODES = ['tests/test_source_heading_runtime_api.py::test_synthetic_fixture'] + [
    'tests/synthetic_d76_summary.py::test_case_' + str(index) for index in range(1, 107)]


def write(path, value):
    path.write_text(json.dumps(value))


def make_run(root, name, *, head=FINAL, selected=None, omitted_call=False, failure=False,
             duplicate=False, invalid_source=False, denial=False, shard=None):
    directory = root / name
    directory.mkdir()
    selected = list(NODES if selected is None else selected)
    if duplicate:
        selected.append(selected[0])
    reports = []
    for index, node in enumerate(selected):
        for phase in ('setup', 'call', 'teardown'):
            if omitted_call and index == 0 and phase == 'call':
                continue
            reports.append({'nodeid': node, 'when': phase,
                'outcome': 'failed' if failure and index == 0 and phase == 'call' else 'passed',
                'xfail': None})
    write(directory / 'plan.json', {'head': head, 'collect_only': False, 'ci_ordinary_shard_of_4': shard})
    write(directory / 'nodes.json', {'collected': selected, 'selected': selected,
                                     'reports': reports, 'collection_errors': {}})
    write(directory / 'outcome.json', {'passed': not failure, 'collection_passed': False,
        'counts': {'passed': len(selected) - int(failure), 'failed': int(failure), 'errors': 0, 'skipped': 0},
        'node_accounting_complete': True, 'source_unchanged': not invalid_source,
        'hygiene_passed': True, 'origins_verified': True, 'helpers_unchanged': True,
        'targets_unchanged': True, 'sandbox_loaded': True, 'all_worker_collections_identical': True})
    if denial:
        (directory / 'guard-denials-synthetic.jsonl').write_text('{"event":"synthetic"}\n')
    return directory


def summarize(tmp_path, runs, *, historical=True, ci=None):
    output = tmp_path / 'summary.json'
    args = [sys.executable, '-S', '-P', '-B', str(SUMMARY), '--accepted-head', FINAL, '--output', str(output)]
    for run in runs:
        args += ['--run', str(run)]
    if historical:
        target = tmp_path / 'historical.json'
        write(target, NODES)
        args += ['--historical-targets', str(target)]
    if ci is not None:
        expected = tmp_path / 'expected-ci.json'
        write(expected, ci)
        args += ['--ci-expected', str(expected)]
    before = hashlib.sha256(SUMMARY.read_bytes()).hexdigest()
    result = subprocess.run(args, capture_output=True, text=True)
    assert output.is_file(), result.stderr
    assert hashlib.sha256(SUMMARY.read_bytes()).hexdigest() == before
    return result, json.loads(output.read_text())


def test_baseline_success_cannot_mask_final_failure(tmp_path):
    result, data = summarize(tmp_path, [make_run(tmp_path, 'baseline', head=BASELINE),
                                        make_run(tmp_path, 'final', failure=True)])
    assert result.returncode == 1 and data['acceptance_passed'] is False
    assert data['historical']['passed'] is False
    assert all(row['head'] == FINAL for row in data['historical']['rows'][0]['eligible_observations'])


def test_other_final_pass_cannot_mask_final_failure(tmp_path):
    result, data = summarize(tmp_path, [make_run(tmp_path, 'passed'), make_run(tmp_path, 'failed', failure=True)])
    assert result.returncode == 1 and data['historical']['passed'] is False


def test_missing_call_phase_is_not_historical_success(tmp_path):
    result, data = summarize(tmp_path, [make_run(tmp_path, 'missing', omitted_call=True)])
    assert result.returncode == 1
    assert data['historical']['nonpassing'] == [NODES[0]]


def test_ci_selection_shortfall_is_not_acceptance(tmp_path):
    result, data = summarize(tmp_path, [make_run(tmp_path, 'short', selected=NODES[:1], shard=1)],
                             historical=False, ci=NODES[:2])
    assert result.returncode == 1
    assert data['ci_partition']['missing'] == {NODES[1]: 1}
    assert data['ci_partition']['passed'] is False


def test_duplicate_selected_occurrences_each_have_three_phases(tmp_path):
    result, data = summarize(tmp_path, [make_run(tmp_path, 'duplicate', duplicate=True)])
    assert result.returncode == 0 and data['acceptance_passed'] is True
    assert data['historical']['passed'] is True
    assert data['runs'][0]['nonpassing_nodes'] == []
    assert data['historical']['rows'][0]['eligible_observations'][0]['selected_occurrences'] == 2


@pytest.mark.parametrize('defect', ['invalid_source', 'denial'])
def test_invalid_run_cannot_claim_107_passed(tmp_path, defect):
    result, data = summarize(tmp_path, [make_run(tmp_path, 'invalid', **{defect: True})])
    assert result.returncode == 1 and data['acceptance_passed'] is False
    assert data['historical']['passed'] is False
    assert len(data['historical']['nonpassing']) == 107


def test_ci_exact_duplicate_multiset_and_held_module_pass(tmp_path):
    expected = [NODES[0], NODES[1], NODES[0]]
    result, data = summarize(tmp_path, [make_run(tmp_path, 'ci', selected=NODES[:2], duplicate=True, shard=2)],
                             historical=False, ci=expected)
    assert result.returncode == 0 and data['acceptance_passed'] is True
    assert data['ci_partition']['passed'] is True
    assert data['ci_partition']['actual_occurrences'] == 3


def test_collection_rows_do_not_add_unstarted_tests_to_execution_totals(tmp_path):
    collection = make_run(tmp_path, 'collection')
    plan = json.loads((collection / 'plan.json').read_text())
    plan['collect_only'] = True
    write(collection / 'plan.json', plan)
    nodes = json.loads((collection / 'nodes.json').read_text())
    nodes['reports'] = []
    write(collection / 'nodes.json', nodes)
    outcome = json.loads((collection / 'outcome.json').read_text())
    outcome.update(passed=False, collection_passed=True, node_accounting_complete=False,
                   counts={'passed': 0, 'failed': 0, 'errors': 0, 'skipped': 0, 'not_started': 107})
    write(collection / 'outcome.json', outcome)
    result, data = summarize(tmp_path, [collection, make_run(tmp_path, 'execution')])
    assert result.returncode == 0 and data['acceptance_passed'] is True
    assert data['reported_counts_sum_includes_repeats']['passed'] == 107
    assert data['reported_counts_sum_includes_repeats'].get('not_started', 0) == 0
    assert data['runs'][0]['outcome']['counts']['not_started'] == 107
    assert len(data['historical']['rows'][0]['eligible_observations']) == 1
