"""Saved-evidence reader tests for U0/#4354, 2026-11-06; no recorder/native run."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


SPEC = importlib.util.spec_from_file_location('u0_pair_analysis',
    Path(__file__).resolve().parents[1] / 'scripts/adhoc/analyze_native_u0_causal_pair_20261106.py')
analysis = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(analysis)


def saved(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(value, sort_keys=True).encode()
    path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def pin(path, raw=b'diagnostic source\n'):
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def fixture(tmp_path, label='control', *, complete=True, cpu=100):
    root = tmp_path / (label + '-source')
    trial = tmp_path / label
    observer_parent = tmp_path / 'observers'
    recorder = observer_parent / ('recorder-' + label)
    recorder.mkdir(parents=True)
    package = root / 'src/data_sheets_schema'
    init = pin(package / '__init__.py')
    helper = pin(root / 'scripts/adhoc/native_u0_source_closure_20261106.py')
    module = {'name': 'data_sheets_schema', 'file': init['path'], 'spec_origin': init['path'],
        'namespace': [str(package)], 'namespace_only': False, 'bytes': init['bytes'], 'sha256': init['sha256']}
    closure = {'root': str(root), 'package_root': str(package), 'ordinary_root_package': True,
        'project_finder_first': True, 'namespace_pruned': False, 'modules': [module],
        'project_module_count': 1, 'helper': helper, 'package_bootstrap': init}
    files = {str(Path(value['path']).relative_to(root)): {**value, 'committed_exact': True}
        for value in (init, helper)}
    fake_raw = b'# Invented fixture body without any marker\n'
    files['tests/fixtures/native_shared_execution/fake_cli.py'] = {
        'bytes': len(fake_raw), 'sha256': hashlib.sha256(fake_raw).hexdigest(), 'committed_exact': True}
    source = {'head': label + '-head', 'pristine': True, 'files': files}
    plan = {'cwd': str(root), 'command': ['/synthetic/python', '--tree', str(root)],
        'node': analysis.NODE, 'host_observation': {'observer_pid': 21}}
    outcome = {'source_unchanged': True, 'status': 'software_test_passed' if complete else 'software_test_failed',
        'cleanup_verified': True, 'child_pid': 20}
    saved(trial / 'source-before.json', source)
    saved(trial / 'source-after.json', source)
    saved(trial / 'plan.json', plan)
    saved(trial / 'outcome.json', outcome)
    wrapper = trial.with_name(trial.name + '.wrapper')
    saved(wrapper / 'plan.json', {'driver_pid': 19, 'observer_pid': 21})
    saved(wrapper / 'outcome.json', {'lock_released': True})
    (trial / 'host.jsonl').write_text(json.dumps({'kind': 'sample', 'sequence': 1, 'monotonic': 1,
        'at': '2026-11-06T00:00:00Z', 'cpu_percent': 70, 'logical_cpus': 4,
        'load': [5, 4, 3], 'processes': [{'pid': 99, 'ppid': 1, 'name': 'desktop', 'cpu_percent': 12},
            {'pid': 20, 'ppid': 19, 'name': 'test', 'cpu_percent': 80}]}) + '\n')
    target = 'schema_snapshot:_capture_native_schema'
    usage = {'thread_cpu_ns': cpu, 'process_cpu_ns': cpu + 20, 'ru_utime': cpu / 1e9, 'ru_stime': 0}
    documents = {'native_schema_member_visits': {'calls': 1, 'input_bytes': 14,
        'hash_counts': {'a' * 64: 1}, 'hash_coverage_complete': True, 'non_text_inputs': 0},
        'yaml:parse_started': {'calls': 1, 'input_bytes': 14,
            'hash_counts': {'a' * 64: 1}, 'hash_coverage_complete': True, 'non_text_inputs': 0}}
    rows = [{'event': 'observer_start', 'root': str(root), 'source_closure': closure,
                'helper': pin(root / 'scripts/adhoc/native_recorder_thread_cpu_20261106.py'),
                'python': {'executable': '/synthetic/python', 'version': '3.13 synthetic'},
                'source_pins': {init['path']: {k: init[k] for k in ('bytes', 'sha256')}}},
        {'event': 'phase_start', 'call': 1, 'target': target, 'phase': 'schema'},
        {'event': 'phase_end', 'call': 1, 'target': target, 'phase': 'schema', 'outcome': 'returns',
            'inclusive_rusage_delta': usage},
        {'event': 'counter_snapshot', 'valid': True,
            'stats': {target: {'calls': 1, 'returns': 1, 'unwinds': 0}}},
        {'event': 'thread_cpu_checkpoint', 'documents': documents, 'active_phases': [],
            'checkpoint': 1, 'reason': 'timer', 'treatment_cache': {'state': 'not_loaded'}, 'parser_inflight': 0}]
    if complete:
        rows.append({'event': 'observer_end', 'valid': True, 'source_closure': closure, 'changed_sources': []})
    write_rows(recorder, rows)
    case = trial / 'cases/test-node/native26'
    actual = {'state': 'completed_pending_independent_review' if complete else 'failed',
        'runtime_gates_passed': complete, 'scientific_acceptance': 'not_assessed',
        'gates': {'recorder': {'checked': True, 'passed': complete}}}
    saved(case / 'actual-result.json', actual)
    destination = case / 'record.yaml'
    if complete:
        destination.write_text('saved: record\n')
    saved(case / 'authority/composition-execution.json', {
        'policy': {'post_final_recorder': {'destination': str(destination)}}})
    peer = case / 'ordinary-python-test-peer'
    peer.write_bytes(b'#!/synthetic/python\n' + fake_raw)
    saved(case / 'authority/runtime-execution.json', {'deadline_seconds': 900,
        'executable': {'path': str(peer), 'sha256': hashlib.sha256(peer.read_bytes()).hexdigest(),
            'version': 'SYNTHETIC PYTHON SOFTWARE TEST'}})
    if complete:
        final = saved(case / 'native-evidence/final.json', actual)
        registration = saved(case / 'native-attempt/registration.json', {'synthetic': 'registration'})
        started = saved(case / 'native-attempt/started.json', {'synthetic': 'started'})
        saved(case / 'native-evidence/published.json', {'final_sha256': final,
            'registration_sha256': registration, 'started_sha256': started})
    (trial / 'pytest.xml').write_text('<testsuites><testsuite><testcase classname="tests.test_native_shared_execution" '
        'name="test_actual_public_correction_three_workers_and_saved_completion">'
        + ('' if complete else '<failure message="synthetic timeout"/>')
        + '</testcase></testsuite></testsuites>')
    return trial, observer_parent, recorder, rows


def write_rows(recorder, rows):
    for index, row in enumerate(rows, 1):
        row.update(sequence=index, elapsed_ns=index * 100, pid=123)
    (recorder / 'observer.jsonl').write_text(''.join(json.dumps(row) + '\n' for row in rows))


def add_second_observer(trial, recorder, rows, raw=b'common second observer\n'):
    relative = 'scripts/adhoc/native_recorder_second_cpu_20261106.py'
    root = Path(rows[0]['root'])
    extension = pin(root / relative, raw)
    rows[0]['second_observer'] = extension
    for name in ('source-before.json', 'source-after.json'):
        path = trial / name
        source = json.loads(path.read_bytes())
        source['files'][relative] = {**extension, 'committed_exact': True}
        saved(path, source)
    write_rows(recorder, rows)


@pytest.mark.parametrize('historical', [True, False])
def test_extension_instrumentation_mismatch_blocks_historical_or_changed_helper_comparison(tmp_path, historical):
    control, parent, c_recorder, c_rows = fixture(tmp_path)
    treatment, _, t_recorder, t_rows = fixture(tmp_path, 'treatment', cpu=30)
    if not historical:
        add_second_observer(control, c_recorder, c_rows, b'older extension bytes\n')
    add_second_observer(treatment, t_recorder, t_rows)
    a, b = analysis.analyze_trial(control, parent), analysis.analyze_trial(treatment, parent)
    assert a['observed_measurement_prefix_valid'] and b['observed_measurement_prefix_valid']
    result = analysis.compare(a, b)
    assert result['matching_native_schema_member_work']
    assert not result['matching_common_instrumentation_and_external_monitored_pins']
    assert not result['matched_completed_phase_observations']


def test_equal_extensions_in_distinct_roots_allow_comparison(tmp_path):
    control, parent, c_recorder, c_rows = fixture(tmp_path)
    treatment, _, t_recorder, t_rows = fixture(tmp_path, 'treatment', cpu=30)
    add_second_observer(control, c_recorder, c_rows)
    add_second_observer(treatment, t_recorder, t_rows)
    result = analysis.compare(analysis.analyze_trial(control, parent), analysis.analyze_trial(treatment, parent))
    assert result['matching_common_instrumentation_and_external_monitored_pins']
    assert result['matched_completed_phase_observations']


@pytest.mark.parametrize('mutation', ['sha', 'size', 'path', 'uncommitted'])
def test_extension_pin_must_match_its_committed_source_inventory(tmp_path, mutation):
    trial, parent, recorder, rows = fixture(tmp_path)
    add_second_observer(trial, recorder, rows)
    if mutation == 'sha':
        rows[0]['second_observer']['sha256'] = 'f' * 64
    elif mutation == 'size':
        rows[0]['second_observer']['bytes'] += 1
    elif mutation == 'path':
        rows[0]['second_observer']['path'] = str(Path(rows[0]['root']) / 'scripts/adhoc/other.py')
    else:
        for name in ('source-before.json', 'source-after.json'):
            path = trial / name
            source = json.loads(path.read_bytes())
            source['files']['scripts/adhoc/native_recorder_second_cpu_20261106.py']['committed_exact'] = False
            saved(path, source)
    write_rows(recorder, rows)
    result = analysis.analyze_trial(trial, parent)
    assert not result['observed_measurement_prefix_valid']
    assert any('second observer source inventory' in error for error in result['recorder']['errors'])


def test_one_saved_arm_canary_verifies_source_peer_record_and_counter_cutoffs(tmp_path):
    trial, parent, _, _ = fixture(tmp_path)
    result = analysis.analyze_trial(trial, parent)
    assert result['observed_measurement_prefix_valid'], result['errors']
    assert result['recorder']['source_closure_start']['verified']
    assert result['recorder']['source_closure_end']['verified']
    assert result['completion']['verified_synthetic_completion'], result['completion']
    assert result['completion']['synthetic_peer_verified']
    assert result['host_context']['samples'] == 1
    assert set(result['host_context']['competitors_at_least_10_percent']) == {'99 desktop'}
    assert result['recorder']['checkpoint_cutoff']['sequence'] == 5
    assert result['recorder']['phases']['latest_counter_snapshot']['sequence'] == 4


def test_pair_compares_only_equal_completed_work_and_preserves_partial_tail(tmp_path):
    control, parent, recorder, rows = fixture(tmp_path, complete=False, cpu=100)
    rows += [{'event': 'phase_start', 'call': 2, 'target': 'provenance:build_record', 'phase': 'record'},
        {'event': 'thread_cpu_checkpoint', 'documents': rows[-1]['documents'],
            'active_phases': [{'call': 2, 'target': 'provenance:build_record',
                'inclusive_rusage_delta': {'thread_cpu_ns': 500}}], 'checkpoint': 2}]
    write_rows(recorder, rows)
    treatment, _, _, _ = fixture(tmp_path, 'treatment', cpu=30)
    a, b = analysis.analyze_trial(control, parent), analysis.analyze_trial(treatment, parent)
    result = analysis.compare(a, b)
    assert result['matching_native_schema_member_work']
    comparison = result['matched_completed_phase_observations']['schema_snapshot:_capture_native_schema']
    assert comparison['inclusive_cpu_comparison']['thread_cpu_ns']['treatment_over_control'] == .3
    assert 'provenance:build_record' in result['excluded_phase_comparisons']
    assert not result['both_synthetic_completions_verified']
    assert not a['recorder']['complete_observer_valid']
    assert a['recorder']['phases']['partial_active_phases'][0]['call'] == 2


@pytest.mark.parametrize('mutation', ['invalid_counter', 'foreign_module', 'changed_inventory', 'wrong_members', 'changed_observer', 'changed_interpreter'])
def test_invalid_flags_or_work_mismatch_block_comparison(tmp_path, mutation):
    control, parent, _, _ = fixture(tmp_path)
    treatment, _, recorder, rows = fixture(tmp_path, 'treatment', cpu=30)
    if mutation == 'invalid_counter':
        rows[3]['valid'] = False
    elif mutation == 'foreign_module':
        rows[0]['source_closure']['modules'][0]['file'] = '/foreign/src/data_sheets_schema/__init__.py'
    elif mutation == 'wrong_members':
        rows[4]['documents']['native_schema_member_visits']['hash_counts'] = {'b' * 64: 1}
    elif mutation == 'changed_observer':
        rows[0]['helper']['sha256'] = 'e' * 64
    elif mutation == 'changed_interpreter':
        rows[0]['python']['version'] = '3.14 synthetic'
    else:
        path = treatment / 'source-after.json'
        value = json.loads(path.read_bytes())
        value['head'] = 'changed'
        saved(path, value)
    write_rows(recorder, rows)
    a, b = analysis.analyze_trial(control, parent), analysis.analyze_trial(treatment, parent)
    assert not analysis.compare(a, b)['matched_completed_phase_observations']
    if mutation == 'invalid_counter':
        assert b['recorder']['invalid_events'][0]['valid'] is False


def test_ambiguous_root_never_selects_newest_recorder(tmp_path):
    trial, parent, recorder, rows = fixture(tmp_path)
    other = parent / 'recorder-duplicate'
    other.mkdir()
    write_rows(other, copy.deepcopy(rows))
    result = analysis.analyze_trial(trial, parent)
    assert result['recorder'] is None
    assert not result['observed_measurement_prefix_valid']
    assert any('exactly one recorder' in str(error) for error in result['errors'])


def test_phase_detail_cap_never_produces_full_phase_comparison(tmp_path):
    control, parent, _, _ = fixture(tmp_path)
    treatment, _, recorder, rows = fixture(tmp_path, 'treatment')
    rows[3]['stats']['schema_snapshot:_capture_native_schema'].update(calls=600, returns=600)
    write_rows(recorder, rows)
    a, b = analysis.analyze_trial(control, parent), analysis.analyze_trial(treatment, parent)
    assert not analysis.compare(a, b)['matched_completed_phase_observations']


def test_saved_summary_is_exclusive_and_nonempty(tmp_path):
    trial, parent, _, _ = fixture(tmp_path)
    output = tmp_path / 'result.json'
    assert analysis.main(['--trial', str(trial), '--observer-parent', str(parent), '--out', str(output)]) == 0
    value = json.loads(output.read_bytes())
    assert value['single_arm']['completion']['verified_synthetic_completion']
    original = output.read_bytes()
    with pytest.raises(SystemExit):
        analysis.main(['--trial', str(trial), '--observer-parent', str(parent), '--out', str(output)])
    assert output.read_bytes() == original


def test_fake_peer_edit_and_missing_readback_do_not_count_as_completion(tmp_path):
    trial, parent, _, _ = fixture(tmp_path)
    peer = next((trial / 'cases').glob('**/ordinary-python-test-peer'))
    peer.write_bytes(peer.read_bytes() + b'# altered\n')
    result = analysis.analyze_trial(trial, parent)
    assert not result['completion']['synthetic_peer_verified']
    assert not result['same_run_readback_verified']


def test_unterminated_observer_tail_remains_invalid(tmp_path):
    trial, parent, recorder, _ = fixture(tmp_path)
    path = recorder / 'observer.jsonl'
    path.write_bytes(path.read_bytes() + b'{"event":')
    result = analysis.analyze_trial(trial, parent)
    assert result['recorder']['observer_jsonl']['bad_last_line']
    assert not result['observed_measurement_prefix_valid']
