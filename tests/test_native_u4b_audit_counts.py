"""U4b A1 R2(a): actual stage-derived audit/report comparison, 2026-11-08.

Input records and delivery frames are invented. Stage reconstruction, captured
readers, report extraction and the native evidence gate are real; none is
replaced by a passing comparison. These are not accepted native executions.
"""
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from data_sheets_schema import native_gate_engine as engine
from data_sheets_schema import native_shared_capture as capture
from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_evidence as evidence
from data_sheets_schema.native_shared_results import Snapshot
from tests.test_native_shared_stages import artifact, case, full_roundtrip, supplied
from tests.test_native_shared_gates import isolated_modules, no_execution, pure_gate_members


REPORT = b'The audit identified 1 findings against the record: 1 medium.\n'


def _members(items):
    # Stable invented metadata for captured in-memory fixtures. No live-file
    # identity or permission observation is claimed by this stage-only test.
    return tuple(evidence.PoolMember(item, c.canonical({
        'exists': True, 'regular': True, 'symlink': False, 'links': 1,
        'device': 0, 'inode': index + 1, 'size': item.pin.bytes, 'mtime_ns': 0}))
        for index, item in enumerate(items))


def _captured(prepared, items):
    run = prepared['run']
    pool = evidence.CapturePool(_members(items), ())
    run = replace(run, pool=pool, reader=capture._Reader(run.selection, pool=pool))
    snapshot = Snapshot('/neutral', pool.members)
    snapshot.sealed = True
    return {**prepared, 'run': run, 'snapshot': snapshot}


def _replace_artifact(prepared, role, raw):
    items = [artifact(role, member.captured.pin.path, raw)
             if member.captured.pin.role == role else member.captured
             for member in prepared['run'].pool.members]
    return _captured(prepared, items)


@pytest.fixture
def prepared_counts(case):
    # Load the shared counter dependency before tests install the no-I/O trap.
    from data_sheets_schema import api_runner  # noqa: F401
    completed, completion = full_roundtrip(case)
    selected, binding, phase1, history = completed
    paths = {name: '/neutral/ordinary-' + name for name in ('full', 'core', 'report', 'receipt')}
    report = artifact('final_report', paths['report'], REPORT)
    pool = evidence.CapturePool(_members((completion.assembly, completion.audit, report)), ())
    run = capture._CapturedRun(selection=selected, value={},
        composition={'policy': {'post_final_recorder': {'destination': '/neutral/provenance'}}},
        spec=SimpleNamespace(_agentic_artifact_paths=paths),
        reader=capture._Reader(selected, pool=pool), pool=pool,
        transcript=None, control=None, binding=binding, history=history,
        observations=history.observations, phase1=phase1)
    snapshot = Snapshot('/neutral', pool.members)
    snapshot.sealed = True
    # An unrelated successful evidence flag must never substitute for the
    # actual stage/report comparison tested below.
    return {'run': run, 'snapshot': snapshot, 'final_result': {'checked': True, 'findings': []}}


def test_actual_derived_audit_and_captured_report_emit_equality(prepared_counts, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail('captured audit-count comparison performed ambient file I/O')
    with monkeypatch.context() as trapped:
        trapped.setattr(evidence, 'read_regular', forbidden)
        for name in ('read_bytes', 'read_text', 'is_file', 'open', 'resolve'):
            trapped.setattr(Path, name, forbidden)
        result = engine.evidence_gate(prepared_counts)
    assert result['checked'] is result['passed'] is True
    row = result['audit_counts']
    assert row['checked'] is row['passed'] is True and row['reason'] is None
    comparison = row['comparison']
    assert comparison['status'] == 'consistent'
    assert type(comparison['stated_total']) is type(comparison['computed_total']) is int
    assert comparison['stated_total'] == comparison['computed_total'] == 1
    assert comparison['computed_by_severity'] == {'medium': 1}
    assert comparison['stated_by_severity'] == {'medium': 1}
    actual = {member.captured.pin.role: c.pin_dict(member.captured.pin)
              for member in prepared_counts['run'].pool.members}
    assert row['compared_artifacts'] == {'typed_assembly': actual['typed_assembly'],
        'derived_audit': actual['audit'], 'final_report': actual['final_report']}


@pytest.mark.parametrize('report,status', [
    (b'The audit identified 2 findings against the record: 1 medium.\n', 'mismatch'),
    (b'The audit identified 1 findings against the record: 1 high.\n', 'mismatch'),
    (REPORT + b'The audit identified 2 findings.\n', 'mismatch'),
    (b'A reconciliation narrative without a finding total.\n', 'no_total_stated'),
])
def test_report_totals_cannot_borrow_unrelated_evidence_success(prepared_counts, report, status):
    assert engine.evidence_gate(prepared_counts)['passed'] is True
    changed = _replace_artifact(prepared_counts, 'final_report', report)
    result = engine.evidence_gate(changed)
    assert result['result'] == {'checked': True, 'findings': []}
    assert result['passed'] is False
    row = result['audit_counts']
    assert row['passed'] is False and row['reason']
    assert row['comparison']['status'] == status
    assert row['checked'] is (status != 'no_total_stated')


@pytest.mark.parametrize('missing', ['typed_assembly', 'audit', 'final_report', 'final_result', 'phase1'])
def test_missing_count_inputs_leave_an_explicit_failed_row(prepared_counts, missing):
    if missing == 'final_result':
        changed = {**prepared_counts, 'final_result': None}
    elif missing == 'phase1':
        changed = {**prepared_counts, 'run': replace(prepared_counts['run'], phase1=None)}
    else:
        changed = _captured(prepared_counts, [member.captured for member in prepared_counts['run'].pool.members
                                             if member.captured.pin.role != missing])
    result = engine.evidence_gate(changed)
    assert result['checked'] is result['passed'] is False
    assert result['audit_counts']['checked'] is result['audit_counts']['passed'] is False
    assert result['audit_counts']['reason']


@pytest.mark.parametrize('final', [{}, {'checked': 1, 'findings': []}, {'checked': True, 'findings': None}])
def test_malformed_final_evidence_never_hides_count_refusal(prepared_counts, final):
    result = engine.evidence_gate({**prepared_counts, 'final_result': final})
    assert result['audit_counts']['checked'] is result['audit_counts']['passed'] is False
    assert 'final evidence' in result['audit_counts']['reason']
    assert result['passed'] is False


@pytest.mark.parametrize('role,raw', [
    ('typed_assembly', b'{'), ('audit', b'{'), ('final_report', b'\xff'),
])
def test_malformed_artifacts_leave_an_explicit_failed_row(prepared_counts, role, raw):
    result = engine.evidence_gate(_replace_artifact(prepared_counts, role, raw))
    assert result['checked'] is result['passed'] is False
    assert result['audit_counts']['checked'] is result['audit_counts']['passed'] is False
    assert result['audit_counts']['reason']


def test_consistently_rehashed_audit_still_must_be_stage_derived(prepared_counts):
    run = prepared_counts['run']
    audit = next(member.captured for member in run.pool.members if member.captured.pin.role == 'audit')
    document = c.strict_json(audit.raw)
    document['findings'] = []
    changed = _replace_artifact(prepared_counts, 'audit', c.canonical(document))
    result = engine.evidence_gate(changed)
    assert result['passed'] is False
    assert 'freshly derived assembly audit' in result['audit_counts']['reason']


def test_incomplete_history_cannot_reuse_a_prior_count_comparison(prepared_counts):
    assert engine.evidence_gate(prepared_counts)['passed'] is True
    run = prepared_counts['run']
    changed = {**prepared_counts, 'run': replace(run,
        history=replace(run.history, records=run.history.records[:-1]))}
    result = engine.evidence_gate(changed)
    assert result['audit_counts']['checked'] is result['audit_counts']['passed'] is False
    assert result['audit_counts']['reason'] and result['passed'] is False


@pytest.mark.parametrize('role', ['typed_assembly', 'audit', 'final_report'])
def test_split_snapshot_bytes_refuse_even_when_both_views_are_available(prepared_counts, role):
    member = next(member for member in prepared_counts['run'].pool.members if member.captured.pin.role == role)
    prepared_counts['snapshot'].raw[member.captured.pin.path] += b'\n'
    result = engine.evidence_gate(prepared_counts)
    assert result['passed'] is False
    assert 'differ between captured views' in result['audit_counts']['reason']


def test_report_text_cannot_be_interpreted_as_an_ambient_path(prepared_counts, tmp_path, monkeypatch):
    target = tmp_path / 'external-report.md'
    target.write_bytes(REPORT)
    changed = _replace_artifact(prepared_counts, 'final_report', str(target).encode())
    def forbidden(*args, **kwargs):
        pytest.fail('one-line captured report escaped into ambient path resolution')
    with monkeypatch.context() as trapped:
        trapped.setattr(Path, 'is_file', forbidden)
        trapped.setattr(Path, 'read_text', forbidden)
        result = engine.evidence_gate(changed)
    assert result['passed'] is False
    assert result['audit_counts']['comparison']['status'] == 'no_total_stated'


def test_all_fifteen_gates_retain_count_refusal_despite_unrelated_success(pure_gate_members):
    from tests.test_native_execution_gates import selected
    prepared, runtime = selected()
    prepared['final_result'] = {'checked': True, 'findings': []}
    result = engine.check(prepared, {}, runtime, pure_gate_members, kind='native_shared',
        exit_code=0, shutdown=None, live={}, first_stop=None,
        runtime_authority={'passed': False}, keep_awake={'passed': False})
    from data_sheets_schema.native_shared_gate_primitives import GATES
    assert tuple(result) == GATES and len(result) == 15
    assert result['evidence']['result'] == {'checked': True, 'findings': []}
    assert result['evidence']['passed'] is False
    assert result['evidence']['audit_counts']['checked'] is False
    assert result['evidence']['audit_counts']['passed'] is False
    assert result['evidence']['audit_counts']['reason']
