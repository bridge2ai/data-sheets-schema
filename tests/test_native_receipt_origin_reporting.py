"""Opt-in origin reports from synthetic saved bytes; never provider evidence.

The two existing offline consumer fixtures use genuine local checkers, a
neutral recipe or an ordinary Python fake CLI. Fabricated registrations,
review/CI/owner documents and runtime observations are software test data.
"""
from copy import deepcopy
import builtins
import io
import os
from pathlib import Path
import socket
import subprocess

import pytest

from data_sheets_schema import native_attribution_registration as draft
from data_sheets_schema import native_attribution_results as replay
from data_sheets_schema import native_attempt_supervisor as neutral
from data_sheets_schema import native_execution as native
from data_sheets_schema import native_execution_registration as registration
from data_sheets_schema import native_receipt_origin as reporting
from data_sheets_schema import receipt_origin as classifier
from tests.test_native_attempt_supervisor import make_case
from tests.test_native_execution import make_native_case, fake_observation
from tests.test_receipt_origin_record import _three_origins


_OMITTED = object()


def _registration(case, family, selector=_OMITTED):
    value = case['value']
    options = {} if selector is _OMITTED else {'receipt_origin_version': selector}
    common = dict(attempt_id=value['attempt_id'], attempt_directory=value['attempt_directory'],
                  evidence_directory=value['evidence_directory'], **options)
    if family == 'neutral_supervisor':
        return neutral.registration(value['composition'], value['fixture'], **common,
            deadline_seconds=value['deadline_seconds'], synthetic_runtime=value['synthetic_runtime'])
    return registration.registration(value['composition'], value['system_path'], **common,
        permission_probe_path=value['permission_probe'], runtime=value['runtime'])


@pytest.fixture(scope='module', params=['neutral_supervisor', 'native_attribution'])
def registered_case(request, tmp_path_factory):
    family = request.param
    root = tmp_path_factory.mktemp('origin-registration') / family
    case = make_case(root) if family == 'neutral_supervisor' else make_native_case(root)
    return family, case


def test_default_and_explicit_zero_preserve_registration_bytes(registered_case):
    family, case = registered_case
    implicit = _registration(case, family)
    explicit = _registration(case, family, 0)
    assert reporting.KEY not in implicit
    assert draft._encoded(implicit) == draft._encoded(explicit) == case['raw']
    verifier = neutral.verified if family == 'neutral_supervisor' else registration.verified
    assert verifier(case['raw']) == implicit


@pytest.mark.parametrize('selector', [True, False, None, '1', '0', 1.0, -1, 2, [], {}])
def test_only_exact_integer_version_is_admitted(registered_case, selector):
    family, case = registered_case
    with pytest.raises((TypeError, ValueError), match='origin|version'):
        _registration(case, family, selector)
    assert not Path(case['value']['attempt_directory']).exists()


def test_registration_derives_paths_and_refuses_forged_declarations(registered_case):
    family, case = registered_case
    selected = _registration(case, family, 1)
    declaration = selected[reporting.KEY]
    assert declaration == reporting.declaration(selected['attempt_directory'],
                                                 case['spec']._agentic_artifact_paths)
    verifier = neutral.verified if family == 'neutral_supervisor' else registration.verified
    assert verifier(draft._encoded(selected)) == selected
    for field, replacement in [('version', True), ('version', 0), ('transcript_path', '/foreign/transcript.jsonl'),
                                ('receipt_path', '/foreign/receipt.yaml'), ('full_path', '/foreign/full.yaml')]:
        changed = deepcopy(selected)
        changed[reporting.KEY][field] = replacement
        with pytest.raises((TypeError, ValueError, KeyError)):
            verifier(draft._encoded(changed))
    changed = deepcopy(selected)
    changed[reporting.KEY]['extra'] = 'caller-selected identity'
    with pytest.raises((TypeError, ValueError, KeyError)):
        verifier(draft._encoded(changed))
    assert not Path(selected['attempt_directory']).exists()


def _captured(root, family='neutral_supervisor', mutate_run=None):
    run, transcript = _three_origins(root)
    run.full.write_text('id: x\n')
    if mutate_run is not None:
        mutate_run(run)
        transcript = run.transcript()
    snapshot = replay.Capture(root)
    for path, role in ((transcript, 'transcript'), (run.receipt, 'receipt'), (run.full, 'full')):
        snapshot.read(path, role)
    snapshot.path(run.receipt.parent / 'CHORUS_d4d_core.yaml')
    snapshot.sealed = True
    kind = next(key for key, name in reporting.FAMILIES.items() if name == family)
    value = {'kind': kind, reporting.KEY: reporting.declaration(str(root),
        {'receipt': str(run.receipt), 'full': str(run.full)})}
    gate = {'checked': True, 'passed': False, 'floors': {'minimum_chunks': True},
            'receipts': {'snippets': {'verified': 5}}, 'reason': 'Existing gate remains failed.'}
    return value, gate, snapshot, run


def _basis(snapshot):
    return {'raw': snapshot.raw, 'aliases': snapshot.aliases, 'metadata': snapshot.metadata}


@pytest.mark.parametrize('family', ['neutral_supervisor', 'native_attribution'])
def test_sealed_three_origins_preserve_failed_gate_and_use_no_ambient_io(tmp_path, monkeypatch, family):
    value, gate, snapshot, _ = _captured(tmp_path / family, family)
    original = deepcopy(gate)
    expected = reporting.attach(value, gate, **_basis(snapshot))
    origin = expected[reporting.REPORT_KEY]
    assert origin['family'] == family
    assert origin['original_receipt']['status'] == 'checked'
    assert origin['original_receipt']['origin'] == {
        'contemporaneous': 3, 'phase1_correction': 1, 'phase3_backport': 1}
    assert origin['original_receipt']['non_checks'] == list(classifier.NON_CHECKS)
    assert {key: item for key, item in expected.items() if key != reporting.REPORT_KEY} == original

    def forbidden(*args, **kwargs):
        raise AssertionError('receipt-origin reporting attempted ambient I/O or resolution')

    with monkeypatch.context() as patch:
        for owner, name in ((builtins, 'open'), (io, 'open'), (os, 'open'), (os, 'stat'),
                            (os, 'lstat'), (os, 'readlink'), (os, 'getcwd'), (os, 'getcwdb'),
                            (os.path, 'realpath'), (os.path, 'abspath'), (Path, 'read_bytes'),
                            (Path, 'resolve'), (Path, 'cwd'), (subprocess, 'Popen'),
                            (os, 'system'), (socket, 'socket'), (socket, 'getaddrinfo')):
            patch.setattr(owner, name, forbidden)
        patch.setattr(classifier, 'origin', forbidden)
        actual = reporting.attach_prepared(value, {'receipts': gate}, {'snapshot': snapshot})
        reporting.check_saved(value, actual['receipts'], **_basis(snapshot))
    assert draft._encoded(actual['receipts']) == draft._encoded(expected)
    assert gate == original


def test_default_attachment_keeps_exact_gate_shape_without_consuming_basis():
    gate = {'checked': False, 'passed': False, 'reason': 'capture unavailable'}
    assert reporting.attach({}, gate, raw=None, aliases=None, metadata=None) is gate
    gates = {'receipts': gate, 'first_stop': {'checked': True, 'passed': False, 'reason': 'original'}}
    assert reporting.attach_prepared({}, gates, object()) is gates
    assert draft._encoded(gates) == draft._encoded({
        'receipts': {'checked': False, 'passed': False, 'reason': 'capture unavailable'},
        'first_stop': {'checked': True, 'passed': False, 'reason': 'original'}})
    with pytest.raises(ValueError, match='undeclared'):
        reporting.check_saved({}, {**gate, reporting.REPORT_KEY: {}}, raw={}, aliases={}, metadata={})


def test_report_and_receipts_gate_are_deeply_detached(tmp_path):
    value, gate, snapshot, _ = _captured(tmp_path / 'detached')
    expected = reporting.attach(value, gate, **_basis(snapshot))
    changed = reporting.attach(value, gate, **_basis(snapshot))
    changed['receipts']['snippets']['verified'] = 900
    changed[reporting.REPORT_KEY]['declaration']['full_path'] = '/changed'
    changed[reporting.REPORT_KEY]['inputs']['transcript']['sha256'] = '0' * 64
    changed[reporting.REPORT_KEY]['original_receipt']['non_checks'].clear()
    changed[reporting.REPORT_KEY]['original_receipt']['origin']['contemporaneous'] = 900
    assert reporting.attach(value, gate, **_basis(snapshot)) == expected
    assert gate['receipts']['snippets']['verified'] == 5


@pytest.mark.parametrize('damage', [
    'missing_transcript', 'missing_full', 'missing_receipt', 'receipt_mismatch',
    'malformed_transcript', 'non_utf8_transcript', 'wrong_size', 'nonregular',
    'redirected_transcript_identity', 'conflicting_receipt_identity', 'relative_alias_target'])
def test_incomplete_or_inconsistent_capture_is_unknown_without_counts(tmp_path, damage):
    value, gate, snapshot, _ = _captured(tmp_path / damage)
    paths = value[reporting.KEY]
    transcript, full, receipt = (paths[key] for key in ('transcript_path', 'full_path', 'receipt_path'))
    if damage.startswith('missing_'):
        target = {'missing_transcript': transcript, 'missing_full': full, 'missing_receipt': receipt}[damage]
        snapshot.raw.pop(target)
    elif damage == 'receipt_mismatch':
        snapshot.raw[receipt] += b'# captured receipt differs from last write\n'
        snapshot.metadata[receipt]['size'] = len(snapshot.raw[receipt])
    elif damage in ('malformed_transcript', 'non_utf8_transcript'):
        snapshot.raw[transcript] = b'{' if damage == 'malformed_transcript' else b'\xff\n'
        snapshot.metadata[transcript]['size'] = len(snapshot.raw[transcript])
    elif damage == 'wrong_size':
        snapshot.metadata[receipt]['size'] += 1
    elif damage == 'nonregular':
        snapshot.metadata[full]['regular'] = False
    elif damage == 'redirected_transcript_identity':
        snapshot.aliases[transcript] = full
    elif damage == 'conflicting_receipt_identity':
        snapshot.aliases[receipt] = full
    else:
        snapshot.aliases[transcript] = 'relative/transcript.jsonl'
    attached = reporting.attach(value, gate, **_basis(snapshot))
    report = attached[reporting.REPORT_KEY]['original_receipt']
    assert report['status'] == 'unknown'
    assert report['reasons']
    for field in ('origin', 'snippets', 'deltas', 'post_draft', 'post_draft_entries', 'by_chunk'):
        assert field not in report
    assert {key: item for key, item in attached.items() if key != reporting.REPORT_KEY} == gate
    reporting.check_saved(value, attached, **_basis(snapshot))


def test_unrecorded_different_basename_write_is_not_silently_ignored(tmp_path):
    def add_unknown_write(run):
        run.write(run.root / 'unregistered-alias.yaml', 'could alias a receipt\n')
    value, gate, snapshot, _ = _captured(tmp_path / 'unknown-alias', mutate_run=add_unknown_write)
    report = reporting.report(value, gate, **_basis(snapshot))['original_receipt']
    assert report['status'] == 'unknown'
    assert 'origin' not in report
    assert any('captured path identity' in reason for reason in report['reasons'])


def test_recorded_alias_with_different_basename_uses_captured_physical_bytes(tmp_path):
    value, gate, snapshot, run = _captured(tmp_path / 'known-alias')
    expected = reporting.report(value, gate, **_basis(snapshot))
    receipt = value[reporting.KEY]['receipt_path']
    physical = str(run.root / 'renamed-physical-receipt.yaml')
    snapshot.raw[physical] = snapshot.raw.pop(receipt)
    snapshot.metadata[physical] = snapshot.metadata.pop(receipt)
    snapshot.aliases[receipt] = physical
    snapshot.aliases[physical] = physical
    # This is recorded data only: that physical file is deliberately absent.
    assert not Path(physical).exists()
    actual = reporting.report(value, gate, **_basis(snapshot))
    assert actual['inputs']['original_receipt']['captured_path'] == physical
    assert actual['inputs']['original_receipt']['sha256'] == expected['inputs']['original_receipt']['sha256']
    assert actual['original_receipt'] == expected['original_receipt']


def test_failed_attempt_without_any_capture_has_reconstructible_unknown(tmp_path):
    value, gate, _, _ = _captured(tmp_path / 'absent')
    gates = {'receipts': gate, 'first_stop': {'checked': True, 'passed': False, 'reason': 'first stop'}}
    original = deepcopy(gates)
    attached = reporting.attach_prepared(value, gates, None)
    origin = attached['receipts'][reporting.REPORT_KEY]
    assert origin['original_receipt']['status'] == 'unknown'
    assert origin['inputs'] == {'transcript': None, 'full': None, 'original_receipt': None}
    assert attached['first_stop'] == original['first_stop']
    assert gates == original
    reporting.check_saved(value, attached['receipts'], raw={}, aliases={}, metadata={})


@pytest.mark.parametrize('seal', [False, None, 0, 1, 'true', [], 'missing'])
def test_unsealed_or_malformed_capture_never_produces_counts(tmp_path, monkeypatch, seal):
    value, gate, snapshot, _ = _captured(tmp_path / 'seal')
    gates = {'receipts': gate, 'first_stop': {'checked': True, 'passed': False, 'reason': 'original stop'}}
    complete = reporting.attach_prepared(value, gates, {'snapshot': snapshot})
    assert complete['receipts'][reporting.REPORT_KEY]['original_receipt']['origin']['contemporaneous'] == 3
    if seal == 'missing':
        del snapshot.sealed
    else:
        snapshot.sealed = seal

    def forbidden(*args, **kwargs):
        raise AssertionError('unsealed origin acquisition read a path or invoked the classifier')

    with monkeypatch.context() as patch:
        patch.setattr(Path, 'read_bytes', forbidden)
        patch.setattr(Path, 'resolve', forbidden)
        patch.setattr(classifier, 'origin_captured', forbidden)
        patch.setattr(classifier, 'origin', forbidden)
        incomplete = reporting.attach_prepared(value, gates, {'snapshot': snapshot})
    assert incomplete == reporting.attach_prepared(value, gates, None)
    assert incomplete['receipts'][reporting.REPORT_KEY]['original_receipt']['status'] == 'unknown'
    assert incomplete['first_stop'] == gates['first_stop']


@pytest.mark.parametrize('tamper', ['counts', 'family', 'declaration', 'input_hash', 'input_size', 'missing_report'])
def test_reconstruction_rejects_forged_derived_reports(tmp_path, tamper):
    value, gate, snapshot, _ = _captured(tmp_path / tamper)
    attached = reporting.attach(value, gate, **_basis(snapshot))
    origin = attached[reporting.REPORT_KEY]
    if tamper == 'counts':
        origin['original_receipt']['origin']['contemporaneous'] += 1
    elif tamper == 'family':
        origin['family'] = 'unregistered_family'
    elif tamper == 'declaration':
        origin['declaration']['receipt_path'] = '/another/receipt.yaml'
    elif tamper == 'input_hash':
        origin['inputs']['transcript']['sha256'] = '0' * 64
    elif tamper == 'input_size':
        origin['inputs']['full']['bytes'] = True
    else:
        attached.pop(reporting.REPORT_KEY)
    with pytest.raises(ValueError, match='receipt-origin'):
        reporting.check_saved(value, attached, **_basis(snapshot))


def _opt_in(case, family):
    """Rebind only the existing explicitly fabricated fixture authorities."""
    value = _registration(case, family, 1)
    case = {**case, 'value': value, 'raw': draft._encoded(value)}
    if family == 'native_attribution':
        for key in ('review_path', 'ci_path'):
            path = case['kwargs'][key]
            document = draft._json(path.read_bytes())
            document['registration_sha256'] = draft._sha(case['raw'])
            path.write_bytes(draft._encoded(document))
        path = case['kwargs']['launch_word_path']
        document = draft._json(path.read_bytes())
        document.update(registration_sha256=draft._sha(case['raw']),
            review_sha256=draft._sha(case['kwargs']['review_path'].read_bytes()),
            ci_sha256=draft._sha(case['kwargs']['ci_path'].read_bytes()))
        path.write_bytes(draft._encoded(document))
    return case


@pytest.fixture(scope='module', params=['neutral_supervisor', 'native_attribution'])
def completed_origin_case(request, tmp_path_factory):
    family = request.param
    root = tmp_path_factory.mktemp('origin-consumer') / family
    case = make_case(root) if family == 'neutral_supervisor' else make_native_case(root)
    case = _opt_in(case, family)
    consumer = neutral if family == 'neutral_supervisor' else native
    before_attachment = []
    attach = reporting.attach_prepared

    def observe(value, gates, prepared):
        before_attachment.append(deepcopy(gates))
        return attach(value, gates, prepared)

    def forbidden(*args, **kwargs):
        raise AssertionError('ambient receipt-origin path reader invoked')

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(reporting, 'attach_prepared', observe)
        patch.setattr(classifier, 'origin', forbidden)
        patch.setattr(native, '_probe_runtime', fake_observation)
        result = (neutral.supervise(case['raw']) if family == 'neutral_supervisor'
                  else native.launch(case['raw'], **case['kwargs']))
    completion_key = 'engineering_completion' if family == 'neutral_supervisor' else 'runtime_gates_passed'
    assert result[completion_key], result['first_stop']
    assert len(before_attachment) == 1
    assert result['first_stop'] is None
    assert set(result['gates']) == set(consumer.GATES if family == 'neutral_supervisor' else native.gates.GATES)
    undecorated = deepcopy(result['gates'])
    undecorated['receipts'].pop(reporting.REPORT_KEY)
    assert undecorated == before_attachment[0]
    assert consumer.read_final(case['raw']) == result
    return family, case, consumer, result


def test_actual_offline_consumers_bind_saved_reporting_without_promoting_gates(completed_origin_case):
    family, case, consumer, result = completed_origin_case
    origin = result['gates']['receipts'][reporting.REPORT_KEY]
    assert origin['family'] == family
    assert origin['declaration'] == case['value'][reporting.KEY]
    for name, key in [('transcript', 'transcript_path'), ('full', 'full_path'), ('original_receipt', 'receipt_path')]:
        identity = origin['inputs'][name]
        path = case['value'][reporting.KEY][key]
        assert identity['path'] == path
        assert identity['sha256'] == result['captured_files'][identity['captured_path']]['sha256']
        assert identity['bytes'] == result['captured_files'][identity['captured_path']]['bytes']
    # Existing fixture tool-result metadata is intentionally synthetic. Its
    # completeness does not entitle the history instrument to infer evidence.
    measured = origin['original_receipt']
    assert measured['status'] in ('checked', 'unknown')
    if measured['status'] == 'unknown':
        assert measured['reasons'] and 'origin' not in measured
    assert consumer.read_final(case['raw']) == result


def _rewrite_final(case, result):
    evidence = Path(case['value']['evidence_directory'])
    raw = draft._encoded(result)
    (evidence / 'final.json').write_bytes(raw)
    marker = draft._json((evidence / 'published.json').read_bytes())
    marker['final_sha256'] = draft._sha(raw)
    (evidence / 'published.json').write_bytes(draft._encoded(marker))


@pytest.mark.parametrize('tamper', ['counts', 'declared_path', 'input_hash', 'family', 'missing_report'])
def test_saved_readers_reject_report_tampering_after_publication_rehash(completed_origin_case, tamper):
    _, case, consumer, original = completed_origin_case
    changed = deepcopy(original)
    receipt_gate = changed['gates']['receipts']
    origin = receipt_gate[reporting.REPORT_KEY]
    if tamper == 'counts':
        origin['original_receipt']['origin'] = {
            'contemporaneous': 999, 'phase1_correction': 0, 'phase3_backport': 0}
    elif tamper == 'declared_path':
        origin['declaration']['receipt_path'] = '/unregistered/receipt.yaml'
    elif tamper == 'input_hash':
        origin['inputs']['transcript']['sha256'] = '0' * 64
    elif tamper == 'family':
        origin['family'] = 'native_shared'
    else:
        receipt_gate.pop(reporting.REPORT_KEY)
    try:
        _rewrite_final(case, changed)
        with pytest.raises(ValueError, match='receipt-origin'):
            consumer.read_final(case['raw'])
    finally:
        _rewrite_final(case, original)
    assert consumer.read_final(case['raw']) == original


@pytest.mark.parametrize('damage', ['bytes', 'alias'])
def test_saved_capture_drift_is_refused_before_classification(completed_origin_case, tmp_path, damage):
    _, case, consumer, original = completed_origin_case
    declaration = case['value'][reporting.KEY]
    target = Path(declaration['receipt_path'])
    raw, info = target.read_bytes(), target.stat()
    moved = tmp_path / 'same-bytes-other-identity.yaml'
    try:
        if damage == 'bytes':
            target.write_bytes(raw + b'# changed after capture\n')
        else:
            target.rename(moved)
            target.symlink_to(moved)
        with pytest.raises((OSError, ValueError), match='captured|capture|metadata|identity|basis'):
            consumer.read_final(case['raw'])
    finally:
        if damage == 'alias':
            target.unlink()
            moved.rename(target)
        else:
            target.write_bytes(raw)
        os.utime(target, ns=(info.st_atime_ns, info.st_mtime_ns))
    assert consumer.read_final(case['raw']) == original


def test_auth_refused_native_outcome_keeps_stop_and_rechecks_unknown(tmp_path, monkeypatch):
    case = _opt_in(make_native_case(tmp_path / 'auth-refused'), 'native_attribution')

    def refused(_value):
        raise RuntimeError('synthetic refusal before any CLI child')

    monkeypatch.setattr(native, '_probe_runtime', refused)
    with native.authority.loaded_dependencies(case['value']['dependencies']) as modules:
        def forbidden(*args, **kwargs):
            raise AssertionError('auth-refused attempt dispatched a child')
        monkeypatch.setattr(modules['run_native_canary'], 'execute_child', forbidden)
        monkeypatch.setattr(classifier, 'origin', forbidden)
        result = native.launch(case['raw'], **case['kwargs'])
    assert result['runtime_gates_passed'] is False
    assert result['state'] == 'failed'
    assert result['first_stop'] == 'launch or runtime failed: RuntimeError'
    assert result['gates']['first_stop']['reason'] == result['first_stop']
    origin = result['gates']['receipts'][reporting.REPORT_KEY]
    assert origin['original_receipt']['status'] == 'unknown'
    assert 'origin' not in origin['original_receipt']
    assert origin['inputs'] == {'transcript': None, 'full': None, 'original_receipt': None}
    assert native.read_final(case['raw']) == result
    changed = deepcopy(result)
    changed['gates']['receipts'][reporting.REPORT_KEY]['original_receipt'].update(
        status='checked', origin={'contemporaneous': 0, 'phase1_correction': 0, 'phase3_backport': 0})
    try:
        _rewrite_final(case, changed)
        with pytest.raises(ValueError, match='receipt-origin'):
            native.read_final(case['raw'])
    finally:
        _rewrite_final(case, result)
    assert native.read_final(case['raw']) == result


def test_actual_reader_cap_is_exceeded_by_one_admitted_origin_identity(tmp_path):
    """An 8 MiB identity fits the frozen 16 MiB frame limit but not final.json."""
    def expand_full_write_identity(run):
        identity = None
        for event in run.events:
            for item in event.get('message', {}).get('content', []):
                if item.get('name') == 'Write' and item.get('input', {}).get('file_path') == str(run.full):
                    identity = item['id']
        assert identity is not None
        expanded = 'x' * neutral.MAX_BYTES
        for event in run.events:
            for item in event.get('message', {}).get('content', []):
                if item.get('id') == identity:
                    item['id'] = expanded
                if item.get('tool_use_id') == identity:
                    item['tool_use_id'] = expanded

    value, gate, snapshot, _ = _captured(tmp_path / 'actual-size', mutate_run=expand_full_write_identity)
    transcript = snapshot.raw[value[reporting.KEY]['transcript_path']]
    # NativeControl admits each frame at this bound; this is not an oversized
    # frame that the controller would refuse before recording the history.
    assert max(map(len, transcript.splitlines())) < 16 * 1024 * 1024
    attached = reporting.attach(value, gate, **_basis(snapshot))
    origin = attached[reporting.REPORT_KEY]['original_receipt']
    assert origin['status'] == 'checked'
    assert len(origin['boundaries']['full_record_write']['tool_use_id']) == neutral.MAX_BYTES
    final_raw = draft._encoded({'gates': {'receipts': attached}})
    assert len(draft._encoded({'gates': {'receipts': gate}})) < neutral.MAX_BYTES
    assert len(final_raw) > neutral.MAX_BYTES
    with pytest.raises(ValueError, match='receipt-origin final result exceeds'):
        reporting.check_final_bytes(value, final_raw, max_bytes=neutral.MAX_BYTES)


def test_final_preflight_accepts_exact_bound_and_preserves_version_zero(tmp_path):
    value, gate, snapshot, _ = _captured(tmp_path / 'size-boundary')
    raw = draft._encoded({'gates': {'receipts': reporting.attach(value, gate, **_basis(snapshot))}})
    assert reporting.check_final_bytes(value, raw, max_bytes=len(raw)) is None
    with pytest.raises(ValueError, match='receipt-origin final result exceeds'):
        reporting.check_final_bytes(value, raw, max_bytes=len(raw) - 1)
    # Default/explicit selector 0 omits the registration declaration. Legacy
    # final publication behavior is outside this opt-in size-hardening slice.
    assert reporting.check_final_bytes({}, raw, max_bytes=1) is None


@pytest.mark.parametrize('family', ['neutral_supervisor', 'native_attribution'])
def test_both_publishers_refuse_before_final_marker_and_keep_attempt_evidence(tmp_path, monkeypatch, family):
    root = tmp_path / family
    case = make_case(root) if family == 'neutral_supervisor' else make_native_case(root)
    case = _opt_in(case, family)
    original_files = {path: path.read_bytes() for path in root.rglob('*') if path.is_file()}
    observed = []
    check = reporting.check_final_bytes

    def small_final_only(value, raw, *, max_bytes):
        assert max_bytes == neutral.MAX_BYTES
        final = draft._json(raw)
        observed.append(final)
        # Change only this publication bound, after genuine registration and
        # authority admission; no input limit or committed-source check is
        # bypassed to reach the intended writer boundary.
        check(value, raw, max_bytes=len(raw) - 1)

    def refused(*args, **kwargs):
        raise RuntimeError('synthetic no-child publication probe')

    monkeypatch.setattr(reporting, 'check_final_bytes', small_final_only)
    monkeypatch.setattr(native, '_probe_runtime', refused)
    consumer = neutral if family == 'neutral_supervisor' else native
    with consumer.authority.loaded_dependencies(case['value']['dependencies']) as modules:
        monkeypatch.setattr(modules['run_native_canary'], 'execute_child', refused)
        if family == 'neutral_supervisor':
            with pytest.raises(ValueError, match='receipt-origin final result exceeds'):
                neutral.supervise(case['raw'])
        else:
            # Native failure handling preserves the first runtime exception,
            # chaining the later publication refusal instead of replacing it.
            with pytest.raises(RuntimeError, match='synthetic no-child publication probe') as caught:
                native.launch(case['raw'], **case['kwargs'])
            assert isinstance(caught.value.__cause__, ValueError)
            assert 'receipt-origin final result exceeds' in str(caught.value.__cause__)
    assert len(observed) == 1
    final = observed[0]
    expected_stop = ('RuntimeError: synthetic no-child publication probe' if family == 'neutral_supervisor'
                     else 'launch or runtime failed: RuntimeError')
    assert final['first_stop'] == expected_stop
    assert final['gates']['first_stop']['reason'] == expected_stop
    assert final['gates']['receipts'][reporting.REPORT_KEY]['original_receipt']['status'] == 'unknown'
    attempt = Path(case['value']['attempt_directory'])
    evidence = Path(case['value']['evidence_directory'])
    assert (attempt / 'registration.json').read_bytes() == case['raw']
    assert (attempt / 'started.json').is_file()
    assert evidence.is_dir()
    assert not (evidence / 'final.json').exists()
    assert not (evidence / 'published.json').exists()
    for path, raw in original_files.items():
        assert path.read_bytes() == raw
