"""Audit response buffering selection: invented ancestry and injected clients only."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

BASE = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(BASE), str(BASE / 'native_controls')]
from audit_controls import batch_native, native, prepare, registration, transport
from audit_controls.test_batch_runtime import batch
from audit_controls.test_context_preparation import ancestry, accepted_audit, save
from audit_controls.test_native import native_case, configure_execution
from audit_controls.test_staged_preparation import actual_renderer_history_root
from audit_controls.test_upstream_timeout import generation_manifest
from budgeted_cborg import BudgetStop
from evaluation_controls import registration as evaluation_registration
from finalization_controls import native as final_native, prepare as final_prepare
from finalization_controls import registration as final_registration
import run_api_canary
import run_native_canary

KEY = 'native_response_buffer'
BUFFER = {'kind': 'complete_response_v1', 'max_bytes': 16777216, 'total_seconds': 1200}
POLICY = {'kind': 'bounded_in_attempt_v1', 'count_attempts': 3,
          'max_stall_debits': 0, 'authorization': None}
RUNTIME = {'api_timeout_ms': 3600000, 'api_force_idle_timeout': False}
PREPARE_OPTIONS = {'native_api_timeout_ms': 3600000, 'native_api_force_idle_timeout': False,
                   'native_upstream_read_timeout_seconds': 1200, 'native_stall_policy': POLICY}


def manifest(**changes):
    return {'kind': 'd4d_native_audit_continuation', KEY: dict(BUFFER),
            'native_stall_policy': deepcopy(POLICY), 'native_runtime': dict(RUNTIME),
            'native_upstream_read_timeout_seconds': 1200,
            'job': {'deadline_seconds': 10800}, **changes}


def forbidden(*args, **kwargs):
    pytest.fail('mutable setup or provider construction before selector validation')


def snapshot(directory):
    return {str(p.relative_to(directory)): p.read_bytes() for p in directory.rglob('*') if p.is_file()}


def test_absence_keeps_legacy_and_selection_returns_an_independent_value():
    assert registration.native_response_buffer({}) is None
    m = manifest()
    selected = registration.native_response_buffer(m)
    assert selected == BUFFER
    selected['max_bytes'] = 1
    assert m[KEY] == BUFFER
    del m[KEY]
    assert registration.native_response_buffer(m) is None
    # With buffering absent, the existing counting-only policy still requires
    # neither an SDK timeout nor an idle override.
    m.pop('native_upstream_read_timeout_seconds'); m['native_runtime'] = {}
    assert registration.native_stall_policy(m) == {'count_attempts': 3, 'max_stall_debits': 0}
    assert registration.native_response_buffer(m) is None


BAD_SELECTIONS = [None, True, False, [], 'on', {}, {**BUFFER, 'extra': 1},
    {**BUFFER, 'kind': 'other'}, {k: v for k, v in BUFFER.items() if k != 'total_seconds'},
    *[{**BUFFER, 'max_bytes': v} for v in (None, True, False, 0, -1, 1.5, '16', 67108865)],
    *[{**BUFFER, 'total_seconds': v} for v in (None, True, False, 0, -1, 1.5, '1200', 1201)]]


@pytest.mark.parametrize('value', BAD_SELECTIONS)
def test_malformed_selection_stops_before_runtime_or_client(value, tmp_path, monkeypatch):
    m = manifest(**{KEY: value})
    monkeypatch.setattr(native, 'build_policy', forbidden)
    monkeypatch.setattr(native, 'verify_runtime', forbidden)
    monkeypatch.setattr(transport, 'Client', forbidden)
    context = SimpleNamespace(manifest=m, job=m['job'], attempt=tmp_path)
    with pytest.raises(BudgetStop): registration.native_response_buffer(m)
    with pytest.raises(BudgetStop): native.execute_job(context)
    with pytest.raises(BudgetStop): transport.provider_clients(m, 'synthetic-key')
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize('max_bytes', [1, 67108864])
@pytest.mark.parametrize('seconds', [1, 1200])
def test_inclusive_byte_and_time_bounds(max_bytes, seconds):
    value = {**BUFFER, 'max_bytes': max_bytes, 'total_seconds': seconds}
    assert registration.native_response_buffer(manifest(**{KEY: value})) == value


@pytest.mark.parametrize('change', ['no_policy', 'null_policy', 'no_sdk', 'short_sdk',
    'idle_absent', 'idle_true', 'idle_null', 'read_bool', 'read_too_short', 'wrong_stage'])
def test_buffer_requires_policy_sdk_margin_and_idle_off_even_without_debits(change, tmp_path, monkeypatch):
    m = manifest()
    if change == 'no_policy': del m['native_stall_policy']
    elif change == 'null_policy': m['native_stall_policy'] = None
    elif change == 'no_sdk': del m['native_runtime']['api_timeout_ms']
    elif change == 'short_sdk': m['native_runtime']['api_timeout_ms'] = 1654999
    elif change == 'idle_absent': del m['native_runtime']['api_force_idle_timeout']
    elif change == 'idle_true': m['native_runtime']['api_force_idle_timeout'] = True
    elif change == 'idle_null': m['native_runtime']['api_force_idle_timeout'] = None
    elif change == 'read_bool': m['native_upstream_read_timeout_seconds'] = True
    elif change == 'read_too_short': m['native_upstream_read_timeout_seconds'] = 1199
    else: m['kind'] = 'd4d_native_finalization'
    monkeypatch.setattr(transport, 'Client', forbidden)
    monkeypatch.setattr(native, 'build_policy', forbidden)
    context = SimpleNamespace(manifest=m, job=m['job'], attempt=tmp_path)
    with pytest.raises(BudgetStop): registration.native_response_buffer(m)
    with pytest.raises(BudgetStop): native.execute_job(context)
    with pytest.raises(BudgetStop): transport.provider_clients(m, 'synthetic-key')
    assert list(tmp_path.iterdir()) == []


def test_exact_sdk_margin_uses_registered_or_legacy_read_bound():
    m = manifest(native_runtime={**RUNTIME, 'api_timeout_ms': 1655000})
    assert registration.native_response_buffer(m) == BUFFER
    del m['native_upstream_read_timeout_seconds']
    m[KEY]['total_seconds'] = 1800
    m['native_runtime']['api_timeout_ms'] = 2255000
    assert registration.native_response_buffer(m)['total_seconds'] == 1800
    m['native_runtime']['api_timeout_ms'] -= 1
    with pytest.raises(BudgetStop, match='SDK timeout margin'): registration.native_response_buffer(m)
    m['native_runtime']['api_timeout_ms'] += 1
    m[KEY]['total_seconds'] = 1801
    with pytest.raises(BudgetStop, match='read bound'): registration.native_response_buffer(m)


@pytest.mark.parametrize('value', [v for v in BAD_SELECTIONS if v is not None])
def test_prepare_rejects_malformed_selection_before_destination(value, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    destination = tmp_path / 'uncreated'
    with pytest.raises(BudgetStop):
        prepare.prepare(parent_registration=tmp_path / 'missing-parent.json', parent_overlay=None,
            parent_job_id=None, reconciliation_receipt=None, reconciled_checkpoint=None,
            destination=destination, job_id='synthetic', repository=tmp_path,
            **PREPARE_OPTIONS, native_response_buffer=value)
    assert not destination.exists()


@pytest.mark.parametrize('change', ['policy', 'margin', 'idle'])
def test_prepare_requires_operational_guards_before_destination(change, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    options = deepcopy(PREPARE_OPTIONS)
    if change == 'policy': options['native_stall_policy'] = None
    elif change == 'margin': options['native_api_timeout_ms'] = 1654999
    else: options['native_api_force_idle_timeout'] = None
    destination = tmp_path / 'uncreated'
    with pytest.raises(BudgetStop):
        prepare.prepare(parent_registration=tmp_path / 'missing-parent.json', parent_overlay=None,
            parent_job_id=None, reconciliation_receipt=None, reconciled_checkpoint=None,
            destination=destination, job_id='synthetic', repository=tmp_path,
            **options, native_response_buffer=BUFFER)
    assert not destination.exists()


CLI_REQUIRED = ['--parent-registration', 'parent.json', '--parent-overlay', 'overlay.json',
    '--parent-job-id', 'synthetic-parent', '--reconciliation-receipt', 'receipt.json',
    '--reconciled-checkpoint', 'checkpoint.json', '--destination', 'unused', '--job-id', 'synthetic']


@pytest.mark.parametrize('text', ['null', 'true', '[]', '"on"', '{', '{"max_bytes":1,"max_bytes":2}',
    '{"total_seconds":NaN}', '{"total_seconds":Infinity}', '{"total_seconds":-Infinity}'])
def test_named_cli_file_is_strict_and_cannot_silently_select_legacy(text, tmp_path, monkeypatch):
    path = tmp_path / 'selection.json'; path.write_text(text)
    monkeypatch.setattr(prepare, 'prepare', forbidden)
    monkeypatch.setattr(sys, 'argv', ['prepare', *CLI_REQUIRED, '--native-response-buffer', str(path)])
    with pytest.raises(BudgetStop): prepare.read_response_buffer(path)
    with pytest.raises(BudgetStop): prepare.main()
    assert snapshot(tmp_path) == {'selection.json': text.encode()}


@pytest.mark.parametrize('kind', ['missing', 'directory', 'invalid_utf8'])
def test_named_cli_file_read_errors_are_budget_stops(kind, tmp_path, monkeypatch):
    path = tmp_path / 'selection.json'
    if kind == 'directory': path.mkdir()
    if kind == 'invalid_utf8': path.write_bytes(b'\xff')
    monkeypatch.setattr(prepare, 'prepare', forbidden)
    monkeypatch.setattr(sys, 'argv', ['prepare', *CLI_REQUIRED, '--native-response-buffer', str(path)])
    with pytest.raises(BudgetStop): prepare.main()


@pytest.mark.parametrize('selected', [False, True])
def test_cli_delivers_exact_selection_or_legacy_none(selected, tmp_path, monkeypatch, capsys):
    path = tmp_path / 'selection.json'; save(path, BUFFER)
    calls = []
    def collect(**kwargs): calls.append(kwargs); return path
    monkeypatch.setattr(prepare, 'prepare', collect)
    monkeypatch.setattr(sys, 'argv', ['prepare', *CLI_REQUIRED,
        *(['--native-response-buffer', str(path)] if selected else [])])
    prepare.main()
    assert len(calls) == 1 and calls[0][KEY] == (BUFFER if selected else None)
    assert json.loads(capsys.readouterr().out) == {'registration': str(path), 'sha256': registration.sha(path)}
    assert list(tmp_path.iterdir()) == [path]


@pytest.mark.parametrize('staged', [False, True])
def test_real_preparation_pins_selection_without_changing_scientific_context(ancestry, tmp_path, staged):
    common = dict(ancestry[0], **PREPARE_OPTIONS, context_recovery=True, staged_audit_output=staged)
    legacy = prepare.prepare(**common, destination=tmp_path / 'legacy__')
    selected = prepare.prepare(**common, destination=tmp_path / 'selected', native_response_buffer=BUFFER)
    before = registration.validate_registration(legacy)
    after = registration.validate_registration(selected)
    assert KEY not in before and after[KEY] == BUFFER
    for key in ('model', 'profile', 'provider_base_url', 'provider_context_policy', 'native_runtime'):
        assert after[key] == before[key]
    expected_budget = deepcopy(before['budget']); expected_budget['ledger_path'] = after['budget']['ledger_path']
    assert after['budget'] == expected_budget
    for key in ('instruction', 'system_prompt'):
        normalized = Path(after['job'][key]).read_text().replace(str(selected.parent), str(legacy.parent)).replace(
            after['context_recovery']['index']['sha256'], before['context_recovery']['index']['sha256'])
        assert normalized == Path(before['job'][key]).read_text()
    assert set(after['inputs']) == set(before['inputs'])
    for role, path in after['inputs'].items():
        assert path.replace(str(selected.parent), str(legacy.parent)) == before['inputs'][role]
        assert Path(path).read_bytes() == Path(before['inputs'][role]).read_bytes()
    assert sorted(p.replace(str(selected.parent), str(legacy.parent)) for p in after['job']['readable_inputs']) == sorted(before['job']['readable_inputs'])
    for path in registration.required_paths(after):
        assert after['pinned_files'][str(path)] == registration.sha(path)
    assert json.loads((selected.parent / 'offline_plan.json').read_text())[KEY] == BUFFER
    assert KEY not in json.loads((legacy.parent / 'offline_plan.json').read_text())
    assert not Path(after['job']['attempt_dir']).exists() and not Path(after['budget']['ledger_path']).exists()
    assert ancestry[2] == {name: Path(name).read_bytes() for name in ancestry[2]}


def test_accepted_audit_selector_remains_evidence_only_for_real_phase4(ancestry, tmp_path):
    selected_ancestry = ({**ancestry[0], **PREPARE_OPTIONS, KEY: BUFFER}, *ancestry[1:])
    accepted, acceptance = accepted_audit(selected_ancestry, tmp_path / 'accepted')
    accepted_bytes = accepted.read_bytes()
    path = final_prepare.prepare(accepted_audit_registration=accepted, acceptance=acceptance,
        destination=tmp_path / 'phase4', job_id='synthetic_final', repository=ancestry[0]['repository'])
    m = final_registration.validate_registration(path)
    assert KEY not in m and KEY not in m['native_runtime'] and KEY not in m.get('provider_transport', {})
    assert accepted.read_bytes() == accepted_bytes and registration.read_json(accepted)[KEY] == BUFFER
    assert m['pinned_files'][str(accepted)] == registration.sha(accepted)
    assert registration.native_response_buffer(m) is None
    assert not Path(m['job']['attempt_dir']).exists() and not Path(m['budget']['ledger_path']).exists()


@pytest.mark.parametrize('stage', ['phase4', 'evaluation'])
@pytest.mark.parametrize('value', [BUFFER, None, True])
def test_actual_later_stage_entry_rejects_even_null_before_ownership(stage, value, tmp_path, monkeypatch):
    m = {'kind': 'd4d_native_finalization' if stage == 'phase4' else 'd4d_evaluation_registration', KEY: value}
    path, review = tmp_path / 'registration.json', tmp_path / 'review.json'
    save(path, m); save(review, {})
    before = snapshot(tmp_path)
    if stage == 'phase4':
        monkeypatch.setattr(final_native, 'owned_sequence', forbidden)
        monkeypatch.setattr(final_native, 'build_policy', forbidden)
        with pytest.raises(BudgetStop, match='audit-only'): final_native.run_job(path, review, adapter=forbidden)
    else:
        # This executable uses the sibling-module import spelling. Bind it to
        # its real verifier without leaking a global `registration` alias into
        # other controls' tests collected in the same interpreter.
        spec = importlib.util.spec_from_file_location('response_buffer_evaluation_entry', BASE / 'evaluation_controls/run_evaluation.py')
        run_evaluation = importlib.util.module_from_spec(spec)
        with monkeypatch.context() as imports:
            imports.setitem(sys.modules, 'registration', evaluation_registration)
            spec.loader.exec_module(run_evaluation)
        monkeypatch.setattr(run_evaluation, 'accounting_owner', forbidden)
        monkeypatch.setattr(run_evaluation, 'verify_dependencies', forbidden)
        with pytest.raises(BudgetStop, match='audit-only'): run_evaluation.run_job(path, review, 'synthetic', adapter=forbidden)
    assert snapshot(tmp_path) == before and sorted(p.name for p in tmp_path.iterdir()) == ['registration.json', 'review.json']


@pytest.mark.parametrize('arm', ['api', 'agentic'])
@pytest.mark.parametrize('selection', [{}, {KEY: BUFFER}, {KEY: None}], ids=['legacy', 'buffer', 'null'])
def test_real_generation_entries_reject_selection_before_mutable_setup(arm, selection, tmp_path, monkeypatch):
    m = generation_manifest(tmp_path, monkeypatch)
    job = {'id': 'synthetic', 'canary': True, 'execution_arm': arm, 'output_directories': [str(tmp_path / 'output')]}
    m.update(selection, generation={'external_canary': {'status': 'registered'}, 'jobs': [job], 'canary_order': [job['id']]})
    path, review_path = tmp_path / 'registration.json', tmp_path / 'review.json'; save(path, m)
    review = {'registration_sha256': registration.sha(path), 'verdict': 'approve', 'ci_conclusion': 'success', 'allowed_jobs': [job['id']]}
    runner, args = run_api_canary, ['--registration', str(path)]
    if arm == 'agentic':
        runner = run_native_canary
        overlay = tmp_path / 'overlay.json'
        save(overlay, {'registration': str(path), 'registration_sha256': review['registration_sha256'], 'allowed_jobs': [job['id']], 'pinned_files': {}})
        review['overlay_sha256'] = registration.sha(overlay); args = ['--overlay', str(overlay)]
    save(review_path, review)
    before = snapshot(tmp_path)
    class NextLegacyGate(Exception): pass
    history_calls = []
    def next_gate(value): history_calls.append(value); raise NextLegacyGate()
    monkeypatch.setattr(runner, 'verify_history', next_gate)
    for name in ('open_ledger', 'cborg_client', 'spec_for'): monkeypatch.setattr(runner, name, forbidden)
    monkeypatch.setattr(sys, 'argv', ['generation', *args, '--review', str(review_path), '--job', job['id']])
    if selection:
        with pytest.raises(BudgetStop, match='audit-only'): runner.main()
        assert history_calls == []
    else:
        with pytest.raises(NextLegacyGate): runner.main()
        assert history_calls == [m]
    assert snapshot(tmp_path) == before
    assert not (tmp_path / 'attempts').exists() and not (tmp_path / 'output').exists()


@pytest.mark.parametrize('selected', [False, True])
def test_registered_transport_forwards_total_deadline_only_when_selected(selected, monkeypatch):
    from audit_controls import bounded_stream, bounded_transport
    m = manifest(provider_base_url='https://api.cborg.lbl.gov')
    if not selected: del m[KEY]
    calls = []
    def metadata(**kwargs): calls.append(('metadata', kwargs)); return SimpleNamespace(close=lambda: None)
    def count(**kwargs): calls.append(('count', kwargs)); return SimpleNamespace(close=lambda: None)
    def stream(client, **kwargs): calls.append(('stream', kwargs)); return SimpleNamespace(metadata=client)
    monkeypatch.setattr(transport, 'Client', metadata)
    monkeypatch.setattr(bounded_transport, 'BoundedCountClient', count)
    monkeypatch.setattr(bounded_stream, 'BoundedStreamClient', stream)
    sdk, upstream = transport.provider_clients(m, 'synthetic-key')
    assert [kind for kind, _ in calls] == ['metadata', 'count', 'stream']
    options = calls[-1][1]
    assert options['read_timeout_seconds'] == 1200
    assert options.get('total_timeout_seconds') == (1200 if selected else None)
    assert ('total_timeout_seconds' in options) is selected


class ProxyBoundary(Exception):
    """Stop at proxy construction, before any server, child or upstream request."""


@pytest.mark.parametrize('selected', [False, True])
def test_nonbatch_runtime_forwards_exact_buffer_only_when_registered(native_case, monkeypatch, selected):
    c = native_case
    context, sdk = configure_execution(c, monkeypatch)
    c.manifest.update(kind='d4d_native_audit_continuation', native_stall_policy=deepcopy(POLICY),
                      native_upstream_read_timeout_seconds=1200)
    c.manifest['native_runtime'].update(RUNTIME); c.job['deadline_seconds'] = 10800
    if selected: c.manifest[KEY] = dict(BUFFER)
    calls = []
    def proxy(**kwargs): calls.append(kwargs); raise ProxyBoundary()
    monkeypatch.setattr(native, 'AuditProxy', proxy)
    monkeypatch.setattr(native, 'execute_child', forbidden)
    with pytest.raises(ProxyBoundary): native.execute_job(context, client=sdk, upstream=object())
    assert len(calls) == 1 and ('response_buffer' in calls[0]) is selected
    if selected: assert calls[0]['response_buffer'] == BUFFER
    assert not c.ledger.path.exists()


@pytest.mark.parametrize('selected', [False, True])
def test_batch_child_forwards_exact_buffer_only_when_registered(batch, monkeypatch, selected):
    m = batch.m
    m.update(native_stall_policy=deepcopy(POLICY), native_upstream_read_timeout_seconds=1200,
             provider_base_url='https://api.cborg.lbl.gov')
    m['native_runtime'].update(RUNTIME)
    m['budget']['prices_per_token'] = {'input': '0.000005', 'output': '0.000025'}
    if selected: m[KEY] = dict(BUFFER)
    context = SimpleNamespace(manifest=m, manifest_sha256=batch.identity, job=m['job'],
                              registration_path=batch.reg, ledger=batch.ledger, verify=lambda: None)
    calls = []
    def proxy(**kwargs): calls.append(kwargs); raise ProxyBoundary()
    monkeypatch.setattr(batch_native, 'BatchProxy', proxy)
    monkeypatch.setattr(native, 'execute_child', forbidden)
    row = m['audit_batches']['children'][0]
    with pytest.raises(ProxyBoundary):
        batch_native._execute_child(context, row, 100, clock=lambda: 0, client=object(), upstream=object())
    assert len(calls) == 1 and ('response_buffer' in calls[0]) is selected
    if selected: assert calls[0]['response_buffer'] == BUFFER
    assert json.loads(batch.ledger.path.read_text())['requests'] == []
