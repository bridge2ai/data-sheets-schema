"""Failed-record retention with real files and synthetic publication identities.

These are byte-inventory/phase tests, not a launch, authorization or eligibility
fixture. Missing and rejected records must never prevent failed publication.
"""
from pathlib import Path
from types import SimpleNamespace

import pytest

from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_results as reader
from data_sheets_schema import native_shared_results_orchestration as capture
from data_sheets_schema import native_shared_gates as gates
from data_sheets_schema.native_execution_engine import GATES, UNASSESSED


def case(root):
    attempt, evidence = root / 'attempt', root / 'evidence'
    attempt.mkdir(); evidence.mkdir()
    paths = {name: str(root / (name + '.yaml')) for name in ('full', 'core', 'report')}
    composition_raw = c.canonical({'render_spec': {'agentic_artifact_paths': paths}})
    composition = root / 'composition.json'; composition.write_bytes(composition_raw)
    for name in ('transcript.jsonl', 'control.jsonl', 'stderr.txt'):
        (attempt / name).write_bytes(b'')
    value = {'kind': 'd4d_native_shared_execution_registration_v2', 'schema_version': 2,
        'working_directory': str(root), 'attempt_directory': str(attempt), 'evidence_directory': str(evidence),
        'attempt_id': 'failed-fixture', 'composition_sha256': c.sha(composition_raw),
        'composition_raw_json': composition_raw.decode()}
    adapter = SimpleNamespace(value=value, spec=SimpleNamespace(_agentic_artifact_paths=paths),
                              state=SimpleNamespace(reg={}), policy={})
    return value, adapter, composition


def publish(value, prepared):
    """Archive fixture using the actual projection and retention manifest code."""
    attempt, directory = Path(value['attempt_directory']), Path(value['evidence_directory'])
    raw = c.canonical({'authority_version': 2, 'controller_sources_sha256': 'a' * 64, 'registration': value})
    started = c.canonical({'attempt_id': value['attempt_id'], 'registration_sha256': c.sha(raw)})
    (attempt / 'registration.json').write_bytes(raw)
    (attempt / 'started.json').write_bytes(started)
    copies = capture.project(prepared, directory / 'captured')
    final = {'kind': 'd4d_native_shared_attempt', 'version': 1, 'attempt_id': value['attempt_id'],
        'composition_sha256': value['composition_sha256'], 'registration_sha256': c.sha(raw),
        'started_sha256': c.sha(started), 'state': 'failed', 'runtime_gates_passed': False,
        'first_stop': 'declared failed fixture', **UNASSESSED,
        'gates': {name: {'checked': False, 'passed': False} for name in GATES},
        'captured_files': prepared['snapshot'].identity(),
        'retained_artifacts': capture.retention_manifest(prepared, copies),
        'capture_problems': prepared['capture_problems']}
    final_raw = c.canonical(final)
    (directory / 'final.json').write_bytes(final_raw)
    (directory / 'published.json').write_bytes(c.canonical({'final_sha256': c.sha(final_raw),
        'registration_sha256': c.sha(raw), 'started_sha256': c.sha(started)}))
    return raw, final


@pytest.mark.parametrize('present', [(), ('full',), ('full', 'core')])
def test_failure_retains_every_existing_record_without_acceptance(tmp_path, present):
    value, adapter, composition = case(tmp_path)
    for name in present:
        Path(adapter.spec._agentic_artifact_paths[name]).write_bytes((name + ' failed fixture\n').encode())
    prepared = capture.incomplete_capture(composition, value['attempt_directory'], adapter, 'declared stop')
    assert prepared['replay_complete'] is False
    with pytest.raises(ValueError, match='complete native saved capture'):
        gates.saved_gate(prepared)
    raw, final = publish(value, prepared)
    rows = reader.list_retained_records(raw)
    assert final['state'] == 'failed' and final['runtime_gates_passed'] is False
    assert {row['role'] for row in rows if row['kept']} == set(present)
    for row in rows:
        if row['kept']:
            saved = Path(row['retained_path']).read_bytes()
            assert row['bytes'] == len(saved) and row['sha256'] == c.sha(saved)
        else:
            assert 'FileNotFoundError' in row['reason']


def test_final_floor_failure_keeps_both_records_and_live_phase(tmp_path):
    from tests.test_native_shared_phase import Trace
    trace = Trace(); trace.assembly(); trace.final_checks()
    trace.helper('final_receipts', code=1)
    with pytest.raises(ValueError, match='current final checks'):
        trace.helper('final_source_inventory')
    phase = trace.state.report(complete=True)
    assert phase['passed'] is False and 'final_receipts' not in phase['current_checks']
    value, adapter, composition = case(tmp_path)
    for name in ('full', 'core', 'report'):
        Path(adapter.spec._agentic_artifact_paths[name]).write_bytes((name + ' rejected by floor\n').encode())
    prepared = capture.incomplete_capture(composition, value['attempt_directory'], adapter,
        'declared final coverage-floor failure', live_phase_report=phase)
    raw, final = publish(value, prepared)
    assert all(row['kept'] for row in reader.list_retained_records(raw))
    phase_pin = final['retained_artifacts']['phase_report']
    assert c.strict_json(Path(phase_pin['retained_path']).read_bytes()) == phase
    assert final['retained_artifacts']['report']['kept'] is True
    with pytest.raises(ValueError, match='complete native saved capture'):
        gates.saved_gate(prepared)


@pytest.mark.parametrize('replacement', ['symlink', 'directory', 'unreadable'])
def test_nonregular_or_unreadable_record_is_reported_without_blocking_publication(tmp_path, monkeypatch, replacement):
    value, adapter, composition = case(tmp_path)
    full = Path(adapter.spec._agentic_artifact_paths['full'])
    core = Path(adapter.spec._agentic_artifact_paths['core']); core.write_bytes(b'core evidence')
    if replacement == 'symlink':
        full.symlink_to(core)
    elif replacement == 'directory':
        full.mkdir()
    else:
        full.write_bytes(b'unreadable full')
        original = capture.evidence.read_regular
        def refuse(path, *args, **kwargs):
            if path == str(full):
                raise PermissionError('declared unreadable fixture')
            return original(path, *args, **kwargs)
        monkeypatch.setattr(capture.evidence, 'read_regular', refuse)
    prepared = capture.incomplete_capture(composition, value['attempt_directory'], adapter, 'declared stop')
    raw, final = publish(value, prepared)
    rows = reader.list_retained_records(raw)
    assert rows[0]['kept'] is False and rows[0]['reason']
    assert rows[1]['kept'] is True
    assert final['runtime_gates_passed'] is False


def test_reader_is_read_only_uses_retained_copies_and_rejects_tampering(tmp_path):
    value, adapter, composition = case(tmp_path)
    for name in ('full', 'core'):
        Path(adapter.spec._agentic_artifact_paths[name]).write_bytes(name.encode())
    prepared = capture.incomplete_capture(composition, value['attempt_directory'], adapter, 'declared stop')
    raw, final = publish(value, prepared)
    # Later changes to working outputs cannot erase retained historical bytes.
    Path(adapter.spec._agentic_artifact_paths['full']).write_bytes(b'changed current file')
    Path(adapter.spec._agentic_artifact_paths['core']).unlink()
    before = {str(path): path.read_bytes() for path in tmp_path.rglob('*') if path.is_file()}
    rows = reader.list_retained_records(raw)
    assert len(rows) == 2 and all(row['kept'] for row in rows)
    assert before == {str(path): path.read_bytes() for path in tmp_path.rglob('*') if path.is_file()}
    copy = Path(rows[0]['retained_path']); copy.chmod(0o600); copy.write_bytes(b'evil')
    with pytest.raises(ValueError, match='changed'):
        reader.list_retained_records(raw)


@pytest.mark.parametrize('field,value', [('state', 'completed_pending_independent_review'),
    ('runtime_gates_passed', True), ('scientific_acceptance', 'accepted')])
def test_reader_never_lists_a_forged_success_as_failed_evidence(tmp_path, field, value):
    registration, adapter, composition = case(tmp_path)
    prepared = capture.incomplete_capture(composition, registration['attempt_directory'], adapter, 'declared stop')
    raw, final = publish(registration, prepared)
    final[field] = value
    directory = Path(registration['evidence_directory'])
    final_raw = c.canonical(final); (directory / 'final.json').write_bytes(final_raw)
    marker = c.strict_json((directory / 'published.json').read_bytes())
    marker['final_sha256'] = c.sha(final_raw); (directory / 'published.json').write_bytes(c.canonical(marker))
    with pytest.raises(ValueError, match='failed, unaccepted'):
        reader.list_retained_records(raw)


@pytest.mark.parametrize('changing_full', [False, True])
def test_public_failed_attempt_retains_records_and_reads_back_exactly(tmp_path, monkeypatch, changing_full):
    """Actual public finalizer; declared invalid runtime, no peer dispatch."""
    from tests.test_native_shared_execution import make_case
    from data_sheets_schema import native_shared_execution_orchestration as execute
    from data_sheets_schema import native_execution_authority_v2 as authority
    monkeypatch.chdir(authority.ROOT)
    fixture = make_case(tmp_path / 'retained-runtime-failure')
    attempt = Path(fixture['value']['attempt_directory'])
    full = str(fixture['spec']._agentic_artifact_paths['full'])
    original_read = capture.evidence.read_regular
    changed = []
    def change_optional_after_read(path, role, **kwargs):
        member = original_read(path, role, **kwargs)
        if changing_full and role == 'retained_phase_report' and not changed:
            Path(full).write_bytes(b'X' + Path(full).read_bytes()[1:])
            changed.append(True)
        return member
    monkeypatch.setattr(capture.evidence, 'read_regular', change_optional_after_read)
    def stop_after_records(value):
        for name in ('full', 'core'):
            path = Path(fixture['spec']._agentic_artifact_paths[name])
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((name + ' failed fixture\n').encode())
        for name in ('transcript.jsonl', 'control.jsonl', 'stderr.txt'):
            (attempt / name).write_bytes(b'{}\n')
        (Path(value['environment']['HOME']) / 'declared-invalid-runtime').write_text('offline fixture\n')
        raise RuntimeError('declared failure after writing both records, before any peer dispatch')
    monkeypatch.setattr(execute, '_synthetic_runtime_observation', stop_after_records)
    result = execute.synthetic_launch(fixture['raw'], **fixture['kwargs'])
    (fixture['root'] / 'actual-failed-result.json').write_bytes(c.canonical(result))
    assert result['state'] == 'failed' and result['runtime_gates_passed'] is False
    assert result['retained_artifacts']['phase_report']['kept'] is True
    assert result['retained_artifacts']['report']['kept'] is False
    assert result['capture_problems']
    for name in ('transcript.jsonl', 'control.jsonl', 'stderr.txt'):
        assert result['captured_files'][str(attempt / name)]['sha256'] == c.sha(b'{}\n')
    if changing_full:
        assert changed == [True]
        assert result['retained_artifacts']['full']['kept'] is False
        assert 'changed before publication' in result['retained_artifacts']['full']['reason']
        for catalog in ('captured_files', 'captured_aliases', 'captured_metadata', 'captured_alias_metadata'):
            assert full not in result[catalog]
    assert execute.read_final(fixture['raw']) == result
    rows = reader.list_retained_records(fixture['raw'])
    assert {row['role'] for row in rows if row['kept']} == ({'core'} if changing_full else {'full', 'core'})
    for row in rows:
        if row['kept']:
            assert row['sha256'] == c.sha((row['role'] + ' failed fixture\n').encode())


@pytest.mark.parametrize('mutation', ['modify', 'remove', 'symlink'])
def test_optional_instability_removes_every_snapshot_reference(tmp_path, monkeypatch, mutation):
    value, adapter, composition = case(tmp_path)
    full, core = (Path(adapter.spec._agentic_artifact_paths[name]) for name in ('full', 'core'))
    full.write_bytes(b'full'); core.write_bytes(b'core')
    original = capture.evidence.read_regular
    changed = []
    def mutate_after_reads(path, role, **kwargs):
        member = original(path, role, **kwargs)
        if role == 'retained_phase_report' and not changed:
            changed.append(True)
            if mutation == 'modify':
                full.write_bytes(b'evil')
            else:
                full.unlink()
                if mutation == 'symlink':
                    full.symlink_to(core)
        return member
    monkeypatch.setattr(capture.evidence, 'read_regular', mutate_after_reads)
    prepared = capture.incomplete_capture(composition, value['attempt_directory'], adapter,
                                          'fixture failure', live_phase_report={'passed': False})
    snap = prepared['snapshot']
    assert str(full) not in snap.raw and str(core) in snap.raw
    assert all(member.captured.pin.path != str(full) for member in snap.members.values())
    for mapping in (snap.roles, snap.aliases, snap.metadata, snap.alias_metadata):
        assert str(full) not in mapping
    raw, result = publish(value, prepared)
    assert result['retained_artifacts']['full']['kept'] is False
    assert result['retained_artifacts']['full']['reason']
    assert result['retained_artifacts']['phase_report']['kept'] is True
    assert reader.list_retained_records(raw)[1]['kept'] is True


def test_public_finalization_after_injected_final_floor_failure(tmp_path, monkeypatch):
    """Public lifetime with an injected final-stage outcome, not a live helper run."""
    from tests.test_native_shared_execution import make_case
    from tests.test_native_shared_phase import Trace
    from data_sheets_schema import native_shared_execution_orchestration as execute
    from data_sheets_schema import native_execution_authority_v2 as authority
    from data_sheets_schema import native_execution_orchestration as engine
    from data_sheets_schema import native_shared_controller_orchestration as controller
    monkeypatch.chdir(authority.ROOT)
    fixture = make_case(tmp_path / 'public-final-floor')
    phase = {}
    original_report = controller.CallbackAdapter.report
    def report(self, *args, **kwargs):
        result = original_report(self, *args, **kwargs)
        if phase:
            result['phase_history'] = phase['report']
        return result
    monkeypatch.setattr(controller.CallbackAdapter, 'report', report)
    def final_floor_failure(controls, argv, **kwargs):
        trace = Trace(); trace.assembly(); trace.final_checks()
        trace.helper('final_receipts', code=1)
        phase['report'] = trace.state.report(complete=True)
        assert phase['report']['passed'] is False
        assert 'final_receipts' not in phase['report']['current_checks']
        for name in ('full', 'core'):
            path = Path(fixture['spec']._agentic_artifact_paths[name])
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((name + ' final floor failure\n').encode())
        attempt = Path(fixture['value']['attempt_directory'])
        for name in ('transcript.jsonl', 'control.jsonl', 'stderr.txt'):
            (attempt / name).write_bytes(b'{}\n')
        kwargs['record_stop']('injected final-stage receipt coverage-floor failure')
        return 1
    monkeypatch.setattr(engine, '_execute_child', final_floor_failure)
    result = execute.synthetic_launch(fixture['raw'], **fixture['kwargs'])
    assert phase, 'public lifetime never reached the injected final-stage failure'
    assert result['state'] == 'failed' and result['runtime_gates_passed'] is False
    assert 'coverage-floor failure' in result['first_stop']
    assert all(result['retained_artifacts'][name]['kept'] for name in ('full', 'core', 'phase_report'))
    saved_phase = Path(result['retained_artifacts']['phase_report']['retained_path']).read_bytes()
    assert c.strict_json(saved_phase) == phase['report']
    assert execute.read_final(fixture['raw']) == result
    assert {row['role'] for row in reader.list_retained_records(fixture['raw']) if row['kept']} == {'full', 'core'}


def test_reader_also_lists_existing_complete_capture_of_a_late_failure(tmp_path):
    """Archive-layout unit only; no claim that the fabricated run completed."""
    value, adapter, composition = case(tmp_path)
    for name in ('full', 'core'):
        Path(adapter.spec._agentic_artifact_paths[name]).write_bytes(name.encode())
    prepared = capture.incomplete_capture(composition, value['attempt_directory'], adapter, 'late failure fixture')
    raw, final = publish(value, prepared)
    del final['retained_artifacts']
    for name in ('full', 'core'):
        final['captured_files'][adapter.spec._agentic_artifact_paths[name]]['roles'] = ['final_' + name]
    directory = Path(value['evidence_directory'])
    final_raw = c.canonical(final); (directory / 'final.json').write_bytes(final_raw)
    marker = c.strict_json((directory / 'published.json').read_bytes())
    marker['final_sha256'] = c.sha(final_raw); (directory / 'published.json').write_bytes(c.canonical(marker))
    assert {row['role'] for row in reader.list_retained_records(raw) if row['kept']} == {'full', 'core'}
    projection = reader.list_retained_records(raw)[0]['retained_path']
    Path(projection).chmod(0o600); Path(projection).write_bytes(b'evil')
    with pytest.raises(ValueError, match='changed'):
        reader.list_retained_records(raw)
