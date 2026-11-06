"""Saved U0 second-pair reader tests, 2026-11-06; no recorder/native execution."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


analysis = module('u0_second_analysis_test', ROOT / 'scripts/adhoc/analyze_native_u0_second_pair_20261106.py')
fixture = module('u0_saved_pair_fixture', Path(__file__).with_name('test_analyze_native_u0_causal_pair_20261106.py'))
saved, pin = fixture.saved, fixture.pin


def make_arm(tmp_path, label, *, complete=True, cpu=100, internal_count=2):
    trial, parent, recorder, rows = fixture.fixture(tmp_path, label, complete=complete, cpu=cpu)
    fixture.add_second_observer(trial, recorder, rows)
    root = Path(rows[0]['root'])
    source = json.loads((trial / 'source-before.json').read_bytes())
    source['head'] = hashlib.sha256(label.encode()).hexdigest()[:40]
    for name in (*analysis.COMMON, *analysis.TESTS):
        source['files'].setdefault(name, {**pin(root / name), 'committed_exact': True})
    source['files']['tests/empty.py'] = {**pin(root / 'tests/empty.py', b''), 'committed_exact': True}
    for name in analysis.CHANGES:
        if label == 'control' and name.endswith('native_catalog_initialization.py'):
            continue
        source['files'][name] = {**pin(root / name, (label + name).encode()), 'committed_exact': True}
    for name in ('source-before.json', 'source-after.json'):
        saved(trial / name, source)
    target = 'cli.provenance:_inline_checks'
    rows[1]['target'] = rows[2]['target'] = target
    rows[3]['stats'] = {target: {'calls': 1, 'returns': 1, 'unwinds': 0},
        'audit_omissions:_schema_product': {'calls': internal_count, 'returns': internal_count, 'unwinds': 0}}
    rows[4]['documents']['audit_omissions:_schema_yaml'] = {'calls': internal_count,
        'input_bytes': 14 * internal_count, 'hash_counts': {'a' * 64: internal_count},
        'hash_coverage_complete': True, 'non_text_inputs': 0}
    for row in rows:
        if row['event'] in ('thread_cpu_checkpoint', 'observer_end'):
            row.update(guard_reason_counts={'native_catalog_reuse:runtime_token/token_available': 2},
                guard_reason_parent_phase_counts={}, guard_reason_details=1,
                guard_reason_details_suppressed=0, guard_reason_callback_thread_cpu_ns=2)
    rows[4]['rusage'] = {'thread_cpu_ns': cpu, 'process_cpu_ns': cpu+20}
    fixture.write_rows(recorder, rows)
    wrapper = trial.with_name(trial.name + '.wrapper')
    saved(wrapper / 'outcome.json', {'lock_released': True, 'helper_limit_seconds': 180,
        'attempt_limit_seconds': 900, 'driver_cleanup_completed': True, 'observer_cleanup_completed': True})
    case = trial / 'cases/test-node/native26'
    composition = json.loads((case / 'authority/composition-execution.json').read_bytes())
    spec = {'profile': 'neutral', 'native_shared_generation_version': 1, 'render_version': 26,
        'condition': 'generic_v10', 'arm': 'BASELINE', 'agentic_artifact_paths': {}}
    captured = {}
    for field, name, raw in [('bundle', 'authority/bundle.txt', b'the same input\n'),
            ('manifest', 'sources.yaml', ('bundle: ' + str(case / 'authority/bundle.txt') + '\n').encode()),
            ('chunk_manifest', 'authority/chunks.json', b'{"chunks":[]}\n')]:
        path = case / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(raw)
        spec[field] = str(path); captured[str(path)] = pin(path, raw)
    for role in ('full', 'core'):
        path = case / (role + '.yaml'); raw = (role + ': the same bytes\n').encode(); path.write_bytes(raw)
        spec['agentic_artifact_paths'][role] = str(path)
        captured[str(path)] = {**pin(path, raw), 'roles': ['final_' + role]}
    composition['render_spec'] = spec
    saved(case / 'authority/composition-execution.json', composition)
    final = json.loads((case / 'actual-result.json').read_bytes())
    final['captured_files'] = captured
    saved(case / 'actual-result.json', final)
    final_sha = saved(case / 'native-evidence/final.json', final)
    registration = saved(case / 'native-attempt/registration.json', {'synthetic': 'registration'})
    started = saved(case / 'native-attempt/started.json', {'synthetic': 'started'})
    saved(case / 'native-evidence/published.json', {'final_sha256': final_sha,
        'registration_sha256': registration, 'started_sha256': started})
    return trial, parent, recorder, rows, source


def make_pair(tmp_path, *, control_complete=True):
    c = make_arm(tmp_path, 'control', complete=control_complete, cpu=100, internal_count=5)
    t = make_arm(tmp_path, 'treatment', cpu=30, internal_count=1)
    manifest = {'format': 'native_u0_second_pair_sources_v1', 'first_treatment': analysis.FIRST_TREATMENT,
        'limits': dict(analysis.LIMITS), 'common_instrumentation_byte_identical': True}
    for label, arm in [('control', c), ('treatment', t)]:
        manifest[label] = {'head': arm[4]['head'], 'worktree': arm[3][0]['root'],
            'files': arm[4]['files'], 'changed_paths': sorted(analysis.CHANGES),
            'parent': c[4]['head'] if label == 'treatment' else analysis.FIRST_TREATMENT}
    manifest['treatment_manifest'] = {'control_head': c[4]['head'],
        'changed_paths': sorted(analysis.CHANGES), 'files': [
            {'path': name, 'before_sha256': c[4]['files'].get(name, {}).get('sha256'),
             'after_sha256': t[4]['files'][name]['sha256']} for name in sorted(analysis.CHANGES)]}
    path = tmp_path / 'sources.json'; saved(path, manifest)
    return c, t, path


def run_pair(c, t, manifest):
    return analysis.analyze(c[0], t[0], c[1], manifest)


def test_saved_second_pair_canary_preserves_gate_and_compares_completed_top_level(tmp_path):
    c, t, manifest = make_pair(tmp_path)
    result = run_pair(c, t, manifest)
    assert result['valid'], result
    assert result['source_contract']['verified']
    assert result['matching_fixture_inputs']
    assert result['control']['same_run_readback_verified']
    assert result['treatment']['same_run_readback_verified']
    top = result['top_level_phase_comparison']['matched_completed_calls']
    assert len(top) == 1
    assert top[0]['inclusive_cpu_comparison']['thread_cpu_ns']['treatment_over_control'] == .3
    assert result['control_details']['document_counters_at_own_cutoff']['audit_omissions:_schema_yaml']['calls'] == 5
    assert result['treatment_details']['document_counters_at_own_cutoff']['audit_omissions:_schema_yaml']['calls'] == 1
    assert all(row['byte_equal'] for row in result['published_full_core_comparison'].values())
    assert result['unchanged_original_global_comparison'] == analysis.base.compare(result['control'], result['treatment'])


def test_censored_phase_never_becomes_completed_and_old_gate_can_fail(tmp_path):
    c, t, manifest = make_pair(tmp_path, control_complete=False)
    rows = c[3]
    rows.pop(2)
    rows[2]['stats']['cli.provenance:_inline_checks']['returns'] = 0
    rows[3]['documents']['native_schema_member_visits']['calls'] = 2
    rows[3]['documents']['native_schema_member_visits']['hash_counts']['a' * 64] = 2
    rows[3]['documents']['native_schema_member_visits']['input_bytes'] = 28
    fixture.write_rows(c[2], rows)
    result = run_pair(c, t, manifest)
    assert result['valid'], result
    assert not result['unchanged_original_global_comparison']['matching_native_schema_member_work']
    assert not result['top_level_phase_comparison']['matched_completed_calls']
    assert result['top_level_phase_comparison']['control_censored_calls'][0]['state'] == 'censored_no_phase_end'
    assert result['control_details']['censored']
    assert not result['control']['same_run_readback_verified']


@pytest.mark.parametrize('damage', ['source_manifest', 'wrong_parent', 'unexpected_source', 'fixture_bytes', 'captured_output',
    'missing_output', 'cleanup', 'limits', 'observer_flag', 'observer_tail', 'guard_counts'])
def test_invalid_saved_artifact_or_authority_blocks_top_level_comparison(tmp_path, damage):
    c, t, manifest = make_pair(tmp_path)
    trial, parent, recorder, rows, source = t
    case = trial / 'cases/test-node/native26'
    if damage == 'source_manifest':
        value = json.loads(manifest.read_bytes()); value['treatment']['head'] = 'wrong'; saved(manifest, value)
    elif damage == 'wrong_parent':
        value = json.loads(manifest.read_bytes()); value['control']['parent'] = 'wrong'; saved(manifest, value)
    elif damage == 'unexpected_source':
        source['files']['src/data_sheets_schema/unrelated.py'] = {**pin(Path(rows[0]['root']) / 'other'), 'committed_exact': True}
        for name in ('source-before.json', 'source-after.json'): saved(trial / name, source)
    elif damage == 'fixture_bytes':
        (case / 'authority/bundle.txt').write_bytes(b'changed input\n')
    elif damage == 'captured_output':
        (case / 'full.yaml').write_bytes(b'changed full\n')
    elif damage == 'missing_output':
        (case / 'full.yaml').unlink()
    elif damage in ('cleanup', 'limits'):
        path = trial.with_name(trial.name + '.wrapper') / 'outcome.json'
        value = json.loads(path.read_bytes()); value['lock_released' if damage == 'cleanup' else 'helper_limit_seconds'] = False
        saved(path, value)
    elif damage == 'observer_flag':
        rows[3]['valid'] = False; fixture.write_rows(recorder, rows)
    elif damage == 'guard_counts':
        rows[-1]['guard_reason_counts'] = {}; fixture.write_rows(recorder, rows)
    else:
        with (recorder / 'observer.jsonl').open('ab') as stream: stream.write(b'{"event":')
    result = run_pair(c, t, manifest)
    assert not result['valid']
    assert not result['top_level_phase_comparison']['matched_completed_calls']


def test_historical_censored_cpu_is_descriptive_and_never_a_ratio(tmp_path):
    c, t, manifest = make_pair(tmp_path, control_complete=False)
    arms = [analysis.base.analyze_trial(row[0], c[1]) for row in (c, t)]
    result = analysis.historical_censored_cpu({'control': arms[0]}, arms[1])
    assert result['descriptive_censored_lower_bound_available']
    assert result['historical_control_censored_prefix']['thread_cpu_ns'] == 100
    assert result['second_treatment_completed_recorder_checkpoint']['thread_cpu_ns'] == 30
    assert result['ratio'] is None and result['wall_time_margin'] is None


def test_exclusive_cli_output_contains_hashes_and_cannot_be_overwritten(tmp_path):
    c, t, manifest = make_pair(tmp_path)
    out = tmp_path / 'analysis.json'
    args = ['--control-trial', str(c[0]), '--treatment-trial', str(t[0]),
        '--observer-parent', str(c[1]), '--sources', str(manifest), '--out', str(out)]
    assert analysis.main(args) == 0
    before = out.read_bytes(); value = json.loads(before)
    assert value['analyzer_pin']['sha256'] and value['artifact_pins'][str(manifest)]['bytes'] > 0
    with pytest.raises(SystemExit): analysis.main(args)
    assert out.read_bytes() == before
