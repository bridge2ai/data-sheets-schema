"""Synthetic saved-event boundary proofs for U0/#4354, 2026-11-06; no trial."""
import importlib.util
import json
from pathlib import Path

import pytest


SPEC = importlib.util.spec_from_file_location('u0_phase_local',
    Path(__file__).resolve().parents[1] / 'scripts/adhoc/compare_native_u0_phase_local_20261106.py')
helper = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(helper)
CAPTURE = 'schema_snapshot:_capture_native_schema'
SCHEMA = 'audit_omissions:_schema_yaml'
PHASE = 'native_shared_capture:live_provenance_block'


def doc(count, letter='a'):
    return {'calls': count, 'input_bytes': count * 12, 'hash_counts': {letter * 64: count} if count else {},
        'hash_coverage_complete': True, 'non_text_inputs': 0}


def checkpoint(member, schema, parser=0):
    return {'event': 'thread_cpu_checkpoint', 'documents': {
        'native_schema_member_visits': doc(member), SCHEMA: doc(schema, 'b'),
        'yaml:parse_started': doc(parser, 'c')}}


def start(call, target):
    return {'event': 'phase_start', 'call': call, 'target': target, 'phase': target}


def end(call, target, cpu=100):
    return {'event': 'phase_end', 'call': call, 'target': target, 'phase': target,
        'outcome': 'returns', 'inclusive_rusage_delta': {'thread_cpu_ns': cpu,
            'process_cpu_ns': cpu + 2, 'ru_utime': cpu / 1e9, 'ru_stime': .000000002}}


def write_rows(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    for sequence, row in enumerate(rows, 1):
        row.update(sequence=sequence, elapsed_ns=sequence * 1000, pid=999)
    path.write_text(''.join(json.dumps(row) + '\n' for row in rows))
    return helper.reader.observer_events(path)[1]['artifact']


def arm(tmp_path, label, *, extra=1, cpu=100):
    root = str(tmp_path / (label + '-source'))
    rows = [{'event': 'observer_start', 'root': root,
             'targets': [{'id': target} for target in (PHASE, CAPTURE, SCHEMA, 'yaml:parse')]},
        checkpoint(0, 0), start(1, PHASE), start(2, CAPTURE), checkpoint(1, 0, 1), end(2, CAPTURE),
        start(3, SCHEMA), checkpoint(1, 1, 2), end(3, SCHEMA), end(1, PHASE, cpu), checkpoint(1, 1, 2)]
    for index in range(extra):
        rows += [start(4 + index, CAPTURE), checkpoint(2 + index, 1, 3 + index), end(4 + index, CAPTURE)]
    rows.append({'event': 'counter_snapshot', 'valid': True, 'stats': {
        PHASE: {'calls': 1, 'returns': 1, 'unwinds': 0},
        CAPTURE: {'calls': 1 + extra, 'returns': 1 + extra, 'unwinds': 0},
        SCHEMA: {'calls': 1, 'returns': 1, 'unwinds': 0}}})
    path = tmp_path / label / 'observer.jsonl'
    artifact = write_rows(path, rows)
    return {'source_root': root, 'observed_measurement_prefix_valid': True,
        'source_preservation_verified': True, 'recorder': {'observer_jsonl': {'artifact': artifact}}}, rows


def pair(tmp_path):
    control, c_rows = arm(tmp_path, 'control', extra=1, cpu=100)
    treatment, t_rows = arm(tmp_path, 'treatment', extra=2, cpu=30)
    return {'comparison': {'matching_common_instrumentation_and_external_monitored_pins': True,
        'distinct_source_roots_and_heads': True, 'matching_native_schema_member_work': False},
        'control': control, 'treatment': treatment}, c_rows, t_rows


def repin(arm_value, rows):
    path = Path(arm_value['recorder']['observer_jsonl']['artifact']['path'])
    arm_value['recorder']['observer_jsonl']['artifact'] = write_rows(path, rows)


def phase(result):
    return next(row for row in result['compared_completed_calls'] if row['target'] == PHASE)


def test_phase_local_canary_preserves_global_gate_and_proves_completed_work(tmp_path):
    value, _, _ = pair(tmp_path)
    result = helper.supplement(value)
    assert result['global_analyzer_gate_unchanged'] is False
    row = phase(result)
    assert row['inclusive_cpu_comparison']['thread_cpu_ns']['treatment_over_control'] == .3
    for arm_name in ('control', 'treatment'):
        work = row[arm_name]['work']
        assert work['native_schema_member_visits']['delta'] == doc(1)
        assert work[SCHEMA]['delta'] == doc(1, 'b')
        assert work['native_schema_member_visits']['entry']['value'] == doc(0)
        assert work['native_schema_member_visits']['exit']['value'] == doc(1)
    assert any(row['reason'] == 'completed call absent in one arm'
               for row in result['excluded_calls'] if 'reason' in row)


def test_snapshot_on_wrong_side_of_a_producing_entry_is_not_used(tmp_path):
    value, rows = arm(tmp_path, 'single', extra=0)
    saved = helper.load_arm(value)
    begin = next(row for row in rows if row.get('call') == 2 and row['event'] == 'phase_start')
    result = saved.boundary('native_schema_member_visits', begin, entry=True)
    assert result['verified']
    assert result['value'] == doc(0), 'capture-entry document increment must remain inside the phase'
    assert result['snapshot_sequences'] == [2]


def test_intervening_starts_without_boundary_snapshot_are_refused(tmp_path):
    value, rows = arm(tmp_path, 'single', extra=0)
    # Counter updates occur both before and after PHASE's entry; neither saved
    # snapshot observes its exact boundary, so extrapolation would fabricate work.
    rows = [rows[0], checkpoint(0, 0), start(2, CAPTURE), end(2, CAPTURE),
        start(1, PHASE), start(3, CAPTURE), end(3, CAPTURE), checkpoint(2, 0), end(1, PHASE),
        {'event': 'counter_snapshot', 'valid': True,
         'stats': {CAPTURE: {'calls': 2}, PHASE: {'calls': 1}, SCHEMA: {'calls': 0}}}]
    repin(value, rows)
    saved = helper.load_arm(value)
    result = saved.boundary('native_schema_member_visits', rows[4], entry=True)
    assert not result['verified']
    assert 'crosses' in result['reason']


def test_capped_producer_roster_refuses_event_bridge(tmp_path):
    value, c_rows, _ = pair(tmp_path)
    c_rows[-1]['stats'][CAPTURE]['calls'] = 600
    repin(value['control'], c_rows)
    result = helper.supplement(value)
    assert not any(row['target'] == PHASE for row in result['compared_completed_calls'])
    excluded = next(row for row in result['excluded_calls'] if row['target'] == PHASE)
    assert any('boundary work not proved' in reason for reason in excluded['reasons'])


def test_parser_count_only_has_no_invented_event_bridge(tmp_path):
    value, _, _ = pair(tmp_path)
    row = phase(helper.supplement(value))
    assert row['optional_document_equality']['yaml:parse_started'] is None
    assert not row['control']['work']['yaml:parse_started']['entry']['verified']


def test_equal_monotone_bracket_can_prove_parser_count_without_start_events(tmp_path):
    value, rows = arm(tmp_path, 'single', extra=0)
    # A no-parser-call phase nested between equal parser snapshots.
    rows = [rows[0], checkpoint(0, 0, 7), start(1, PHASE),
        checkpoint(0, 0, 7), end(1, PHASE), checkpoint(0, 0, 7),
        {'event': 'counter_snapshot', 'valid': True, 'stats': {PHASE: {'calls': 1}}}]
    repin(value, rows)
    saved = helper.load_arm(value)
    bound = saved.boundary('yaml:parse_started', rows[2], entry=True)
    assert bound['verified']
    assert bound['method'] == 'equal_monotone_bracketing_snapshots'
    assert bound['value'] == doc(7, 'c')


def test_generic_schema_work_mismatch_excludes_even_with_same_member_work(tmp_path):
    value, _, rows = pair(tmp_path)
    for row in rows:
        if row['event'] == 'thread_cpu_checkpoint' and row['documents'][SCHEMA]['calls']:
            row['documents'][SCHEMA] = doc(1, 'd')
    repin(value['treatment'], rows)
    result = helper.supplement(value)
    assert not any(row['target'] == PHASE for row in result['compared_completed_calls'])


@pytest.mark.parametrize('mode', ['invalid_flag', 'wrong_source', 'changed_bytes', 'bad_prefix', 'bad_common_pins'])
def test_invalid_evidence_fails_closed(tmp_path, mode):
    value, rows, _ = pair(tmp_path)
    if mode == 'bad_prefix':
        value['control']['observed_measurement_prefix_valid'] = False
    elif mode == 'bad_common_pins':
        value['comparison']['matching_common_instrumentation_and_external_monitored_pins'] = False
    elif mode == 'changed_bytes':
        path = Path(value['control']['recorder']['observer_jsonl']['artifact']['path'])
        path.write_bytes(path.read_bytes() + b'\n')
    else:
        if mode == 'invalid_flag':
            rows[-1]['valid'] = False
        else:
            rows[0]['root'] = '/foreign/source'
        repin(value['control'], rows)
    with pytest.raises(ValueError):
        helper.supplement(value)


def test_document_regression_is_excluded_not_normalized_away(tmp_path):
    value, rows, _ = pair(tmp_path)
    checkpoint_row = [row for row in rows if row['event'] == 'thread_cpu_checkpoint'][-1]
    checkpoint_row['documents']['native_schema_member_visits'] = doc(0)
    repin(value['control'], rows)
    result = helper.supplement(value)
    assert not result['compared_completed_calls']


def test_existing_analysis_unchanged_and_new_output_exclusive(tmp_path):
    value, _, _ = pair(tmp_path)
    input_path, output_path = tmp_path / 'pair.json', tmp_path / 'local.json'
    input_path.write_text(json.dumps(value))
    before = input_path.read_bytes()
    assert helper.main(['--pair-analysis', str(input_path), '--out', str(output_path)]) == 0
    assert input_path.read_bytes() == before
    result = json.loads(output_path.read_bytes())
    assert result['global_analyzer_gate_unchanged'] is False
    assert phase(result)['control']['outcome'] == 'returns'
    with pytest.raises(SystemExit):
        helper.main(['--pair-analysis', str(input_path), '--out', str(output_path)])
