"""Public offline request/registration/history boundaries for native drafts."""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys

import pytest

from data_sheets_schema import api_runner as api, native_source_attribution as policy
from data_sheets_schema import native_attribution_registration as offline
from data_sheets_schema import source_attribution_preflight as preflight
from tests.test_source_attribution_preflight import inputs, edited, claim
from tests.test_source_metadata_renderer import fixture as renderer_fixture

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def case(tmp_path, inputs):
    root = tmp_path / "run with ' quotes"; root.mkdir()
    for name, key in [('bundle.txt', 'bundle_raw'), ('chunks.yaml', 'chunk_manifest_raw'),
                      ('sources.yaml', 'source_manifest_raw')]:
        (root / name).write_bytes(inputs[key])
    spec = api.RunSpec(project='EXAMPLE', arm='baseline', method='claudecode_direct', label='neutral_fixture',
        condition='generic_v9', bundle=root / 'bundle.txt', chunk_manifest=root / 'chunks.yaml',
        manifest=root / 'sources.yaml', profile='neutral', render_version=16,
        runtime='Claude Code (direct)', provider='neutral provider', run_date='2026-10-02',
        out_dir=root / 'output', native_source_attribution_version=1, native_source_attribution_max_checks=3)
    spec.full_path.parent.mkdir()
    spec.full_path.write_bytes(inputs['record_raw']); spec.report_path.write_bytes(inputs['report_raw'])
    return spec, offline._encoded(offline.registration(spec)), inputs


def call(identity, command, **extras):
    return {'type': 'assistant', 'message': {'content': [
        {'type': 'tool_use', 'id': identity, 'name': 'Bash', 'input': {'command': command, **extras}}]}}


def result(identity, payload, status=0):
    text = json.dumps(payload)
    return {'type': 'user', 'tool_use_result': {'exitCode': status, 'stdout': text},
            'message': {'content': [{'type': 'tool_result', 'tool_use_id': identity,
                                     'is_error': bool(status), 'content': text}]}}


def write(identity, path):
    return {'type': 'assistant', 'message': {'content': [{'type': 'tool_use', 'id': identity,
            'name': 'Write', 'input': {'file_path': str(path), 'content': 'changed draft'}}]}}


def valid_events(spec):
    return [call('draft', shlex.join(policy.command_args(spec))),
            result('draft', preflight.check_files(**offline._arguments(spec)))]


@pytest.mark.parametrize('version', range(1, 25))
def test_every_existing_assembly_hash_is_exact(version):
    expected = json.loads((ROOT / 'tests/fixtures/native_attribution_legacy_assemblies.json').read_text())
    assert api.assembly_digest(version)['sha256'] == expected[str(version)]
    assert api.assembly_digest(version, native_source_attribution_version=0)['sha256'] == expected[str(version)]


@pytest.mark.parametrize('version', range(16, 24))
def test_opt_in_binds_selected_protocol_and_replays_without_changing_zero(tmp_path, version):
    old, _ = renderer_fixture(tmp_path, 'Claude Code')
    old = replace(old, render_version=version)
    zero = replace(old, native_source_attribution_version=0)
    assert old.instruction == zero.instruction and old.render_spec() == zero.render_spec()
    spec = replace(old, native_source_attribution_version=1, native_source_attribution_max_checks=2)
    assert spec.instruction != old.instruction
    assert policy.POLICY_PATH in spec.prompt_files
    assert spec.instruction.index(policy.MODULE) < spec.instruction.rindex(' -m data_sheets_schema.evidence_assertions ')
    assert api.NATIVE_EVIDENCE_STOP in spec.instruction
    assert api.assembly_digest(version, native_source_attribution_version=1) != api.assembly_digest(version)
    replay = api.RunSpec.from_render_spec(spec.render_spec(), project=spec.project, method=spec.method, label=spec.label)
    assert replay.instruction == spec.instruction
    assert policy.command_args(spec)[-4:] == ['--source-manifest', str(spec.manifest), '--project', 'EXAMPLE']
    expected = 5 if version < 18 else 6 if version < 20 else 7
    assert policy.command_args(spec)[policy.command_args(spec).index('--protocol-version') + 1] == str(expected)


@pytest.mark.parametrize('changes', [
    {'native_source_attribution_version': True}, {'native_source_attribution_version': '1'},
    {'native_source_attribution_version': 2}, {'native_source_attribution_max_checks': None},
    {'native_source_attribution_max_checks': 0}, {'native_source_attribution_max_checks': True},
    {'render_version': 15}, {'render_version': 24}, {'render_version': 25},
    {'runtime': 'Claude API (direct)'}, {'runtime': 'Codex CLI'}, {'native_source_attribution_version': 0},
])
def test_invalid_or_downgraded_selections_refuse(case, changes):
    with pytest.raises(ValueError):
        replace(case[0], **changes)


@pytest.mark.parametrize('change', ['missing_pin', 'wrong_pin', 'unknown_key', 'zero', 'missing_limit'])
def test_recorded_policy_cannot_be_dropped_or_forged(case, change):
    spec = case[0]; recorded = spec.render_spec()
    if change == 'missing_pin': recorded.pop('native_source_attribution_sha256')
    elif change == 'wrong_pin': recorded['native_source_attribution_sha256'] = '0' * 64
    elif change == 'unknown_key': recorded['native_source_attribution_secret_override'] = True
    elif change == 'zero': recorded['native_source_attribution_version'] = 0
    else: recorded.pop('native_source_attribution_max_checks')
    with pytest.raises(ValueError):
        api.RunSpec.from_render_spec(recorded, project=spec.project, method=spec.method, label=spec.label)


@pytest.mark.parametrize('selection', ['absent', 'unused'])
def test_unused_manifest_is_not_a_preflight_input(case, selection):
    spec = replace(case[0], **({'manifest': None} if selection == 'absent' else {'manifest_line': '# Source manifest: not used'}))
    assert '--source-manifest' not in policy.command_args(spec)
    assert 'source_manifest' not in offline.registration(spec)['inputs']


def test_actual_subprocess_command_passes_and_preserves_files(case):
    spec, raw, _ = case
    tracked = [spec.bundle, spec.chunk_manifest, spec.manifest, spec.full_path, spec.report_path]
    before = {p: p.read_bytes() for p in tracked}
    completed = subprocess.run(policy.command_args(spec), cwd=ROOT, capture_output=True, text=True)
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout)['passed'] is True
    assert {p: p.read_bytes() for p in tracked} == before
    verdict = offline.verify_history(raw, valid_events(spec))
    assert verdict['draft_gate_passed'] and verdict['execution'] == offline.EXECUTION
    assert verdict['observations'][-1]['verified_against_current_saved_bytes']


@pytest.mark.parametrize('mutation', ['wrong_path', 'extra_flag', 'wrong_interpreter', 'semicolon', 'background',
    'missing_result', 'duplicate_result', 'exit2', 'exit_bool', 'missing_exit', 'no_boolean_success',
    'wrong_hash', 'false_count', 'stdout_mismatch', 'wrong_result_id', 'pending_call', 'duplicate_call'])
def test_false_or_unsettled_draft_pass_cannot_satisfy_gate(case, mutation):
    spec, raw, _ = case; events = valid_events(spec)
    inputs = events[0]['message']['content'][0]['input']
    if mutation == 'wrong_path': inputs['command'] = inputs['command'].replace('--report ', '--report /another ')
    elif mutation == 'extra_flag': inputs['command'] += ' --write'
    elif mutation == 'wrong_interpreter': inputs['command'] = inputs['command'].replace(sys.executable, '/wrong/python')
    elif mutation == 'semicolon': inputs['command'] += '; true'
    elif mutation == 'background': inputs['run_in_background'] = True
    elif mutation == 'missing_result': events.pop()
    elif mutation == 'duplicate_result': events.append(deepcopy(events[-1]))
    elif mutation == 'exit2': events[-1]['tool_use_result']['exitCode'] = 2
    elif mutation == 'exit_bool': events[-1]['tool_use_result']['exitCode'] = False
    elif mutation == 'missing_exit': events[-1].pop('tool_use_result')
    elif mutation == 'no_boolean_success': events[-1]['message']['content'][0]['is_error'] = None
    elif mutation in ('wrong_hash', 'false_count'):
        payload = json.loads(events[-1]['message']['content'][0]['content'])
        if mutation == 'wrong_hash': payload['input_sha256']['report'] = '0' * 64
        else: payload['counts']['claims_examined'] += 1
        events[-1] = result('draft', payload)
    elif mutation == 'stdout_mismatch': events[-1]['tool_use_result']['stdout'] = '{}'
    elif mutation == 'wrong_result_id': events[-1]['message']['content'][0]['tool_use_id'] = 'other'
    elif mutation == 'pending_call': events.insert(0, call('pending', 'echo waiting'))
    elif mutation == 'duplicate_call': events.insert(1, deepcopy(events[0]))
    out = offline.verify_history(raw, events)
    assert not out['draft_gate_passed'], (mutation, out)


def test_failed_draft_correction_can_pass_but_terminal_failure_cannot(case):
    spec, raw, inputs = case
    bad = edited(inputs, lambda review: claim(review).update(attributed_to=['project_documentation']))
    failure = preflight.check_bytes(**bad)
    assert not failure['passed']
    events = [call('bad', shlex.join(policy.command_args(spec))), result('bad', failure, 1),
              write('correction', spec.report_path), result('correction', {})] + valid_events(spec)
    assert offline.verify_history(raw, events)['draft_gate_passed']
    terminal_command = next(c for c, kind in offline._commands(spec).items() if kind == 'evidence')
    events = [call('terminal', terminal_command), result('terminal', {}, 1)] + valid_events(spec)
    out = offline.verify_history(raw, events)
    assert not out['draft_gate_passed'] and out['terminal_failure_observed']


def test_write_then_exact_restore_invalidates_old_pass_but_new_check_can_pass(case):
    spec, raw, _ = case
    before = spec.report_path.read_bytes()
    events = valid_events(spec) + [write('rewrite', spec.report_path), result('rewrite', {})]
    spec.report_path.write_bytes(b'changed'); spec.report_path.write_bytes(before)
    assert not offline.verify_history(raw, events)['draft_gate_passed']
    new = valid_events(spec)
    new[0]['message']['content'][0]['id'] = 'again'
    new[1]['message']['content'][0]['tool_use_id'] = 'again'
    assert offline.verify_history(raw, events + new)['draft_gate_passed']


def test_finite_limit_and_protected_writes_refuse(case):
    spec, raw, _ = case
    events = []
    for i in range(4):
        payload = preflight.check_files(**offline._arguments(spec))
        events += [call(str(i), shlex.join(policy.command_args(spec))), result(str(i), payload)]
    assert not offline.verify_history(raw, events)['draft_gate_passed']
    for target in (spec.bundle, spec.full_path, spec.core_path, spec.manifest):
        assert not offline.verify_history(raw, valid_events(spec) + [write('write', target), result('write', {})])['draft_gate_passed']


def test_registration_drift_duplicate_keys_no_overwrite_and_execution_refusal(case, tmp_path, monkeypatch):
    spec, raw, _ = case
    registration = json.loads(raw); registration['max_draft_checks'] += 1
    with pytest.raises(ValueError): offline.verified(offline._encoded(registration))
    with pytest.raises(ValueError): offline.verified(raw.replace(b'"schema_version": 1', b'"schema_version": 1, "schema_version": 1'))
    dest = tmp_path / 'registration.json'; dest.write_bytes(b'preserve')
    with pytest.raises(FileExistsError): offline.write_registration(spec, dest)
    assert dest.read_bytes() == b'preserve'
    monkeypatch.setattr(api, "_client", lambda: pytest.fail("offline registration constructed a provider client"))
    for execute in (api.execute, api._execute):
        with pytest.raises(ValueError, match='offline-only'):
            execute(spec, **({'resume': False, 'client': None} if execute is api._execute else {}))
    spec.bundle.write_bytes(spec.bundle.read_bytes() + b'\n')
    with pytest.raises(ValueError): offline.verified(raw)


@pytest.mark.parametrize('version', range(19, 25))
@pytest.mark.parametrize('private', [False, True])
def test_historical_execution_refusal_precedes_new_axis_access(version, private, monkeypatch):
    class HistoricalRefusedSpec:
        render_version = version
        _replay_only = False

        @property
        def native_source_attribution_version(self):
            pytest.fail('historical renderer refusal inspected a new opt-in field')

    monkeypatch.setattr(api, '_exclusive_run', lambda *a, **k: pytest.fail('output lock reached'))
    monkeypatch.setattr(api, '_client', lambda *a, **k: pytest.fail('provider client reached'))
    expected = 'offline only' if version == 24 else 'separately registered audit continuation'
    with pytest.raises(ValueError, match=expected):
        (api._execute if private else api.execute)(HistoricalRefusedSpec(), resume=False, client=None)


@pytest.mark.parametrize('version', range(16, 19))
@pytest.mark.parametrize('private', [False, True])
def test_new_axis_still_refuses_before_any_execution_side_effect(case, version, private, monkeypatch):
    spec = replace(case[0], render_version=version)
    monkeypatch.setattr(api, '_exclusive_run', lambda *a, **k: pytest.fail('output lock reached'))
    monkeypatch.setattr(api, '_client', lambda *a, **k: pytest.fail('provider client reached'))
    with pytest.raises(ValueError, match='native source attribution is offline-only'):
        (api._execute if private else api.execute)(spec, resume=False, client=None)


def test_actual_prepare_cli_is_offline_and_preserves_existing_file(case, tmp_path):
    spec = case[0]; dest = tmp_path / 'prepared.json'
    args = [sys.executable, '-m', 'data_sheets_schema.native_attribution_registration', 'prepare',
        '--project', spec.project, '--method', spec.method, '--label', spec.label,
        '--bundle', str(spec.bundle), '--chunk-manifest', str(spec.chunk_manifest),
        '--source-manifest', str(spec.manifest), '--render-version', '16',
        '--run-date', '2026-10-02', '--max-draft-checks', '3', '--out', str(dest)]
    completed = subprocess.run(args, cwd=ROOT, text=True, capture_output=True)
    assert completed.returncode == 0, (completed.stdout, completed.stderr)
    raw = dest.read_bytes(); offline.verified(raw)
    assert subprocess.run(args, cwd=ROOT, capture_output=True).returncode == 2
    assert dest.read_bytes() == raw


def test_actual_old_launcher_refuses_new_registration_before_any_launch_action(case, tmp_path):
    spec, raw, _ = case
    directory = tmp_path / 'old launcher probe'; directory.mkdir()
    registration = directory / 'registration.json'; registration.write_bytes(raw)
    digest = hashlib.sha256(raw).hexdigest()
    value = json.loads(raw)
    (directory / 'review.json').write_text(json.dumps({'verdict': 'approve', 'ci_conclusion': 'success',
        'registration_sha256': digest, 'allowed_jobs': ['fixture_job'], 'ci_head': value['code_commit'],
        'ci_run_id': 1, 'independent_review_sha256': 'a' * 64}))
    (directory / 'word.json').write_text(json.dumps({'registration_sha256': digest,
                                                    'exact_response': 'offline fixture only'}))
    before = {p: p.read_bytes() for p in directory.iterdir()}
    program = r'''
import runpy,sys,subprocess
from pathlib import Path
root,folder=map(Path,sys.argv[1:])
sys.path.insert(0,str(root/'notes/claudecode_direct'))
ns=runpy.run_path(str(root/'notes/claudecode_direct/run_direct_canary.py'))
g=ns['main'].__globals__
def trap(*args,**kwargs): raise AssertionError('old launcher reached authentication, transport or child execution')
g['verify_environment']=lambda: None
for module,name in [(g['preparation'],'auth_evidence'),(g['native'],'execute_child'),
                    (subprocess,'Popen'),(subprocess,'check_output')]:
    setattr(module,name,trap)
try:
    ns['main'](['--registration',str(folder/'registration.json'),'--review',str(folder/'review.json'),
                '--job','fixture_job','--launch-word',str(folder/'word.json')])
except g['BudgetStop'] as error:
    assert str(error)=='not a direct-arm registration',str(error)
    print(str(error))
else: raise AssertionError('old launcher admitted new registration')
'''
    completed = subprocess.run([sys.executable, '-c', program, str(ROOT), str(directory)],
                               cwd=ROOT, capture_output=True, text=True)
    assert completed.returncode == 0, (completed.stdout, completed.stderr)
    assert 'not a direct-arm registration' in completed.stdout
    assert {p: p.read_bytes() for p in directory.iterdir()} == before


@pytest.mark.parametrize('mutation', ['rewrite_during_check', 'newer_failure', 'unknown_tool', 'wrong_terminal_args'])
def test_temporal_and_terminal_cross_axis_failures(case, mutation):
    spec, raw, _ = case; events = valid_events(spec)
    if mutation == 'rewrite_during_check':
        events.insert(1, write('overlap', spec.report_path))
        events.insert(2, result('overlap', {}))
    elif mutation == 'newer_failure':
        events.insert(1, call('newer', shlex.join(policy.command_args(spec))))
        events.insert(2, result('newer', {'checked': False, 'passed': False}, 2))
    elif mutation == 'unknown_tool':
        event = write('unknown', spec.report_path)
        event['message']['content'][0]['name'] = 'UnregisteredEditor'
        events += [event, result('unknown', {})]
    else:
        command = next(c for c,k in offline._commands(spec).items() if k == 'final_evidence')
        events += [call('terminal', command + ' --extra'), result('terminal', {})]
    assert not offline.verify_history(raw, events)['draft_gate_passed']


def test_changed_saved_report_and_protocol_identity_refuse(case):
    spec, raw, _ = case; events = valid_events(spec)
    spec.report_path.write_bytes(spec.report_path.read_bytes() + b'\nextra draft bytes')
    assert not offline.verify_history(raw, events)['draft_gate_passed']
    assert not offline.verify_history(raw, [call('final', next(c for c,k in offline._commands(spec).items()
                                                                if k == 'final_evidence')), result('final', {})])['draft_gate_passed']


def test_boolean_counter_and_float_checker_counts_are_not_equal_authority(case):
    spec, raw, _ = case
    single = replace(spec, native_source_attribution_max_checks=1)
    registration = offline.registration(single); registration['max_draft_checks'] = True
    with pytest.raises(ValueError): offline.verified(offline._encoded(registration))
    events = valid_events(spec)
    payload = json.loads(events[-1]['message']['content'][0]['content'])
    payload['counts']['claims_examined'] = float(payload['counts']['claims_examined'])
    events[-1] = result('draft', payload)
    assert not offline.verify_history(raw, events)['draft_gate_passed']


@pytest.mark.parametrize('alias', ['exitCode', 'exit_code'])
@pytest.mark.parametrize('value', [False, 0.0, None, '0', 1])
def test_every_supplied_exit_alias_must_be_the_same_integer(case, alias, value):
    spec, raw, _ = case
    events = valid_events(spec)
    events[-1]['tool_use_result'].update(exitCode=0, exit_code=0)
    events[-1]['tool_use_result'][alias] = value
    out = offline.verify_history(raw, events)
    assert not out['draft_gate_passed']
    assert not out['observations'][0]['verified_against_current_saved_bytes']


@pytest.mark.parametrize('field,value', [('checked', 1), ('checked', 1.0),
                                        ('claims_examined', True), ('claims_examined', 1.0)])
def test_stdout_requires_type_preserving_checker_equality(case, field, value):
    spec, raw, _ = case
    events = valid_events(spec)
    stdout = json.loads(events[-1]['tool_use_result']['stdout'])
    target = stdout['counts'] if field == 'claims_examined' else stdout
    target[field] = value
    events[-1]['tool_use_result']['stdout'] = json.dumps(stdout)
    out = offline.verify_history(raw, events)
    assert not out['draft_gate_passed']
    assert not out['observations'][0]['verified_against_current_saved_bytes']
    assert any('stdout disagree' in p for p in out['problems'])


def test_matching_integer_aliases_and_reordered_stdout_remain_valid(case):
    spec, raw, _ = case
    events = valid_events(spec)
    meta = events[-1]['tool_use_result']
    meta['exit_code'] = 0
    meta['stdout'] = json.dumps(json.loads(meta['stdout']), sort_keys=True, indent=4)
    assert offline.verify_history(raw, events)['draft_gate_passed']


def test_policy_drift_does_not_change_legacy_and_refuses_new_output(case, tmp_path, monkeypatch):
    legacy = replace(case[0], native_source_attribution_version=0, native_source_attribution_max_checks=None)
    expected = legacy.instruction
    monkeypatch.setattr(policy, 'POLICY_SHA256', '0' * 64)
    assert replace(legacy).instruction == expected
    target = tmp_path / 'must-not-exist.json'
    with pytest.raises(ValueError, match='frozen SHA256'):
        offline.write_registration(case[0], target)
    assert not target.exists()


def test_registration_will_not_add_itself_to_the_captured_checker_tree(case):
    target = ROOT / 'src/data_sheets_schema/never-written-offline-registration.json'
    with pytest.raises(ValueError, match='checker source tree'):
        offline.write_registration(case[0], target)
    assert not target.exists()


@pytest.mark.parametrize('typed_stdout_mismatch', [False, True])
def test_history_cli_reads_actual_saved_events_without_authorizing_execution(case, tmp_path, typed_stdout_mismatch):
    spec, raw, _ = case
    registration = tmp_path / 'registration.json'; registration.write_bytes(raw)
    history = valid_events(spec)
    if typed_stdout_mismatch:
        payload = json.loads(history[-1]['tool_use_result']['stdout'])
        payload['checked'] = 1
        history[-1]['tool_use_result']['stdout'] = json.dumps(payload)
    events = tmp_path / 'events.json'; events.write_text(json.dumps(history))
    before = {registration: raw, events: events.read_bytes(), spec.report_path: spec.report_path.read_bytes()}
    proc = subprocess.run([sys.executable, '-m', 'data_sheets_schema.native_attribution_registration',
        'verify-history', '--registration', str(registration), '--events', str(events)],
        cwd=ROOT, capture_output=True, text=True)
    assert proc.returncode == int(typed_stdout_mismatch), (proc.stdout, proc.stderr)
    report = json.loads(proc.stdout)
    assert report['draft_gate_passed'] is not typed_stdout_mismatch
    assert report['execution'] == offline.EXECUTION
    assert {p: p.read_bytes() for p in before} == before
