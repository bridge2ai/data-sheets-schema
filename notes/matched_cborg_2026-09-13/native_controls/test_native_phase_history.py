"""Offline checker results exercise native draft correction and terminal gates."""
from copy import deepcopy
import importlib
import json
from pathlib import Path
import shlex
import subprocess
import sys

from click.testing import CliRunner
import pytest
import yaml

from data_sheets_schema import chunking, evidence_assertions
from tests.test_evidence_generation_gate import specification
from tests.test_receipts import BUNDLE, FULL, _receipt
from native_phase_history import PhaseHistory, phase_history


def use(identity, name, **inputs):
    return {'type': 'assistant', 'message': {'content': [
        {'type': 'tool_use', 'id': identity, 'name': name, 'input': inputs}]}}


def response(identity, success, content=''):
    return {'type': 'user', 'message': {'content': [
        {'type': 'tool_result', 'tool_use_id': identity, 'is_error': not success, 'content': content}]}}


def command(spec, module, *args):
    return shlex.join([spec._agentic_toolchain['python'], '-m', module, *map(str, args)])


def receipt_args(spec):
    return ['--method', spec.method, '--label', spec.label, '--project', spec.project,
            '--bundle', str(spec.bundle), '--chunk-manifest', str(spec.chunk_manifest), '--strict']


def receipt_command(spec):
    return command(spec, 'data_sheets_schema.cli', '--manifest', 'none',
                   'receipts', 'check', *receipt_args(spec))


def derive_command(spec):
    return command(spec, 'data_sheets_schema.cli', 'derive', 'core',
                   '--full', spec.full_path, '--out', spec.core_path)


@pytest.fixture
def case(tmp_path, monkeypatch):
    spec = specification(tmp_path, 'Claude Code')
    spec.bundle.write_text(BUNDLE)
    manifest = chunking.build_manifest(spec.bundle)
    spec.chunk_manifest.write_text(chunking.dump_manifest(manifest))
    spec.full_path.parent.mkdir(parents=True, exist_ok=True)
    spec.full_path.write_text(yaml.safe_dump(FULL))
    receipt = Path(spec._agentic_artifact_paths['receipt'])
    original = _receipt(manifest['bundle_md5'])
    receipt.write_text(yaml.safe_dump(original))
    cli = importlib.import_module('data_sheets_schema.cli.receipts')
    monkeypatch.setattr(cli, '_run_paths', lambda *args: {
        'core_dir': spec.core_path.parent, 'full': spec.full_path,
        'provenance': spec.provenance_path})

    def check(value):
        receipt.write_text(yaml.safe_dump(value))
        result = CliRunner().invoke(cli.check, receipt_args(spec))
        assert result.exit_code in (0, 1), result.output
        return result

    return spec, original, check


def receipt_trace(spec, identity, result):
    return [use(identity, 'Bash', command=receipt_command(spec)),
            response(identity, result.exit_code == 0, result.output)]


def test_actual_failed_then_passing_receipt_allows_first_derive(case):
    spec, original, check = case
    bad = deepcopy(original)
    bad['chunks'][1]['extracted'][0]['slot'] = 'invented_field'
    failed = check(bad)
    passed = check(original)
    assert failed.exit_code == 1 and 'slot_not_in_record' in failed.output
    assert passed.exit_code == 0
    events = receipt_trace(spec, 'first', failed)
    events += [use('correction', 'Write', file_path=spec._agentic_artifact_paths['receipt'],
                   content=yaml.safe_dump(original)), response('correction', True)]
    events += receipt_trace(spec, 'second', passed)
    events += [use('derive', 'Bash', command=derive_command(spec)), response('derive', True)]
    result = phase_history(events, spec, complete=True)
    assert result['problems'] == []
    assert [row['success'] for row in result['phase1_receipt_checks']] == [False, True]
    assert result['phase2_completed'] and not result['terminal_failures']


def test_actual_reported_diagnostics_do_not_turn_success_into_terminal_failure(case):
    spec, original, check = case
    diagnostic = deepcopy(original)
    diagnostic['chunks'][1]['extracted'].append({'slot': 'title', 'snippet': 'AI'})
    passed = check(diagnostic)
    assert passed.exit_code == 0 and 'unattesting' in passed.output
    events = receipt_trace(spec, 'check', passed)
    events.append(use('derive', 'Bash', command=derive_command(spec)))
    result = phase_history(events, spec)
    assert result['problems'] == [] and result['receipt_gate_current']


@pytest.mark.parametrize('prefix', ['absent', 'pending', 'failed'])
def test_core_admission_requires_prior_success_not_scheduled_or_failed_check(case, prefix):
    spec, original, check = case
    events = []
    if prefix != 'absent':
        events.append(use('check', 'Bash', command=receipt_command(spec)))
    if prefix == 'failed':
        bad = deepcopy(original)
        bad['chunks'][1]['extracted'][0]['slot'] = 'absent'
        failed = check(bad)
        assert failed.exit_code == 1
        events.append(response('check', False, failed.output))
    events.append(use('derive', 'Bash', command=derive_command(spec)))
    assert any('precedes a passing receipt' in p for p in phase_history(events, spec)['problems'])


@pytest.mark.parametrize('artifact', ['full', 'receipt'])
def test_current_file_mutation_invalidates_success_until_rechecked(case, artifact):
    spec, original, check = case
    passed = check(original)
    events = receipt_trace(spec, 'check', passed)
    events += [use('edit', 'Write', file_path=spec._agentic_artifact_paths[artifact], content='new'),
               response('edit', True)]
    bad = phase_history(events + [use('derive', 'Bash', command=derive_command(spec))], spec)
    assert any('precedes a passing receipt' in p for p in bad['problems'])
    good = events + receipt_trace(spec, 'recheck', passed)
    good.append(use('derive', 'Bash', command=derive_command(spec)))
    assert phase_history(good, spec)['problems'] == []


def test_write_while_receipt_check_is_pending_cannot_be_covered_by_its_result(case):
    spec, original, check = case
    passed = check(original)
    events = [use('check', 'Bash', command=receipt_command(spec)),
              use('edit', 'Write', file_path=spec._agentic_artifact_paths['receipt'], content='new'),
              response('edit', True), response('check', True, passed.output),
              use('derive', 'Bash', command=derive_command(spec))]
    assert any('precedes a passing receipt' in p for p in phase_history(events, spec)['problems'])


def test_wrong_record_gate_or_missing_success_evidence_never_admits_core(case):
    spec, original, check = case
    passed = check(original)
    events = receipt_trace(spec, 'check', passed)
    events[0]['message']['content'][0]['input']['command'] = receipt_command(spec).replace(spec.label, 'another-run')
    assert phase_history(events, spec)['problems']
    events = receipt_trace(spec, 'check', passed)
    del events[1]['message']['content'][0]['is_error']
    events.append(use('derive', 'Bash', command=derive_command(spec)))
    assert any('precedes a passing receipt' in p for p in phase_history(events, spec)['problems'])


def test_actual_evidence_failure_stays_terminal_after_later_success(case, capsys):
    spec, _, _ = case
    directory = spec.core_path.parent / 'evidence'
    directory.mkdir()
    (directory / 'original_full.yaml').write_text('id: x\ntitle: Original\n')
    (directory / 'original_core.yaml').write_text('id: x\ntitle: Original\n')
    audit = directory / 'audit.json'
    audit.write_text(json.dumps({'findings': [{'severity': 'low', 'record': 'full',
        'slot': 'title', 'issue': 'Wrong quote', 'evidence': [{'artifact': 'original_full',
        'path': '/title', 'op': 'contains', 'quote': 'Absent passage'}]}], 'summary': 'Audit'}))
    args = ['--audit', str(audit), '--bundle', str(spec.bundle), '--manifest', str(spec.chunk_manifest),
            '--original-full', str(directory / 'original_full.yaml'),
            '--original-core', str(directory / 'original_core.yaml')]
    status = evidence_assertions.main(args)
    failed = capsys.readouterr().out
    assert status == 1 and 'artifact_assertion_contradicted' in failed
    audit.write_text(json.dumps({'findings': [], 'summary': 'Empty audit'}))
    assert evidence_assertions.main(args) == 0
    passed = capsys.readouterr().out
    cmd = command(spec, 'data_sheets_schema.evidence_assertions', *args)
    events = [use('audit', 'Bash', command=cmd), response('audit', False, failed),
              use('later', 'Bash', command=cmd), response('later', True, passed)]
    result = phase_history(events, spec)
    assert len(result['terminal_failures']) == 1
    assert len(result['continuation_after_terminal']) == 1
    assert result['problems']


def test_source_inventory_failure_is_terminal_but_ordinary_schema_error_is_not(case):
    spec, _, _ = case
    cmd = command(spec, 'data_sheets_schema.source_review', '--record', spec.full_path,
                  '--artifact', 'final_full')
    events = [use('schema', 'Bash', command='synthetic schema validator'), response('schema', False)]
    assert phase_history(events, spec)['problems'] == []
    events += [use('inventory', 'Bash', command=cmd), response('inventory', False)]
    assert phase_history(events, spec)['terminal_failures']


def test_partial_state_is_detached_and_does_not_require_a_completed_pair(case):
    spec, _, _ = case
    reviewer = PhaseHistory(spec)
    reviewer.observe(use('receipt-write', 'Write', file_path=spec._agentic_artifact_paths['receipt'], content='draft'))
    snapshot = reviewer.report()
    assert snapshot['problems'] == [] and snapshot['pending_tool_ids'] == ['receipt-write']
    snapshot['problems'].append('consumer mutation')
    # Native successful Write results may omit is_error; no checker pass is inferred.
    written = response('receipt-write', True)
    del written['message']['content'][0]['is_error']
    reviewer.observe(written)
    assert reviewer.report()['problems'] == []
    assert reviewer.report(complete=True)['problems'] == ['completed attempt has no successful core derivation']


def test_duplicate_results_and_pending_calls_cannot_be_complete_evidence(case):
    spec, original, check = case
    events = receipt_trace(spec, 'check', check(original))
    events.append(events[-1])
    assert phase_history(events, spec)['problems']
    events = [use('pending', 'Bash', command=receipt_command(spec))]
    assert phase_history(events, spec)['problems'] == []
    assert any('without results' in p for p in phase_history(events, spec, complete=True)['problems'])


def test_pending_write_cannot_be_attested_by_a_concurrent_receipt_check(case):
    spec, original, check = case
    events = [use('write', 'Write', file_path=spec._agentic_artifact_paths['receipt'], content='pending')]
    events += receipt_trace(spec, 'check', check(original))
    events += [response('write', True), use('derive', 'Bash', command=derive_command(spec))]
    assert any('precedes a passing receipt' in p for p in phase_history(events, spec)['problems'])


def test_informational_nonmapping_events_do_not_crash_or_establish_evidence(case):
    spec, _, _ = case
    events = [None, 'status', {'type': 'system', 'message': 'Initializing'},
              {'message': ['text']}, {'message': {'content': 'a string'}}]
    result = phase_history(events, spec)
    assert result['problems'] == [] and not result['receipt_gate_current']
    malformed = use('malformed', 'Bash')
    malformed['message']['content'][0]['input'] = 'invalid'
    assert phase_history([malformed], spec)['problems']


def test_relative_registered_paths_match_absolute_runtime_writes_from_another_cwd(case, tmp_path):
    spec, original, check = case
    passed = check(original)
    repository = tmp_path
    absolute = dict(spec._agentic_artifact_paths)
    spec._agentic_artifact_paths = {key: str(Path(value).relative_to(repository))
                                    for key, value in absolute.items()}
    events = receipt_trace(spec, 'check', passed)
    events += [use('edit', 'Write', file_path=absolute['receipt'], content='new'),
               response('edit', True), use('derive', 'Bash', command=derive_command(spec))]
    result = phase_history(events, spec, repository=repository)
    assert any('precedes a passing receipt' in p for p in result['problems'])


def test_optimized_interpreter_retains_selected_helper_argument_binding(case, tmp_path):
    spec, original, check = case
    events = receipt_trace(spec, 'check', check(original))
    events[0]['message']['content'][0]['input']['command'] = receipt_command(spec).replace(spec.label, 'wrong-label')
    payload = tmp_path / 'optimized-case.json'
    payload.write_text(json.dumps({'events': events, 'spec': spec.render_spec(),
                                   'project': spec.project, 'method': spec.method, 'label': spec.label}))
    code = '''import json, sys
from data_sheets_schema.api_runner import RunSpec
from native_phase_history import phase_history
case = json.load(open(sys.argv[1]))
spec = RunSpec.from_render_spec(case['spec'], project=case['project'], method=case['method'], label=case['label'])
result = phase_history(case['events'], spec)
print(json.dumps(result))
raise SystemExit(0 if result['problems'] and not result['receipt_gate_current'] else 1)
'''
    completed = subprocess.run([sys.executable, '-O', '-c', code, str(payload)],
                               capture_output=True, text=True)
    assert completed.returncode == 0, completed.stdout + completed.stderr


@pytest.mark.parametrize('background', [False, True])
def test_background_or_interrupted_success_is_not_a_completed_receipt_gate(case, background):
    spec, original, check = case
    events = receipt_trace(spec, 'check', check(original))
    if background:
        events[0]['message']['content'][0]['input']['run_in_background'] = True
        events[1]['tool_use_result'] = {'backgroundTaskId': 'pending-job', 'interrupted': False}
    else:
        events[1]['tool_use_result'] = {'interrupted': True}
    events.append(use('derive', 'Bash', command=derive_command(spec)))
    result = phase_history(events, spec)
    assert any('precedes a passing receipt' in p for p in result['problems'])


def test_new_receipt_invocation_invalidates_a_previous_success_until_it_finishes(case):
    spec, original, check = case
    passed = check(original)
    events = receipt_trace(spec, 'earlier', passed)
    events.append(use('latest', 'Bash', command=receipt_command(spec)))
    assert not phase_history(events, spec)['receipt_gate_current']
    premature = events + [use('derive', 'Bash', command=derive_command(spec))]
    assert any('precedes a passing receipt' in p for p in phase_history(premature, spec)['problems'])
    events += [response('latest', True, passed.output), use('derive', 'Bash', command=derive_command(spec))]
    assert phase_history(events, spec)['problems'] == []


@pytest.mark.parametrize('completion_order', ['earlier-only', 'latest-fails-first'])
def test_overlapping_receipt_results_cannot_revive_a_stale_pass(case, completion_order):
    spec, original, check = case
    passed = check(original)
    events = [use('earlier', 'Bash', command=receipt_command(spec)),
              use('latest', 'Bash', command=receipt_command(spec))]
    if completion_order == 'earlier-only':
        events.append(response('earlier', True, passed.output))
    elif completion_order == 'latest-fails-first':
        bad = deepcopy(original)
        bad['chunks'][1]['extracted'][0]['slot'] = 'nonexistent'
        failed = check(bad)
        assert failed.exit_code == 1
        events += [response('latest', False, failed.output), response('earlier', True, passed.output)]
    assert not phase_history(events, spec)['receipt_gate_current']
    events.append(use('derive', 'Bash', command=derive_command(spec)))
    assert any('precedes a passing receipt' in p for p in phase_history(events, spec)['problems'])


def test_latest_check_can_pass_after_earlier_check_has_settled(case):
    spec, original, check = case
    passed = check(original)
    events = [use('earlier', 'Bash', command=receipt_command(spec)),
              use('latest', 'Bash', command=receipt_command(spec)),
              response('earlier', True, passed.output), response('latest', True, passed.output),
              use('derive', 'Bash', command=derive_command(spec))]
    assert phase_history(events, spec)['problems'] == []


def test_latest_pass_waits_for_older_pending_check_then_allows_core(case):
    spec, original, check = case
    passed = check(original)
    events = [use('earlier', 'Bash', command=receipt_command(spec)),
              use('latest', 'Bash', command=receipt_command(spec)),
              response('latest', True, passed.output)]
    assert not phase_history(events, spec)['receipt_gate_current']
    premature = events + [use('derive', 'Bash', command=derive_command(spec))]
    assert any('precedes a passing receipt' in p for p in phase_history(premature, spec)['problems'])
    events.append(response('earlier', True, passed.output))
    assert phase_history(events, spec)['receipt_gate_current']
    events.append(use('derive', 'Bash', command=derive_command(spec)))
    assert phase_history(events, spec)['problems'] == []


@pytest.mark.parametrize('exit_key', ['exitCode', 'exit_code'])
def test_nonzero_receipt_exit_metadata_preserves_phase1_correction(case, exit_key):
    spec, original, check = case
    bad = deepcopy(original)
    bad['chunks'][1]['extracted'][0]['slot'] = 'absent_field'
    failed = check(bad)
    passed = check(original)
    assert failed.exit_code == 1 and passed.exit_code == 0
    events = receipt_trace(spec, 'first', failed)
    events[-1]['tool_use_result'] = {exit_key: failed.exit_code, 'interrupted': False}
    assert phase_history(events, spec)['problems'] == []
    events += [use('correction', 'Write', file_path=spec._agentic_artifact_paths['receipt'],
                   content=yaml.safe_dump(original)), response('correction', True)]
    events += receipt_trace(spec, 'second', passed)
    events += [use('derive', 'Bash', command=derive_command(spec)), response('derive', True)]
    result = phase_history(events, spec, complete=True)
    assert result['problems'] == [] and result['phase2_completed']
    assert [row['success'] for row in result['phase1_receipt_checks']] == [False, True]


@pytest.mark.parametrize('exit_key', ['exitCode', 'exit_code'])
def test_nonzero_evidence_exit_metadata_remains_terminal(case, exit_key):
    spec, _, _ = case
    cmd = command(spec, 'data_sheets_schema.source_review', '--record', spec.full_path,
                  '--artifact', 'final_full')
    events = [use('source', 'Bash', command=cmd), response('source', False)]
    events[-1]['tool_use_result'] = {exit_key: 1, 'interrupted': False}
    result = phase_history(events, spec)
    assert result['terminal_failures'] and result['problems']
