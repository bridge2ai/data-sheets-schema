"""Offline exact-byte assembly and opt-in native file admission regressions."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shlex
import sys

import pytest

BASE = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(BASE), str(BASE / 'native_controls')]
from audit_controls import output_parts as parts
from budgeted_cborg import BudgetStop
from native_file_policy import FileAccess

IDENTITY = 'a' * 64
REJECTED = (BudgetStop, OSError, ValueError)


@pytest.fixture
def staged(tmp_path):
    condition = tmp_path.resolve() / 'condition'
    attempt = condition / 'attempts' / 'synthetic'
    output = attempt / 'output'
    (output / 'audit-parts').mkdir(parents=True)
    manifest = {
        'kind': 'd4d_native_audit_continuation', 'python': sys.executable,
        'job': {'id': 'synthetic', 'attempt_dir': str(attempt),
                'output_dir': str(output), 'audit_path': str(output / 'audit.json')},
    }
    parts.select(manifest, condition / 'registration.json', True)
    return manifest


def slot(manifest, index=0):
    return Path(manifest['audit_output']['parts'][index])


def write_parts(manifest, pieces):
    descriptions = []
    for index, raw in enumerate(pieces):
        path = slot(manifest, index)
        path.write_bytes(raw)
        descriptions.append({'path': str(path), 'bytes': len(raw),
                             'sha256': hashlib.sha256(raw).hexdigest()})
    return descriptions


def policy(manifest, *, restricted=True):
    lookup = {'repository': str(Path(manifest['job']['attempt_dir']).parent.parent),
              'inputs': [], 'output_directories': [manifest['job']['output_dir']]}
    if restricted:
        lookup['write_paths'] = {name: parts.MAX_PART_BYTES
                                 for name in manifest['audit_output']['parts']}
    return {'readonly_lookups': lookup}


def test_exact_utf8_concat_preserves_json_string_boundaries_and_spelling(staged):
    # No individual part is complete JSON. Whitespace, Unicode, escaped strings
    # and numeric spelling must survive without parsing or reserialization.
    pieces = [b' {"note":"', 'α'.encode(), '🙂'.encode(),
              b'\\u03b2","number":1e+00, "items": [1, 2]}\r\n']
    expected = write_parts(staged, pieces)
    raw = b''.join(pieces)
    assert parts.read_parts(staged) == (raw, expected)
    report = parts.assemble(staged, IDENTITY)
    assert Path(staged['job']['audit_path']).read_bytes() == raw
    assert report['parts'] == expected
    assert report['audit'] == {'path': staged['job']['audit_path'], 'bytes': len(raw),
                               'sha256': hashlib.sha256(raw).hexdigest()}
    assert report['registration_sha256'] == IDENTITY
    assert parts.verify_assembly(staged, IDENTITY, expected) == report


def test_assembler_does_not_parse_or_repair_scientific_output(staged):
    raw = b'{"unfinished":"raw audit text'
    expected = write_parts(staged, [raw])
    parts.assemble(staged, IDENTITY)
    assert Path(staged['job']['audit_path']).read_bytes() == raw
    assert parts.verify_assembly(staged, IDENTITY, expected)['passed'] is True
    with pytest.raises(json.JSONDecodeError):
        json.loads(raw)


@pytest.mark.parametrize('count', [1, parts.MAX_PARTS])
def test_nonempty_prefix_including_all_slots_is_allowed(staged, count):
    expected = write_parts(staged, [b'x'] * count)
    assert parts.read_parts(staged) == (b'x' * count, expected)


def test_part_limit_counts_utf8_bytes_exactly(staged):
    raw = ('🙂' * (parts.MAX_PART_BYTES // 4)).encode()
    expected = write_parts(staged, [raw])
    assert len(raw) == parts.MAX_PART_BYTES
    assert parts.read_parts(staged) == (raw, expected)


@pytest.mark.parametrize('names', [[], ['000002.txt'], ['000001.txt', '000003.txt'],
    ['000001.txt', 'extra.txt'], ['000001.txt', '.hidden'], ['000001.txt', '.gitignore'],
    [f'{index:06d}.txt' for index in range(1, parts.MAX_PARTS + 2)]],
    ids=['empty', 'missing-first', 'gap', 'extra', 'hidden', 'ignored-entry', 'too-many'])
def test_parts_require_exact_contiguous_prefix_including_hidden_entries(staged, names):
    directory = slot(staged).parent
    for name in names:
        (directory / name).write_bytes(b'x')
    with pytest.raises(BudgetStop):
        parts.read_parts(staged)


@pytest.mark.parametrize('raw', [b'', b'\xff', b'\xf0\x9f', b'x' * (parts.MAX_PART_BYTES + 1)],
                         ids=['empty', 'invalid-utf8', 'split-codepoint', 'oversize'])
def test_invalid_part_bytes_fail_assembly_without_accepted_result(staged, raw):
    expected = write_parts(staged, [raw])
    with pytest.raises(REJECTED):
        parts.assemble(staged, IDENTITY)
    receipt, failure = parts.receipt_paths(staged)
    assert receipt.exists() and failure.exists()
    assert not Path(staged['job']['audit_path']).exists()
    assert slot(staged).read_bytes() == raw
    with pytest.raises(REJECTED):
        parts.verify_assembly(staged, IDENTITY, expected)


@pytest.mark.parametrize('alias', ['symlink', 'hardlink', 'ancestor-symlink', 'directory'])
def test_parts_refuse_links_aliases_and_nonregular_files(staged, tmp_path, alias):
    target = slot(staged)
    outside = tmp_path / 'outside.txt'
    outside.write_bytes(b'original')
    if alias == 'symlink':
        target.symlink_to(outside)
    elif alias == 'hardlink':
        os.link(outside, target)
    elif alias == 'ancestor-symlink':
        directory = target.parent
        moved = tmp_path / 'moved-parts'
        directory.rename(moved)
        directory.symlink_to(moved, target_is_directory=True)
        (moved / target.name).write_bytes(b'original')
    else:
        target.mkdir()
    with pytest.raises(REJECTED):
        parts.read_parts(staged)
    assert outside.read_bytes() == b'original'


@pytest.mark.parametrize('existing', ['regular', 'symlink', 'hardlink'])
def test_preexisting_audit_is_never_replaced(staged, tmp_path, existing):
    expected = write_parts(staged, [b'new audit'])
    target = Path(staged['job']['audit_path'])
    original = tmp_path / 'original.txt'
    original.write_bytes(b'preserved audit')
    if existing == 'regular':
        target.write_bytes(original.read_bytes())
    elif existing == 'symlink':
        target.symlink_to(original)
    else:
        os.link(original, target)
    with pytest.raises(REJECTED):
        parts.assemble(staged, IDENTITY)
    assert target.read_bytes() == original.read_bytes() == b'preserved audit'
    with pytest.raises(REJECTED):
        parts.verify_assembly(staged, IDENTITY, expected)


def test_second_assembly_cannot_rewrite_original_success(staged):
    expected = write_parts(staged, [b'first'])
    report = parts.assemble(staged, IDENTITY)
    receipt, failure = parts.receipt_paths(staged)
    original_receipt = receipt.read_bytes()
    with pytest.raises(BudgetStop):
        parts.assemble(staged, IDENTITY)
    assert receipt.read_bytes() == original_receipt
    assert Path(staged['job']['audit_path']).read_bytes() == b'first'
    assert not failure.exists()
    assert parts.verify_assembly(staged, IDENTITY, expected) == report


@pytest.mark.parametrize('change', ['part', 'audit', 'receipt', 'identity', 'expected-parts',
                                  'extra-part', 'failure-marker'])
def test_verification_rejects_mutation_and_stale_receipts(staged, change):
    expected = write_parts(staged, [b'original'])
    report = parts.assemble(staged, IDENTITY)
    receipt, failure = parts.receipt_paths(staged)
    identity = IDENTITY
    if change == 'part':
        slot(staged).write_bytes(b'changed!')
    elif change == 'audit':
        Path(staged['job']['audit_path']).write_bytes(b'changed!')
    elif change == 'receipt':
        report['parts'][0]['sha256'] = '0' * 64
        receipt.write_text(json.dumps(report), encoding='utf-8')
    elif change == 'identity':
        identity = 'b' * 64
    elif change == 'expected-parts':
        expected[0]['sha256'] = '0' * 64
    elif change == 'extra-part':
        slot(staged, 1).write_bytes(b'additional')
    else:
        failure.write_text('{"passed":false}', encoding='utf-8')
    with pytest.raises(REJECTED):
        parts.verify_assembly(staged, identity, expected)


def test_mutation_during_assembly_is_terminal(staged, monkeypatch):
    expected = write_parts(staged, [b'original'])
    original_read = parts.read_parts
    calls = 0

    def mutate_before_second_read(manifest):
        nonlocal calls
        calls += 1
        if calls == 2:
            slot(manifest).write_bytes(b'changed!')
        return original_read(manifest)

    monkeypatch.setattr(parts, 'read_parts', mutate_before_second_read)
    with pytest.raises(BudgetStop):
        parts.assemble(staged, IDENTITY)
    assert parts.receipt_paths(staged)[1].exists()
    with pytest.raises(REJECTED):
        parts.verify_assembly(staged, IDENTITY, expected)


@pytest.mark.parametrize('stage', ['output-write', 'output-fsync', 'directory-fsync',
                                 'receipt-fsync', 'parent-fsync'])
def test_io_failure_cannot_produce_accepted_assembly(staged, monkeypatch, stage):
    expected = write_parts(staged, [b'original bytes'])
    if stage == 'output-write':
        original_fdopen = parts.os.fdopen

        class FailingWriter:
            def __init__(self, stream):
                self.stream = stream

            def __enter__(self):
                return self

            def __exit__(self, *args):
                self.stream.close()

            def write(self, raw):
                self.stream.write(raw[:3])
                raise OSError('injected output write failure')

        def failing_fdopen(descriptor, mode, *args, **kwargs):
            stream = original_fdopen(descriptor, mode, *args, **kwargs)
            return FailingWriter(stream) if mode == 'wb' else stream

        monkeypatch.setattr(parts.os, 'fdopen', failing_fdopen)
    else:
        original_fsync = parts.os.fsync
        fail_at = {'output-fsync': 1, 'directory-fsync': 2,
                   'receipt-fsync': 3, 'parent-fsync': 4}[stage]
        calls = 0

        def failing_fsync(descriptor):
            nonlocal calls
            calls += 1
            if calls == fail_at:
                raise OSError('injected fsync failure')
            return original_fsync(descriptor)

        monkeypatch.setattr(parts.os, 'fsync', failing_fsync)
    with pytest.raises(OSError):
        parts.assemble(staged, IDENTITY)
    assert parts.receipt_paths(staged)[1].exists()
    with pytest.raises(REJECTED):
        parts.verify_assembly(staged, IDENTITY, expected)
    with pytest.raises(REJECTED):
        parts.assemble(staged, IDENTITY)


def test_mode_omission_remains_unselected(staged):
    manifest = deepcopy(staged)
    manifest.pop('audit_output')
    registration = Path(manifest['job']['attempt_dir']).parent.parent / 'registration.json'
    parts.select(manifest, registration, False)
    assert 'audit_output' not in manifest
    assert parts.configuration(manifest) is None
    with pytest.raises(BudgetStop):
        parts.select(manifest, registration, 1)


@pytest.mark.parametrize('change', ['kind', 'parts', 'bound', 'bool-bound', 'command'])
def test_staged_registration_rejects_changed_protocol_or_scope(staged, change):
    if change == 'kind':
        staged['kind'] = 'd4d_native_finalization'
    elif change == 'parts':
        staged['audit_output']['parts'][0] = staged['job']['audit_path']
    elif change in ('bound', 'bool-bound'):
        staged['audit_output']['max_part_bytes'] = True if change == 'bool-bound' else 65536
    else:
        staged['audit_output']['assemble_argv'].append('--anything')
    with pytest.raises(BudgetStop):
        parts.configuration(staged)


@pytest.mark.parametrize('target', ['audit', 'unlisted', 'controller-receipt'])
def test_file_policy_denies_nonpart_writes(staged, target):
    path = {'audit': staged['job']['audit_path'],
            'unlisted': str(slot(staged).parent / 'unlisted.txt'),
            'controller-receipt': str(parts.receipt_paths(staged)[0])}[target]
    assert FileAccess(policy(staged)).classify('Write', {'file_path': path, 'content': 'x'})[0] == 'not_prescribed'


@pytest.mark.parametrize('content', ['', 'x' * (parts.MAX_PART_BYTES + 1),
    '🙂' * (parts.MAX_PART_BYTES // 4) + 'x', '\ud800', 123],
    ids=['empty', 'oversize-ascii', 'oversize-utf8', 'invalid-utf8', 'nontext'])
def test_file_policy_denies_invalid_part_content(staged, content):
    payload = {'file_path': str(slot(staged)), 'content': content}
    assert FileAccess(policy(staged)).classify('Write', payload)[0] == 'not_prescribed'


def test_file_policy_accepts_exact_part_byte_limit(staged):
    payload = {'file_path': str(slot(staged)), 'content': '🙂' * (parts.MAX_PART_BYTES // 4)}
    assert FileAccess(policy(staged)).classify('Write', payload)[0] == 'prescribed'


def test_file_policy_omission_preserves_legacy_output_writes(staged):
    files = FileAccess(policy(staged, restricted=False))
    for name in (staged['job']['audit_path'], str(slot(staged).parent / 'unlisted.txt')):
        assert files.classify('Write', {'file_path': name, 'content': 'legacy'})[0] == 'prescribed'


@pytest.mark.parametrize('change', ['duplicate-checked', 'duplicate-part-size', 'checked-number',
    'passed-number', 'schema-float', 'part-size-float', 'part-size-bool',
    'audit-size-float', 'audit-size-bool'])
def test_receipt_parser_and_comparison_preserve_json_types(staged, change):
    expected = write_parts(staged, [b'x'])
    report = parts.assemble(staged, IDENTITY)
    receipt, _ = parts.receipt_paths(staged)
    if change == 'duplicate-checked':
        encoded = json.dumps(report).replace('"checked": true', '"checked": false, "checked": true')
    elif change == 'duplicate-part-size':
        encoded = json.dumps(report).replace('"bytes": 1', '"bytes": 2, "bytes": 1', 1)
    else:
        if change == 'checked-number':
            report['checked'] = 1
        elif change == 'passed-number':
            report['passed'] = 1
        elif change == 'schema-float':
            report['schema_version'] = 1.0
        else:
            descriptor = report['parts'][0] if change.startswith('part-') else report['audit']
            descriptor['bytes'] = True if change.endswith('bool') else 1.0
        encoded = json.dumps(report)
    receipt.write_text(encoded, encoding='utf-8')
    with pytest.raises(REJECTED):
        parts.verify_assembly(staged, IDENTITY, expected)


@pytest.mark.parametrize('size', [True, 1.0], ids=['bool', 'float'])
def test_observed_part_descriptors_cannot_use_numeric_type_aliases(staged, size):
    expected = write_parts(staged, [b'x'])
    parts.assemble(staged, IDENTITY)
    expected[0]['bytes'] = size
    with pytest.raises(BudgetStop):
        parts.verify_assembly(staged, IDENTITY, expected)


def test_phase4_cannot_activate_audit_staging(staged):
    phase4 = deepcopy(staged)
    phase4['kind'] = 'd4d_native_finalization'
    phase4['job'].pop('audit_path')
    with pytest.raises(BudgetStop, match='staged audit output registration'):
        parts.configuration(phase4)
    phase4.pop('audit_output')
    assert parts.configuration(phase4) is None
    assert parts.instruction(phase4) is None


def save_registration(manifest):
    path = Path(manifest['job']['attempt_dir']).parent.parent / 'registration.json'
    raw = (json.dumps(manifest, indent=2) + '\n').encode()
    path.write_bytes(raw)
    return path, hashlib.sha256(raw).hexdigest()


def scientific_manifest(staged, tmp_path):
    from audit_controls.test_contract import audit_fixture

    fixture_dir = tmp_path / 'scientific'
    fixture_dir.mkdir()
    manifest, audit = audit_fixture(fixture_dir)
    manifest.update(kind=staged['kind'], python=staged['python'], job=deepcopy(staged['job']))
    return manifest, (json.dumps(audit) + '\n').encode()


@pytest.mark.parametrize('completed_parts', [False, True], ids=['no-parts', 'parts-without-receipt'])
def test_pure_audit_check_refuses_valid_direct_output_without_assembly(staged, tmp_path, completed_parts):
    from audit_controls import contract

    manifest, raw = scientific_manifest(staged, tmp_path)
    Path(manifest['job']['audit_path']).write_bytes(raw)
    assert contract.validate_audit(manifest)['passed'] is True
    manifest['audit_output'] = deepcopy(staged['audit_output'])
    if completed_parts:
        write_parts(manifest, [raw])
    save_registration(manifest)
    before = {path: path.read_bytes() for path in tmp_path.rglob('*') if path.is_file()}
    report = contract.validate_audit(manifest)
    assert report['passed'] is False and report['checked'] is False
    assert report['errors']
    assert before == {path: path.read_bytes() for path in tmp_path.rglob('*') if path.is_file()}
    assert not parts.receipt_paths(manifest)[0].exists()


def test_pure_audit_check_accepts_exact_assembly_with_real_scientific_fixture(staged, tmp_path):
    from audit_controls import contract

    manifest, raw = scientific_manifest(staged, tmp_path)
    manifest['audit_output'] = deepcopy(staged['audit_output'])
    write_parts(manifest, [raw])
    _, identity = save_registration(manifest)
    assembly = parts.assemble(manifest, identity)
    before = {path: path.read_bytes() for path in tmp_path.rglob('*') if path.is_file()}
    assert parts.validate_output(manifest) == assembly
    report = contract.validate_audit(manifest)
    assert report['passed'] is True and report['checked'] is True
    assert report['audit_sha256'] == hashlib.sha256(raw).hexdigest()
    assert before == {path: path.read_bytes() for path in tmp_path.rglob('*') if path.is_file()}


@pytest.mark.parametrize('change', ['registration-bytes', 'manifest'])
def test_pure_output_check_binds_exact_registration_bytes_and_manifest(staged, change):
    write_parts(staged, [b'x'])
    registration, identity = save_registration(staged)
    parts.assemble(staged, identity)
    assert parts.validate_output(staged)['registration_sha256'] == identity
    if change == 'registration-bytes':
        registration.write_bytes(registration.read_bytes() + b'\n')
    else:
        staged['unexpected'] = 'changed in-memory manifest'
    with pytest.raises(BudgetStop):
        parts.validate_output(staged)


def test_persistent_recovery_repeats_current_staged_paths_and_commands(staged):
    from audit_controls.prepare import render_system
    import native_context_control as recovery

    condition = Path(staged['job']['attempt_dir']).parent.parent
    instruction = condition / 'instruction.md'
    instruction.write_text(parts.instruction(staged), encoding='utf-8')
    source = condition / 'source.txt'
    source.write_text('Synthetic reference data.', encoding='utf-8')
    staged['inputs'] = {'bundle': str(source)}
    staged['job'].update(instruction=str(instruction), readable_inputs=[str(instruction), str(source)],
        validator_argv=[sys.executable, '-m', 'audit_controls.contract',
                        '--registration', str(condition / 'registration.json')])
    recovery.prepare(staged, condition, True)
    rendered = render_system(staged)
    persistent = rendered.split('Persistent registered context recovery\n', 1)[1]
    assert 'Current stage: Phase 3 audit only.' in persistent
    assert str(slot(staged).parent) in persistent
    assert '000001.txt through 000064.txt' in persistent
    assert '1 to 32768 UTF-8 bytes' in persistent
    assert shlex.join(staged['audit_output']['assemble_argv']) in persistent
    assert shlex.join(staged['job']['validator_argv']) in persistent
    assert 'Do not rewrite a completed part' in persistent
    assert 'write audit.json directly' in persistent
    assert str(staged['context_recovery']['index']['path']) in persistent
    assert 'parent_instruction is historical reference only' in persistent
    assert 'Write only the new audit at ' not in rendered
    assert 'write the one registered audit JSON' not in rendered


@pytest.mark.parametrize('count', [1, parts.MAX_PARTS])
def test_assembly_summary_is_bounded_and_binds_full_retained_receipt(staged, count):
    expected = write_parts(staged, [b'x'] * count)
    report = parts.assemble(staged, IDENTITY)
    receipt, _ = parts.receipt_paths(staged)
    before = receipt.read_bytes()
    summary = parts.summary(staged, report)
    assert summary == {
        'schema_version': 1, 'operation': 'concatenate_utf8_parts', 'passed': True,
        'job_id': staged['job']['id'], 'registration_sha256': IDENTITY,
        'part_count': count, 'audit_sha256': hashlib.sha256(b'x' * count).hexdigest(),
        'audit_bytes': count, 'receipt_sha256': hashlib.sha256(before).hexdigest(),
    }
    encoded = json.dumps(summary).encode()
    assert len(encoded) < 1024
    assert staged['job']['audit_path'].encode() not in encoded
    assert str(slot(staged)).encode() not in encoded
    assert receipt.read_bytes() == before
    assert json.loads(before)['parts'] == expected


def test_assembly_cli_stdout_contains_summary_and_keeps_full_receipt(staged, monkeypatch, capsys):
    from audit_controls import registration

    expected = write_parts(staged, [b'first', b'second'])
    path, identity = save_registration(staged)
    monkeypatch.setattr(registration, 'validate_registration', lambda selected: staged)
    monkeypatch.setattr(sys, 'argv', ['output_parts', '--registration', str(path)])
    parts.main()
    printed = json.loads(capsys.readouterr().out)
    report = json.loads(parts.receipt_paths(staged)[0].read_bytes())
    assert printed == parts.summary(staged, report)
    assert printed['registration_sha256'] == identity
    assert 'parts' not in printed and 'audit' not in printed
    assert report['parts'] == expected
    assert Path(staged['job']['audit_path']).read_bytes() == b'firstsecond'


@pytest.mark.parametrize('stage', ['output-fsync', 'directory-fsync', 'receipt-fsync',
                                 'parent-fsync', 'ready-link'])
def test_preservation_failure_without_failure_marker_still_cannot_pass_or_retry(staged, monkeypatch, stage):
    expected = write_parts(staged, [b'original bytes'])
    receipt, failure = parts.receipt_paths(staged)
    ready = parts.ready_path(staged)
    original_open = Path.open
    failure_writes = 0

    def cannot_record_failure(path, *args, **kwargs):
        nonlocal failure_writes
        if path == failure:
            failure_writes += 1
            raise OSError('injected failure marker creation failure')
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, 'open', cannot_record_failure)
    if stage == 'ready-link':
        def cannot_publish(source, destination, **kwargs):
            assert Path(source) == receipt and Path(destination) == ready
            assert not os.path.lexists(ready)
            # A failed link syscall creates no witness. Never create then raise.
            raise OSError('injected readiness publication failure')

        monkeypatch.setattr(parts.os, 'link', cannot_publish)
    else:
        original_fsync = parts.os.fsync
        fail_at = {'output-fsync': 1, 'directory-fsync': 2,
                   'receipt-fsync': 3, 'parent-fsync': 4}[stage]
        calls = 0

        def cannot_preserve(descriptor):
            nonlocal calls
            calls += 1
            if calls == fail_at:
                raise OSError('injected preservation failure')
            return original_fsync(descriptor)

        monkeypatch.setattr(parts.os, 'fsync', cannot_preserve)
    with pytest.raises(OSError):
        parts.assemble(staged, IDENTITY)
    assert failure_writes == 1
    assert receipt.is_file() and not os.path.lexists(failure) and not os.path.lexists(ready)
    original_receipt = receipt.read_bytes()
    with pytest.raises(BudgetStop, match='preservation witness'):
        parts.verify_assembly(staged, IDENTITY, expected)
    with pytest.raises(FileExistsError):
        parts.assemble(staged, IDENTITY)
    assert failure_writes == 2
    assert receipt.read_bytes() == original_receipt
    assert not os.path.lexists(failure) and not os.path.lexists(ready)
    with pytest.raises(BudgetStop, match='preservation witness'):
        parts.verify_assembly(staged, IDENTITY, expected)


def test_success_witness_is_exact_two_link_receipt_inode(staged):
    expected = write_parts(staged, [b'original'])
    report = parts.assemble(staged, IDENTITY)
    receipt, failure = parts.receipt_paths(staged)
    ready = parts.ready_path(staged)
    assert not receipt.is_symlink() and not ready.is_symlink()
    assert os.path.samefile(receipt, ready)
    assert receipt.stat().st_nlink == ready.stat().st_nlink == 2
    assert receipt.read_bytes() == ready.read_bytes()
    assert not failure.exists()
    assert parts.verify_assembly(staged, IDENTITY, expected) == report


@pytest.mark.parametrize('damage', ['ready-copy', 'receipt-copy', 'extra-hardlink',
                                  'ready-symlink', 'ready-directory'])
def test_witness_requires_exact_inode_and_link_count(staged, tmp_path, damage):
    expected = write_parts(staged, [b'original'])
    parts.assemble(staged, IDENTITY)
    receipt, _ = parts.receipt_paths(staged)
    ready = parts.ready_path(staged)
    if damage == 'extra-hardlink':
        os.link(receipt, tmp_path / 'third-receipt-link.json')
    elif damage == 'receipt-copy':
        raw = receipt.read_bytes()
        receipt.unlink()
        receipt.write_bytes(raw)
    else:
        raw = ready.read_bytes()
        ready.unlink()
        if damage == 'ready-copy':
            ready.write_bytes(raw)
        elif damage == 'ready-symlink':
            ready.symlink_to(receipt)
        else:
            ready.mkdir()
    with pytest.raises(REJECTED):
        parts.verify_assembly(staged, IDENTITY, expected)


def test_lost_witness_is_not_repaired_by_verification_or_reentry(staged):
    expected = write_parts(staged, [b'preserved'])
    parts.assemble(staged, IDENTITY)
    receipt, _ = parts.receipt_paths(staged)
    ready = parts.ready_path(staged)
    before = receipt.read_bytes()
    ready.unlink()
    assert receipt.stat().st_nlink == 1
    with pytest.raises(BudgetStop, match='preservation witness'):
        parts.verify_assembly(staged, IDENTITY, expected)
    assert not os.path.lexists(ready) and receipt.read_bytes() == before
    with pytest.raises(FileExistsError):
        parts.assemble(staged, IDENTITY)
    assert not os.path.lexists(ready) and receipt.read_bytes() == before
    assert Path(staged['job']['audit_path']).read_bytes() == b'preserved'
    with pytest.raises(BudgetStop):
        parts.verify_assembly(staged, IDENTITY, expected)


def test_readiness_publication_has_no_later_fsync_or_close(staged, monkeypatch):
    write_parts(staged, [b'preserved'])
    original_fsync, original_close, original_link = parts.os.fsync, parts.os.close, parts.os.link
    operations = []
    published = False

    def tracked_fsync(descriptor):
        assert not published, 'no fsync may follow readiness publication'
        operations.append('fsync')
        return original_fsync(descriptor)

    def tracked_close(descriptor):
        assert not published, 'no descriptor cleanup may follow readiness publication'
        operations.append('close')
        return original_close(descriptor)

    def publish(source, destination, **kwargs):
        nonlocal published
        assert operations.count('fsync') == 4
        assert operations[-1] == 'close'
        result = original_link(source, destination, **kwargs)
        published = True
        operations.append('publish')
        return result

    with monkeypatch.context() as patch:
        patch.setattr(parts.os, 'fsync', tracked_fsync)
        patch.setattr(parts.os, 'close', tracked_close)
        patch.setattr(parts.os, 'link', publish)
        assert parts.assemble(staged, IDENTITY)['passed'] is True
    assert published and operations[-1] == 'publish'
