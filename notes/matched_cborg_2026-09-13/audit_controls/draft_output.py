"""Two immutable native audit drafts: grammar only, then exact-byte sealing."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import stat

from budgeted_cborg import BudgetStop
from .output_parts import canonical, describe, read_regular, same_json

PROTOCOL = 'bounded_draft_grammar_v1'
MAX_ROUNDS = 2
MAX_PARTS = 64
MAX_PART_BYTES = 32768
MAX_BYTES = MAX_PARTS * MAX_PART_BYTES
MAX_GRAMMAR_BYTES = 16384
MAX_RECEIPT_BYTES = 131072


def specification(manifest, registration_path):
    root = Path(manifest['job']['output_dir']) / 'audit-drafts'
    command = [manifest['python'], '-m', 'audit_controls.draft_output',
               '--registration', str(registration_path)]
    return {'protocol': PROTOCOL, 'max_rounds': MAX_ROUNDS,
            'max_parts': MAX_PARTS, 'max_part_bytes': MAX_PART_BYTES,
            'rounds': [{'round': number,
                        'parts': [str(root / f'round-{number}' / f'{i:06d}.txt')
                                  for i in range(1, MAX_PARTS + 1)],
                        'check_argv': [*command, '--round', str(number)]}
                       for number in range(1, MAX_ROUNDS + 1)],
            'seal_argv': [*command, '--seal']}


def configuration(manifest, registration_path=None):
    if 'audit_drafting' not in manifest:
        return None
    if (manifest.get('kind') != 'd4d_native_audit_continuation' or
            type(manifest.get('protocol_version')) is not int or
            type(manifest.get('render_version')) is not int or
            (manifest['protocol_version'], manifest['render_version']) != (6, 18) or
            'audit_output' in manifest):
        raise BudgetStop('bounded audit drafting requires only the audit 6/18 protocol')
    job = manifest['job']
    path = canonical(registration_path or Path(job['attempt_dir']).parent.parent / 'registration.json')
    block = manifest['audit_drafting']
    if type(block) is not dict or not same_json(block, specification(manifest, path)):
        raise BudgetStop('unsupported or changed bounded audit drafting registration')
    attempt, output = canonical(job['attempt_dir']), canonical(job['output_dir'])
    if (attempt != path.parent / 'attempts' / job['id'] or output != attempt / 'output' or
            canonical(job['audit_path']) != output / 'audit.json'):
        raise BudgetStop('audit draft destinations differ from the registered layout')
    for entry in block['rounds']:
        for value in entry['parts']:
            canonical(value)
    return block


def _number(number):
    if type(number) is not int or not 1 <= number <= MAX_ROUNDS:
        raise BudgetStop('audit draft round must be the integer 1 or 2')
    return number


def draft_path(manifest, number):
    _number(number)
    return canonical(Path(manifest['job']['output_dir']) / 'audit-drafts' / f'round-{number}.json')


def check_paths(manifest, number):
    _number(number)
    attempt = canonical(manifest['job']['attempt_dir'])
    return tuple(attempt / name for name in
                 (f'draft-round-{number}.json', f'draft-round-{number}_ready.json',
                  f'draft-round-{number}_failure.json'))


def seal_paths(manifest):
    attempt = canonical(manifest['job']['attempt_dir'])
    return tuple(attempt / name for name in
                 ('draft-seal.json', 'draft-seal_ready.json', 'draft-seal_failure.json'))


def instruction(manifest):
    block = configuration(manifest)
    if block is None:
        return None
    lines = [
        'Author at most two immutable grammar drafts of the complete audit. This is grammar-only '
        'feedback, not scientific/source validation or permission to alter inputs. For each round, '
        'use native Write on a nonempty consecutive prefix of its registered parts, starting at '
        '000001.txt. Each part contains 1 to 32768 UTF-8 bytes. Split at any UTF-8 character '
        'boundary, without inserting separators or repeating content. Wait for each Write result. '
        'Registered input Reads are allowed between completed Writes. Never rewrite a completed '
        'part, write another round early, or write audit.json/round snapshots/receipts yourself.']
    for entry in block['rounds']:
        lines += [f"Round {entry['round']}: {Path(entry['parts'][0]).parent}/000001.txt through 000064.txt",
                  'Invoke its exact foreground grammar command once after completing the parts:',
                  shlex.join(entry['check_argv'])]
    lines += [
        'Round 2 is allowed only after the completed round-1 grammar result has passed=false. '
        'A helper execution/I/O error ends the attempt; it is not grammar feedback and permits '
        'no retry. Round-2 grammar failure also ends the attempt. After a grammar pass, no more '
        'parts or draft corrections are allowed. Seal only the current, last, passing round with:',
        shlex.join(block['seal_argv']),
        'Sealing preserves the exact selected bytes as audit.json, without parsing, normalizing '
        'or repairing them. After sealing starts, wait for its successful result, then invoke '
        'only the existing single terminal source validator. No correction or extra grammar '
        'check is allowed after sealing or terminal source validation.']
    return '\n'.join(lines) + '\n'


def _strict(raw):
    from .contract import strict_json
    return strict_json(raw)


def _encoded(value):
    return (json.dumps(value, sort_keys=True, allow_nan=False) + '\n').encode('utf-8')


def _registration_identity(manifest):
    path = canonical(Path(manifest['job']['attempt_dir']).parent.parent / 'registration.json')
    raw = read_regular(path, 16777216)
    if not same_json(_strict(raw), manifest):
        raise BudgetStop('audit draft manifest differs from registered bytes')
    return hashlib.sha256(raw).hexdigest()


def _directory(path, *, optional=False):
    path = canonical(path)
    if optional and not os.path.lexists(path):
        return []
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode):
        raise BudgetStop('audit draft container must be a nonsymlink directory')
    return list(path.iterdir())  # Includes every hidden and ignored entry.


def _roster(manifest):
    root = canonical(Path(manifest['job']['output_dir']) / 'audit-drafts')
    allowed = {f'round-{i}{suffix}' for i in range(1, MAX_ROUNDS + 1)
               for suffix in ('', '.json')}
    if any(p.name not in allowed for p in _directory(root, optional=True)):
        raise BudgetStop('audit draft container has extra entries')
    controls = {p.name for number in (1, 2) for p in check_paths(manifest, number)}
    controls.update(p.name for p in seal_paths(manifest))
    for entry in _directory(manifest['job']['attempt_dir'], optional=True):
        if entry.name.startswith(('draft-round-', 'draft-seal')) and entry.name not in controls:
            raise BudgetStop('audit draft receipt namespace has extra entries')


def read_round(manifest, number, allow_empty=False):
    block = configuration(manifest)
    if block is None:
        raise BudgetStop('bounded audit drafting is not selected')
    _number(number)
    if type(allow_empty) is not bool:
        raise BudgetStop('allow_empty must be boolean')
    _roster(manifest)
    slots = block['rounds'][number - 1]['parts']
    names = sorted(p.name for p in _directory(Path(slots[0]).parent, optional=allow_empty))
    if ((not names and not allow_empty) or len(names) > MAX_PARTS or
            names != [Path(p).name for p in slots[:len(names)]]):
        raise BudgetStop('audit draft parts require a nonempty contiguous prefix without extras')
    pieces, parts = [], []
    for path in slots[:len(names)]:
        raw = read_regular(path, MAX_PART_BYTES)
        if not raw:
            raise BudgetStop('audit draft parts must be nonempty')
        raw.decode('utf-8', errors='strict')
        pieces.append(raw)
        parts.append(describe(path, raw))
    return b''.join(pieces), parts


def _grammar(raw):
    from data_sheets_schema.audit_grammar import check
    report = check(raw)
    if (type(report) is not dict or type(report.get('passed')) is not bool or
            len(_encoded(report)) > MAX_GRAMMAR_BYTES):
        raise BudgetStop('grammar helper returned an invalid or unbounded report')
    return report


def _check_receipt(manifest, identity, number, raw, parts):
    return {'schema_version': 1, 'operation': 'audit_draft_grammar', 'checked': True,
            'job_id': manifest['job']['id'], 'registration_sha256': identity,
            'round': number, 'parts': parts, 'draft': describe(draft_path(manifest, number), raw),
            'grammar': _grammar(raw)}


def _witness(paths):
    receipt, ready, failure = map(canonical, paths)
    if os.path.lexists(failure):
        raise BudgetStop('audit draft helper previously failed; no retry')
    # Both reads enforce exact two-link regular inodes; a copied witness is invalid.
    raw = read_regular(receipt, MAX_RECEIPT_BYTES, links=2)
    witness = read_regular(ready, MAX_RECEIPT_BYTES, links=2)
    if not os.path.samefile(receipt, ready) or raw != witness:
        raise BudgetStop('audit draft receipt lacks its exact preservation witness')
    return _strict(raw)


def verify_check(manifest, identity, number, expected_parts):
    _number(number)
    report = _witness(check_paths(manifest, number))
    raw, parts = read_round(manifest, number)
    if not same_json(parts, expected_parts):
        raise BudgetStop('audit draft parts differ from completed native Writes')
    if read_regular(draft_path(manifest, number), MAX_BYTES) != raw:
        raise BudgetStop('preserved audit draft differs from its exact part bytes')
    if not same_json(report, _check_receipt(manifest, identity, number, raw, parts)):
        raise BudgetStop('audit grammar receipt differs from bytes, grammar or registration')
    return report


def check_summary(manifest, report):
    receipt, _, _ = check_paths(manifest, report['round'])
    return {'schema_version': 1, 'operation': 'audit_draft_grammar',
            'job_id': report['job_id'], 'registration_sha256': report['registration_sha256'],
            'round': report['round'], 'part_count': len(report['parts']),
            'draft_sha256': report['draft']['sha256'], 'draft_bytes': report['draft']['bytes'],
            'grammar': report['grammar'],
            'receipt_sha256': hashlib.sha256(read_regular(receipt, MAX_RECEIPT_BYTES, links=2)).hexdigest()}


def _rounds(manifest, identity):
    """Verify every completed round and all open rosters, without consuming anything."""
    checks, parts = [], []
    for number in range(1, MAX_ROUNDS + 1):
        _, current = read_round(manifest, number, allow_empty=True)
        artifacts = check_paths(manifest, number)
        started = any(os.path.lexists(p) for p in (*artifacts, draft_path(manifest, number)))
        if number > 1 and (current or started):
            if len(checks) != number - 1 or checks[-1]['grammar']['passed']:
                raise BudgetStop('another audit draft requires the previous grammar failure')
        if started:
            checks.append(verify_check(manifest, identity, number, current))
        parts.append(current)
    return checks, parts


def _seal_receipt(manifest, identity, number, raw, parts, checks):
    return {'schema_version': 1, 'operation': 'seal_audit_draft', 'passed': True,
            'job_id': manifest['job']['id'], 'registration_sha256': identity,
            'round': number, 'parts': parts, 'audit': describe(manifest['job']['audit_path'], raw),
            'checks': [{'round': c['round'], 'passed': c['grammar']['passed'],
                        'receipt_sha256': check_summary(manifest, c)['receipt_sha256']}
                       for c in checks]}


def verify_seal(manifest, identity, expected_round, expected_parts):
    _number(expected_round)
    report = _witness(seal_paths(manifest))
    checks, rosters = _rounds(manifest, identity)
    if (len(checks) != expected_round or not checks[-1]['grammar']['passed'] or
            any(rosters[expected_round:])):
        raise BudgetStop('sealed audit must be the last grammar-passing round')
    raw, parts = read_round(manifest, expected_round)
    if not same_json(parts, expected_parts):
        raise BudgetStop('sealed audit parts differ from completed native Writes')
    if read_regular(manifest['job']['audit_path'], MAX_BYTES) != raw:
        raise BudgetStop('sealed audit differs from exact chosen draft bytes')
    if not same_json(report, _seal_receipt(manifest, identity, expected_round, raw, parts, checks)):
        raise BudgetStop('audit seal receipt differs from preserved round history')
    return report


def seal_summary(manifest, report):
    receipt, _, _ = seal_paths(manifest)
    return {'schema_version': 1, 'operation': 'seal_audit_draft', 'passed': True,
            'job_id': report['job_id'], 'registration_sha256': report['registration_sha256'],
            'round': report['round'], 'part_count': len(report['parts']),
            'audit_sha256': report['audit']['sha256'], 'audit_bytes': report['audit']['bytes'],
            'receipt_sha256': hashlib.sha256(read_regular(receipt, MAX_RECEIPT_BYTES, links=2)).hexdigest()}


def verify_open(manifest):
    if configuration(manifest) is None:
        return
    identity = _registration_identity(manifest)
    checks, rosters = _rounds(manifest, identity)
    if checks and checks[-1]['round'] == MAX_ROUNDS and not checks[-1]['grammar']['passed']:
        raise BudgetStop('last permitted audit draft failed grammar; attempt is terminal')
    if any(os.path.lexists(p) for p in (*seal_paths(manifest), Path(manifest['job']['audit_path']))):
        if not checks:
            raise BudgetStop('audit seal exists before a completed grammar check')
        verify_seal(manifest, identity, checks[-1]['round'], rosters[len(checks) - 1])


def _sync(path, *, directory=False):
    path = canonical(path)
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
    if directory:
        flags |= os.O_DIRECTORY
    descriptor = os.open(path, flags)
    try:
        info = os.fstat(descriptor)
        if (not directory and (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1)):
            raise BudgetStop('audit draft durability requires regular single-link files')
        os.fsync(descriptor)
        current = path.lstat()
        if (current.st_dev, current.st_ino) != (info.st_dev, info.st_ino):
            raise BudgetStop('audit draft path changed during preservation')
    finally:
        os.close(descriptor)


def _write_preserved(descriptor, path, raw):
    offset = 0
    while offset < len(raw):
        written = os.write(descriptor, raw[offset:])
        if written <= 0:
            raise OSError('audit draft write made no progress')
        offset += written
    os.fsync(descriptor)
    info, current = os.fstat(descriptor), canonical(path).lstat()
    if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size != len(raw) or
            (current.st_dev, current.st_ino) != (info.st_dev, info.st_ino)):
        raise BudgetStop('audit draft output changed while being preserved')


def _exclusive(path, raw):
    path = canonical(path)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        _write_preserved(fd, path, raw)
    finally:
        os.close(fd)


def _preserve(paths, produce):
    receipt, ready, failure = map(canonical, paths)
    if any(os.path.lexists(p) for p in paths):
        raise BudgetStop('audit draft operation already started; no repetition')
    # Reserve before producing anything. A missing witness cannot be repaired.
    descriptor = os.open(receipt, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        try:
            report = produce()
            raw = _encoded(report)
            if len(raw) > MAX_RECEIPT_BYTES:
                raise BudgetStop('audit draft receipt exceeds its bound')
            _write_preserved(descriptor, receipt, raw)
        finally:
            os.close(descriptor)
        _sync(receipt.parent, directory=True)
        # Last fallible preservation operation; nothing to fsync/close afterwards.
        # If this link is lost in a reboot, verification fails closed.
        os.link(receipt, ready, follow_symlinks=False)
        return report
    except BaseException:
        try:
            _exclusive(failure, b'{"passed":false}\n')
        except (OSError, BudgetStop):
            pass
        raise


def check_round(manifest, identity, number):
    configuration(manifest); _number(number)
    checks, rosters = _rounds(manifest, identity)
    if (len(checks) != number - 1 or (checks and checks[-1]['grammar']['passed']) or
            any(rosters[number:]) or
            any(os.path.lexists(p) for p in (*seal_paths(manifest), Path(manifest['job']['audit_path'])))):
        raise BudgetStop('audit grammar check is out of sequence')

    def produce():
        raw, parts = read_round(manifest, number)
        report = _check_receipt(manifest, identity, number, raw, parts)
        _exclusive(draft_path(manifest, number), raw)
        for part in parts:
            _sync(part['path'])
        for directory in (Path(parts[0]['path']).parent, draft_path(manifest, number).parent,
                          Path(manifest['job']['output_dir'])):
            _sync(directory, directory=True)
        if (read_round(manifest, number) != (raw, parts) or
                read_regular(draft_path(manifest, number), MAX_BYTES) != raw):
            raise BudgetStop('audit draft changed during preservation')
        return report

    return _preserve(check_paths(manifest, number), produce)


def seal(manifest, identity):
    configuration(manifest)
    checks, rosters = _rounds(manifest, identity)
    if not checks or not checks[-1]['grammar']['passed'] or any(rosters[len(checks):]):
        raise BudgetStop('only the current last grammar-passing audit draft can be sealed')
    number = checks[-1]['round']

    def produce():
        raw, parts = read_round(manifest, number)
        _exclusive(manifest['job']['audit_path'], raw)
        _sync(Path(manifest['job']['output_dir']), directory=True)
        again, current = _rounds(manifest, identity)
        if (not same_json(again, checks) or not same_json(current, rosters) or
                read_regular(manifest['job']['audit_path'], MAX_BYTES) != raw):
            raise BudgetStop('audit draft history changed during sealing')
        return _seal_receipt(manifest, identity, number, raw, parts, checks)

    return _preserve(seal_paths(manifest), produce)


def validate_output(manifest):
    if configuration(manifest) is None:
        raise BudgetStop('bounded audit drafting is not selected')
    identity = _registration_identity(manifest)
    receipt = _witness(seal_paths(manifest))
    return verify_seal(manifest, identity, receipt['round'], receipt['parts'])


def closure_paths(manifest, registration_path, result):
    if configuration(manifest, registration_path) is None:
        return set()
    identity = _registration_identity(manifest)
    phase = result.get('evidence', {}).get('phase3', {})
    drafts, sealed = phase.get('audit_drafts'), phase.get('audit_seal')
    if type(drafts) is not list or not drafts or type(sealed) is not dict:
        raise BudgetStop('audit predecessor lacks native draft/seal provenance')
    paths = set()
    for number, entry in enumerate(drafts, 1):
        if type(entry.get('round')) is not int or entry['round'] != number:
            raise BudgetStop('audit predecessor draft rounds differ')
        writes = entry.get('part_writes')
        if type(writes) is not list or not writes or not _tool_identity(entry.get('checker')):
            raise BudgetStop('audit predecessor lacks part/check history')
        if any(not _tool_lines(write) for write in writes):
            raise BudgetStop('audit predecessor lacks typed part-write locations')
        parts = [write['part'] for write in writes]
        report = verify_check(manifest, identity, number, parts)
        if (not same_json(entry.get('receipt'), report) or
                entry.get('receipt_sha256') != check_summary(manifest, report)['receipt_sha256']):
            raise BudgetStop('audit predecessor draft receipt differs from result')
        paths.update((*check_paths(manifest, number)[:2], draft_path(manifest, number),
                      *(Path(p['path']) for p in parts)))
    report = verify_seal(manifest, identity, len(drafts), drafts[-1]['receipt']['parts'])
    if (not _tool_identity(sealed) or not same_json(sealed.get('receipt'), report) or
            sealed.get('receipt_sha256') != seal_summary(manifest, report)['receipt_sha256'] or
            result.get('registration_sha256') != identity or
            result.get('audit_sha256') != report['audit']['sha256']):
        raise BudgetStop('audit predecessor seal differs from accepted result')
    paths.update(seal_paths(manifest)[:2])
    return paths


def _tool_lines(value):
    return (type(value) is dict and type(value.get('call_line')) is int and
            type(value.get('result_line')) is int and 0 < value['call_line'] < value['result_line'])


def _tool_identity(value):
    return (_tool_lines(value) and isinstance(value.get('id'), str) and bool(value['id']))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--registration', required=True, type=Path)
    operation = parser.add_mutually_exclusive_group(required=True)
    operation.add_argument('--round', type=int, choices=(1, 2))
    operation.add_argument('--seal', action='store_true')
    args = parser.parse_args(argv)
    from .registration import sha, validate_registration
    manifest = validate_registration(args.registration)
    configuration(manifest, args.registration)
    identity = sha(args.registration)
    report = seal(manifest, identity) if args.seal else check_round(manifest, identity, args.round)
    summary = seal_summary(manifest, report) if args.seal else check_summary(manifest, report)
    print(json.dumps(summary, sort_keys=True))


if __name__ == '__main__':
    main()
