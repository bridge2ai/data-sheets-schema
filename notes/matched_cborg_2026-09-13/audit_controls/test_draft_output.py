"""Offline preservation, bounded feedback and exact sealing; no source checker."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import sys

import pytest

BASE = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(BASE), str(BASE / 'native_controls')]
from audit_controls import draft_output as draft
from budgeted_cborg import BudgetStop

REJECTED = (BudgetStop, OSError, ValueError)


def grammar_audit():
    # Deliberately no source authority: grammar must not decide quote/coverage truth.
    return {'findings': [], 'summary': 'Synthetic grammar exercise.',
            'source_review': {'artifact': 'original_full', 'sha256': 'a' * 64,
                              'values': [{'path': '/name', 'claims': [{
                                  'text': 'Unverified synthetic text.', 'verdict': 'supported',
                                  'attributed_to': [], 'claim_status': 'fact', 'source_status': 'fact',
                                  'evidence': [{'source': 'unknown.txt', 'chunk': 'unknown',
                                                'quote': 'Not checked against any source.'}],
                                  'reason': 'Only grammar is checked here.'}]}]}}


@pytest.fixture
def case(tmp_path):
    condition = tmp_path.resolve() / 'condition'
    attempt = condition / 'attempts' / 'synthetic'
    output = attempt / 'output'
    for number in (1, 2):
        (output / 'audit-drafts' / f'round-{number}').mkdir(parents=True)
    manifest = {'kind': 'd4d_native_audit_continuation', 'protocol_version': 6,
                'render_version': 18, 'python': sys.executable,
                'job': {'id': 'synthetic', 'attempt_dir': str(attempt),
                        'output_dir': str(output), 'audit_path': str(output / 'audit.json')}}
    path = condition / 'registration.json'
    manifest['audit_drafting'] = draft.specification(manifest, path)
    path.write_text(json.dumps(manifest))
    return manifest, hashlib.sha256(path.read_bytes()).hexdigest()


def write_parts(manifest, number=1, pieces=None):
    pieces = pieces if pieces is not None else [json.dumps(grammar_audit()).encode()]
    parts = []
    for path, raw in zip(manifest['audit_drafting']['rounds'][number - 1]['parts'], pieces):
        Path(path).write_bytes(raw)
        parts.append(draft.describe(path, raw))
    return parts


def accepted(case, *, second=False):
    manifest, identity = case
    reports = []
    if second:
        write_parts(manifest, pieces=[b'{"incomplete":'])
        reports.append(draft.check_round(manifest, identity, 1))
        assert reports[-1]['grammar']['passed'] is False
    number = 2 if second else 1
    parts = write_parts(manifest, number)
    reports.append(draft.check_round(manifest, identity, number))
    assert reports[-1]['grammar']['passed'] is True
    seal = draft.seal(manifest, identity)
    return reports, seal, parts


def result_for(manifest, identity, reports, sealed):
    drafts = []
    for report in reports:
        drafts.append({'round': report['round'],
                       'part_writes': [{'call_line': 1, 'result_line': 2, 'part': p}
                                       for p in report['parts']],
                       'checker': {'id': f"check-{report['round']}", 'call_line': 3, 'result_line': 4},
                       'receipt': report,
                       'receipt_sha256': draft.check_summary(manifest, report)['receipt_sha256']})
    return {'registration_sha256': identity, 'audit_sha256': sealed['audit']['sha256'],
            'evidence': {'phase3': {'audit_drafts': drafts,
                        'audit_seal': {'id': 'seal', 'call_line': 5, 'result_line': 6,
                                      'receipt': sealed,
                                      'receipt_sha256': draft.seal_summary(manifest, sealed)['receipt_sha256']}}}}


def test_exact_bytes_grammar_does_not_consult_science_and_seal_does_not_repair(case, monkeypatch):
    from data_sheets_schema import evidence_assertions, source_review
    def forbidden(*args, **kwargs):
        pytest.fail('draft helper consulted scientific validation')
    monkeypatch.setattr(evidence_assertions, 'check_audit', forbidden)
    monkeypatch.setattr(source_review, 'check', forbidden)
    manifest, identity = case
    value = grammar_audit(); value['summary'] = 'α🙂'
    raw = (' \n' + json.dumps(value, ensure_ascii=False, indent=2) + '\r\n').encode()
    split = raw.index('α'.encode())
    parts = write_parts(manifest, pieces=[raw[:split], 'α'.encode(), raw[split + 2:]])
    report = draft.check_round(manifest, identity, 1)
    assert report['grammar']['passed'] is True
    assert draft.draft_path(manifest, 1).read_bytes() == raw
    assert not Path(manifest['job']['audit_path']).exists()
    sealed = draft.seal(manifest, identity)
    assert Path(manifest['job']['audit_path']).read_bytes() == raw
    assert draft.verify_check(manifest, identity, 1, parts) == report
    assert draft.verify_seal(manifest, identity, 1, parts) == sealed
    assert draft.validate_output(manifest) == sealed


def test_failed_first_round_is_preserved_and_second_seals_without_overwrite(case):
    manifest, identity = case
    reports, sealed, parts = accepted(case, second=True)
    first = draft.draft_path(manifest, 1).read_bytes()
    assert first == b'{"incomplete":'
    assert reports[0]['grammar']['passed'] is False
    assert not draft.check_paths(manifest, 1)[2].exists()
    assert draft.verify_seal(manifest, identity, 2, parts) == sealed
    draft.verify_open(manifest)
    result = result_for(manifest, identity, reports, sealed)
    reg = Path(manifest['job']['attempt_dir']).parent.parent / 'registration.json'
    paths = draft.closure_paths(manifest, reg, result)
    for number in (1, 2):
        assert draft.draft_path(manifest, number) in paths
        assert set(draft.check_paths(manifest, number)[:2]) <= paths
        assert {Path(p['path']) for p in reports[number - 1]['parts']} <= paths
    assert set(draft.seal_paths(manifest)[:2]) <= paths
    assert draft.draft_path(manifest, 1).read_bytes() == first


def test_two_grammar_failures_are_terminal_and_no_io_failure_markers(case):
    manifest, identity = case
    for number in (1, 2):
        write_parts(manifest, number, [b'{broken'])
        report = draft.check_round(manifest, identity, number)
        assert report['grammar']['passed'] is False
        assert not draft.check_paths(manifest, number)[2].exists()
        if number == 1:
            draft.verify_open(manifest)
    with pytest.raises(BudgetStop):
        draft.verify_open(manifest)
    with pytest.raises(BudgetStop):
        draft.seal(manifest, identity)
    with pytest.raises(BudgetStop):
        draft.check_round(manifest, identity, 3)
    assert not Path(manifest['job']['audit_path']).exists()


@pytest.mark.parametrize('change', ['null', 'bool-round', 'float-bound', 'extra-key',
                                  'version', 'bool-version', 'kind', 'legacy-output', 'command'])
def test_registration_is_exact_typed_opt_in(case, change):
    manifest, _ = case
    if change == 'null': manifest['audit_drafting'] = None
    elif change == 'bool-round': manifest['audit_drafting']['rounds'][0]['round'] = True
    elif change == 'float-bound': manifest['audit_drafting']['max_rounds'] = 2.0
    elif change == 'extra-key': manifest['audit_drafting']['repair'] = True
    elif change == 'version': manifest['render_version'] = 17
    elif change == 'bool-version': manifest['protocol_version'] = True
    elif change == 'kind': manifest['kind'] = 'd4d_native_finalization'
    elif change == 'legacy-output': manifest['audit_output'] = None
    else: manifest['audit_drafting']['rounds'][0]['check_argv'].append('--source')
    with pytest.raises(REJECTED): draft.configuration(manifest)


def test_absent_mode_and_prelaunch_directories_remain_absent(case):
    manifest, _ = case
    attempt = Path(manifest['job']['attempt_dir'])
    for path in sorted(attempt.rglob('*'), reverse=True):
        path.rmdir() if path.is_dir() else path.unlink()
    attempt.rmdir()
    draft.verify_open(manifest)
    assert not attempt.exists()
    manifest.pop('audit_drafting')
    assert draft.configuration(manifest) is None
    assert draft.instruction(manifest) is None
    assert draft.closure_paths(manifest, attempt.parent.parent / 'registration.json', {}) == set()


@pytest.mark.parametrize('bad', [[], ['000002.txt'], ['000001.txt', '000003.txt'],
                               ['000001.txt', '.hidden'], ['000001.txt', '.gitignore']])
def test_roster_includes_hidden_and_ignored_entries_and_rejects_gaps(case, bad):
    manifest, _ = case
    directory = Path(manifest['audit_drafting']['rounds'][0]['parts'][0]).parent
    for name in bad: (directory / name).write_bytes(b'x')
    with pytest.raises(REJECTED): draft.read_round(manifest, 1)


@pytest.mark.parametrize('raw', [b'', b'\xff', b'\xf0\x9f', b'x' * (draft.MAX_PART_BYTES + 1)])
def test_part_bytes_are_nonempty_bounded_complete_utf8(case, raw):
    manifest, _ = case
    write_parts(manifest, pieces=[raw])
    with pytest.raises(REJECTED): draft.read_round(manifest, 1)


@pytest.mark.parametrize('number', [0, 3, True, 1.0, '1', None])
def test_round_selector_requires_strict_integer(case, number):
    with pytest.raises(BudgetStop): draft.read_round(case[0], number)


@pytest.mark.parametrize('change', ['symlink', 'hardlink', 'directory', 'ancestor-symlink'])
def test_part_aliases_and_nonregular_files_refused(case, tmp_path, change):
    manifest, _ = case
    target = Path(manifest['audit_drafting']['rounds'][0]['parts'][0])
    original = tmp_path / 'original'; original.write_bytes(b'unchanged')
    if change == 'symlink': target.symlink_to(original)
    elif change == 'hardlink': os.link(original, target)
    elif change == 'directory': target.mkdir()
    else:
        moved = tmp_path / 'moved'; target.parent.rename(moved)
        target.parent.symlink_to(moved, target_is_directory=True)
        (moved / target.name).write_bytes(b'unchanged')
    with pytest.raises(REJECTED): draft.read_round(manifest, 1)
    assert original.read_bytes() == b'unchanged'


@pytest.mark.parametrize('early', ['round2-before-check', 'round2-after-pass', 'direct-audit', 'orphan-snapshot'])
def test_early_or_unregistered_outputs_stop_admission(case, early):
    manifest, identity = case
    if early == 'round2-before-check': write_parts(manifest, 2)
    elif early == 'round2-after-pass':
        write_parts(manifest); draft.check_round(manifest, identity, 1); write_parts(manifest, 2)
    elif early == 'direct-audit': Path(manifest['job']['audit_path']).write_bytes(b'{}')
    else: draft.draft_path(manifest, 1).write_bytes(b'{}')
    with pytest.raises(REJECTED): draft.verify_open(manifest)


@pytest.mark.parametrize('change', ['part1', 'draft1', 'receipt1', 'ready-copy', 'third-link',
                                  'new-part1', 'extra-root', 'final', 'identity'])
def test_seal_binds_every_round_not_just_selected_bytes(case, tmp_path, change):
    manifest, identity = case
    reports, sealed, parts = accepted(case, second=True)
    receipt, ready, _ = draft.check_paths(manifest, 1)
    if change == 'part1': Path(reports[0]['parts'][0]['path']).write_bytes(b'changed')
    elif change == 'draft1': draft.draft_path(manifest, 1).write_bytes(b'changed')
    elif change == 'receipt1': receipt.write_text('{}')
    elif change == 'ready-copy':
        raw = ready.read_bytes(); ready.unlink(); ready.write_bytes(raw)
    elif change == 'third-link': os.link(receipt, tmp_path / 'third-link')
    elif change == 'new-part1': Path(manifest['audit_drafting']['rounds'][0]['parts'][1]).write_bytes(b'x')
    elif change == 'extra-root': (draft.draft_path(manifest, 1).parent / '.hidden').write_bytes(b'x')
    elif change == 'final': Path(manifest['job']['audit_path']).write_bytes(b'changed')
    else: identity = 'b' * 64
    with pytest.raises(REJECTED): draft.verify_seal(manifest, identity, 2, parts)


@pytest.mark.parametrize('change', ['drop-round1', 'round-number-bool', 'receipt', 'receipt-hash',
                                  'seal-hash', 'audit-hash', 'registration', 'checker-missing',
                                  'write-line-bool', 'seal-line-reversed'])
def test_descendant_closure_requires_result_bound_history(case, change):
    manifest, identity = case
    reports, sealed, _ = accepted(case, second=True)
    result = result_for(manifest, identity, reports, sealed)
    phase = result['evidence']['phase3']
    if change == 'drop-round1': phase['audit_drafts'].pop(0)
    elif change == 'round-number-bool': phase['audit_drafts'][0]['round'] = True
    elif change == 'receipt': phase['audit_drafts'][0]['receipt'] = {}
    elif change == 'receipt-hash': phase['audit_drafts'][0]['receipt_sha256'] = '0' * 64
    elif change == 'seal-hash': phase['audit_seal']['receipt_sha256'] = '0' * 64
    elif change == 'audit-hash': result['audit_sha256'] = '0' * 64
    elif change == 'checker-missing': phase['audit_drafts'][0]['checker'] = {}
    elif change == 'write-line-bool': phase['audit_drafts'][0]['part_writes'][0]['call_line'] = True
    elif change == 'seal-line-reversed': phase['audit_seal']['result_line'] = 1
    else: result['registration_sha256'] = '0' * 64
    with pytest.raises(REJECTED):
        draft.closure_paths(manifest, Path(manifest['job']['attempt_dir']).parent.parent / 'registration.json', result)


@pytest.mark.parametrize('operation,count', [('check', 7), ('seal', 4)])
def test_no_ready_witness_after_any_fsync_failure_even_if_failure_marker_fails(case, monkeypatch, operation, count):
    # Exercise each preservation boundary using a fresh isolated condition.
    manifest, identity = case
    original_fsync = draft.os.fsync
    for fail_at in range(1, count + 1):
        copy = deepcopy(manifest)
        old = Path(manifest['job']['attempt_dir'])
        condition = old.parent.parent.parent / f'{operation}-{fail_at}'
        attempt = condition / 'attempts' / 'synthetic'
        output = attempt / 'output'
        for n in (1, 2): (output / 'audit-drafts' / f'round-{n}').mkdir(parents=True)
        copy['job'].update(attempt_dir=str(attempt), output_dir=str(output), audit_path=str(output / 'audit.json'))
        copy['audit_drafting'] = draft.specification(copy, condition / 'registration.json')
        write_parts(copy)
        if operation == 'seal': draft.check_round(copy, identity, 1)
        paths = draft.check_paths(copy, 1) if operation == 'check' else draft.seal_paths(copy)
        calls = 0
        def broken_fsync(fd):
            nonlocal calls
            calls += 1
            if calls == fail_at: raise OSError('synthetic fsync failure')
            return original_fsync(fd)
        original_exclusive = draft._exclusive
        def broken_failure(path, raw):
            if Path(path) == paths[2]: raise OSError('synthetic failure-marker failure')
            return original_exclusive(path, raw)
        with monkeypatch.context() as patch:
            patch.setattr(draft.os, 'fsync', broken_fsync)
            patch.setattr(draft, '_exclusive', broken_failure)
            with pytest.raises(OSError):
                draft.check_round(copy, identity, 1) if operation == 'check' else draft.seal(copy, identity)
        assert paths[0].exists() and not paths[1].exists() and not paths[2].exists()
        before = paths[0].read_bytes()
        with pytest.raises(REJECTED):
            draft.check_round(copy, identity, 1) if operation == 'check' else draft.seal(copy, identity)
        assert paths[0].read_bytes() == before and not paths[1].exists()


@pytest.mark.parametrize('operation', ['check', 'seal'])
def test_ready_publication_is_last_and_link_failure_cannot_retry(case, monkeypatch, operation):
    manifest, identity = case
    write_parts(manifest)
    if operation == 'seal': draft.check_round(manifest, identity, 1)
    paths = draft.check_paths(manifest, 1) if operation == 'check' else draft.seal_paths(manifest)
    original_link, original_fsync, original_close = draft.os.link, draft.os.fsync, draft.os.close
    published = False
    def link(*args, **kwargs):
        nonlocal published
        value = original_link(*args, **kwargs); published = True; return value
    def fsync(fd):
        assert not published
        return original_fsync(fd)
    def close(fd):
        assert not published
        return original_close(fd)
    with monkeypatch.context() as patch:
        patch.setattr(draft.os, 'link', link); patch.setattr(draft.os, 'fsync', fsync); patch.setattr(draft.os, 'close', close)
        draft.check_round(manifest, identity, 1) if operation == 'check' else draft.seal(manifest, identity)
    assert published and os.path.samefile(paths[0], paths[1]) and paths[0].stat().st_nlink == 2
    before = paths[0].read_bytes()
    with pytest.raises(REJECTED):
        draft.check_round(manifest, identity, 1) if operation == 'check' else draft.seal(manifest, identity)
    assert before == paths[0].read_bytes() and not paths[2].exists()


@pytest.mark.parametrize('operation', ['check', 'seal'])
def test_failed_last_link_and_lost_witness_cannot_be_repaired(case, monkeypatch, operation):
    manifest, identity = case
    write_parts(manifest)
    if operation == 'seal': draft.check_round(manifest, identity, 1)
    paths = draft.check_paths(manifest, 1) if operation == 'check' else draft.seal_paths(manifest)
    def failure(*args, **kwargs): raise OSError('synthetic link failure')
    with monkeypatch.context() as patch:
        patch.setattr(draft.os, 'link', failure)
        with pytest.raises(OSError):
            draft.check_round(manifest, identity, 1) if operation == 'check' else draft.seal(manifest, identity)
    assert paths[0].exists() and not paths[1].exists()
    before = paths[0].read_bytes()
    with pytest.raises(REJECTED):
        draft.check_round(manifest, identity, 1) if operation == 'check' else draft.seal(manifest, identity)
    assert paths[0].read_bytes() == before and not paths[1].exists()


def test_summary_is_bounded_no_raw_prose_and_receipt_is_not_returned(case):
    manifest, identity = case
    write_parts(manifest, pieces=[b'{"secret":"candidate prose"'])
    report = draft.check_round(manifest, identity, 1)
    summary = draft.check_summary(manifest, report)
    encoded = json.dumps(summary)
    assert len(encoded) < 20000 and 'candidate prose' not in encoded
    assert 'parts' not in summary and 'draft' not in summary
    assert summary['grammar']['passed'] is False


def test_part_limits_and_utf8_boundary_are_exact(case):
    manifest, _ = case
    pieces = [('🙂' * (draft.MAX_PART_BYTES // 4)).encode()] * draft.MAX_PARTS
    parts = write_parts(manifest, pieces=pieces)
    raw, observed = draft.read_round(manifest, 1)
    assert len(raw) == draft.MAX_BYTES and observed == parts
    with pytest.raises(BudgetStop):
        draft.read_round(manifest, 1, allow_empty=1)


def test_cli_grammar_failure_is_successful_execution_with_typed_false_feedback(case, monkeypatch, capsys):
    from audit_controls import registration
    manifest, identity = case
    write_parts(manifest, pieces=[b'{bad'])
    path = Path(manifest['job']['attempt_dir']).parent.parent / 'registration.json'
    monkeypatch.setattr(registration, 'validate_registration', lambda p: manifest)
    draft.main(['--registration', str(path), '--round', '1'])
    printed = json.loads(capsys.readouterr().out)
    assert printed['registration_sha256'] == identity and printed['grammar']['passed'] is False
    assert not draft.check_paths(manifest, 1)[2].exists()


@pytest.mark.parametrize('change', ['duplicate-key', 'float-round', 'bool-passed', 'bool-size', 'extra-key'])
def test_receipt_types_and_duplicate_keys_cannot_alias_original(case, change):
    manifest, identity = case
    parts = write_parts(manifest)
    report = draft.check_round(manifest, identity, 1)
    receipt = draft.check_paths(manifest, 1)[0]
    if change == 'duplicate-key':
        raw = json.dumps(report).replace('"checked": true', '"checked": false, "checked": true')
    else:
        if change == 'float-round': report['round'] = 1.0
        elif change == 'bool-passed': report['grammar']['passed'] = 1
        elif change == 'bool-size': report['parts'][0]['bytes'] = True
        else: report['repair'] = True
        raw = json.dumps(report)
    receipt.write_text(raw)
    with pytest.raises(REJECTED): draft.verify_check(manifest, identity, 1, parts)


@pytest.mark.parametrize('which', ['snapshot', 'final'])
@pytest.mark.parametrize('alias', ['regular', 'symlink', 'hardlink'])
def test_existing_snapshot_and_final_are_never_overwritten(case, tmp_path, which, alias):
    manifest, identity = case
    write_parts(manifest)
    if which == 'final': draft.check_round(manifest, identity, 1)
    target = draft.draft_path(manifest, 1) if which == 'snapshot' else Path(manifest['job']['audit_path'])
    original = tmp_path / 'preserved'; original.write_bytes(b'original bytes')
    if alias == 'regular': target.write_bytes(original.read_bytes())
    elif alias == 'symlink': target.symlink_to(original)
    else: os.link(original, target)
    with pytest.raises(REJECTED):
        draft.check_round(manifest, identity, 1) if which == 'snapshot' else draft.seal(manifest, identity)
    assert target.read_bytes() == original.read_bytes() == b'original bytes'


@pytest.mark.parametrize('operation', ['check', 'seal'])
def test_bytes_changed_during_preservation_never_get_a_witness(case, monkeypatch, operation):
    manifest, identity = case
    write_parts(manifest)
    if operation == 'seal': draft.check_round(manifest, identity, 1)
    original = draft._exclusive
    target = draft.draft_path(manifest, 1) if operation == 'check' else Path(manifest['job']['audit_path'])
    part = Path(manifest['audit_drafting']['rounds'][0]['parts'][0])
    def mutate(path, raw):
        result = original(path, raw)
        if Path(path) == target: part.write_bytes(b'changed during preservation')
        return result
    with monkeypatch.context() as patch:
        patch.setattr(draft, '_exclusive', mutate)
        with pytest.raises(REJECTED):
            draft.check_round(manifest, identity, 1) if operation == 'check' else draft.seal(manifest, identity)
    paths = draft.check_paths(manifest, 1) if operation == 'check' else draft.seal_paths(manifest)
    assert paths[0].exists() and not paths[1].exists()


@pytest.mark.parametrize('operation', ['check', 'seal'])
def test_zero_progress_write_is_terminal_and_all_opened_fds_close(case, monkeypatch, operation):
    manifest, identity = case
    write_parts(manifest)
    if operation == 'seal': draft.check_round(manifest, identity, 1)
    original_open, original_close = draft.os.open, draft.os.close
    opened, closed = [], []
    def track_open(*args, **kwargs):
        fd = original_open(*args, **kwargs); opened.append(fd); return fd
    def track_close(fd):
        closed.append(fd); return original_close(fd)
    with monkeypatch.context() as patch:
        patch.setattr(draft.os, 'open', track_open)
        patch.setattr(draft.os, 'close', track_close)
        patch.setattr(draft.os, 'write', lambda *args: 0)
        with pytest.raises(OSError):
            draft.check_round(manifest, identity, 1) if operation == 'check' else draft.seal(manifest, identity)
    # read_regular closes its own read descriptors through fdopen; check every fd
    # directly rather than assuming our write-side os.close sees all readers.
    for fd in set(opened):
        with pytest.raises(OSError): os.fstat(fd)
    paths = draft.check_paths(manifest, 1) if operation == 'check' else draft.seal_paths(manifest)
    assert not paths[1].exists()


@pytest.mark.parametrize('extra', ['draft-round-3.json', 'draft-round-01.json', 'draft-seal-backup.json'])
def test_extra_control_receipts_fail_closed_including_unselected_round(case, extra):
    manifest, _ = case
    (Path(manifest['job']['attempt_dir']) / extra).write_bytes(b'{}')
    with pytest.raises(BudgetStop): draft.verify_open(manifest)


@pytest.mark.parametrize('change', ['raw-registration', 'in-memory-manifest'])
def test_output_verification_binds_actual_registration_identity(case, change):
    manifest, _ = case
    accepted(case)
    if change == 'raw-registration':
        path = Path(manifest['job']['attempt_dir']).parent.parent / 'registration.json'
        path.write_bytes(path.read_bytes() + b'\n')
    else:
        manifest['unexpected'] = True
    with pytest.raises(REJECTED): draft.validate_output(manifest)
