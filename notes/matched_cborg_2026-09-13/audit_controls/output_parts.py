"""Opt-in native audit output: exact bounded UTF-8 parts, never content repair (#2144)."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import stat

from budgeted_cborg import BudgetStop

PROTOCOL = 'raw_utf8_parts_v1'
MAX_PARTS = 64
MAX_PART_BYTES = 32768


def canonical(path):
    path = Path(path)
    if not path.is_absolute() or path.resolve() != path or path.is_symlink():
        raise BudgetStop('audit output paths must be canonical and nonsymlinked')
    return path


def specification(manifest, registration_path):
    job = manifest['job']
    directory = Path(job['output_dir']) / 'audit-parts'
    return {'protocol': PROTOCOL, 'max_parts': MAX_PARTS, 'max_part_bytes': MAX_PART_BYTES,
            'parts': [str(directory / f'{i:06d}.txt') for i in range(1, MAX_PARTS + 1)],
            'assemble_argv': [manifest['python'], '-m', 'audit_controls.output_parts',
                              '--registration', str(registration_path)]}


def select(manifest, registration_path, enabled):
    if type(enabled) is not bool:
        raise BudgetStop('staged audit output requires an explicit boolean')
    if enabled:
        manifest['audit_output'] = specification(manifest, registration_path)


def configuration(manifest, registration_path=None):
    if 'audit_output' not in manifest:
        return None
    job = manifest['job']
    path = canonical(registration_path or Path(job['attempt_dir']).parent.parent / 'registration.json')
    block = manifest['audit_output']
    if (manifest.get('kind') != 'd4d_native_audit_continuation' or
            block != specification(manifest, path) or
            type(block.get('max_parts')) is not int or type(block.get('max_part_bytes')) is not int):
        raise BudgetStop('unsupported or changed staged audit output registration')
    attempt, output = canonical(job['attempt_dir']), canonical(job['output_dir'])
    if (attempt != path.parent / 'attempts' / job['id'] or output != attempt / 'output' or
            canonical(job['audit_path']) != output / 'audit.json'):
        raise BudgetStop('staged audit output layout differs from registration')
    for value in block['parts']:
        canonical(value)
    return block


def instruction(manifest):
    block = configuration(manifest)
    if block is None:
        return None
    return ('Write the complete audit as consecutive raw UTF-8 text parts with native Write. '
            'Use a nonempty prefix of these fixed slots, in numeric order, starting at 000001.txt:\n'
            + str(Path(block['parts'][0]).parent) + '/000001.txt through 000064.txt\n'
            'Each part must contain 1 to 32768 UTF-8 bytes. Split the audit text at any UTF-8 character '
            'boundary; individual parts need not be complete JSON. Do not add separators or repeat text '
            'between parts. Wait for each successful Write result before another tool. Registered input '
            'Reads remain available between completed part Writes. Do not rewrite a completed part, '
            'write an unregistered path, or write audit.json directly. Unused trailing slots are allowed.\n'
            'After all parts are complete, invoke this exact foreground assembly command once:\n'
            + shlex.join(block['assemble_argv']) + '\n'
            'It concatenates the exact part bytes without parsing, normalizing, repairing or inferring '
            'scientific content. A failed assembly ends the attempt. After assembly starts, the only '
            'permitted next tool is the single terminal validator, after the successful assembly result.\n')


def read_regular(path, limit, *, links=1):
    path = canonical(path)
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, 'rb') as handle:
        info = os.fstat(handle.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != links or info.st_size > limit:
            raise BudgetStop('audit output must be bounded single-link regular files')
        raw = handle.read(limit + 1)
        after = os.fstat(handle.fileno())
        current = path.lstat()
        if (len(raw) > limit or (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns) !=
                (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns) or
                (current.st_dev, current.st_ino, current.st_nlink) != (info.st_dev, info.st_ino, links)):
            raise BudgetStop('audit output changed while reading')
    return raw


def describe(path, raw):
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def same_json(left, right):
    return json.dumps(left, sort_keys=True, allow_nan=False) == json.dumps(right, sort_keys=True, allow_nan=False)


def read_parts(manifest):
    block = configuration(manifest)
    if block is None:
        raise BudgetStop('staged audit output is not selected')
    directory = canonical(Path(block['parts'][0]).parent)
    names = sorted(p.name for p in directory.iterdir())  # Includes hidden/ignored entries.
    if not names or len(names) > MAX_PARTS or names != [Path(p).name for p in block['parts'][:len(names)]]:
        raise BudgetStop('audit parts have gaps, extra files or no completed prefix')
    pieces, descriptions = [], []
    for path in block['parts'][:len(names)]:
        raw = read_regular(path, MAX_PART_BYTES)
        if not raw:
            raise BudgetStop('audit parts must be nonempty')
        raw.decode('utf-8', errors='strict')
        pieces.append(raw)
        descriptions.append(describe(path, raw))
    return b''.join(pieces), descriptions


def receipt_paths(manifest):
    attempt = canonical(manifest['job']['attempt_dir'])
    return attempt / 'assembly.json', attempt / 'assembly_failure.json'


def ready_path(manifest):
    return canonical(manifest['job']['attempt_dir']) / 'assembly_ready.json'


def expected_receipt(manifest, identity, raw, parts):
    return {'schema_version': 1, 'operation': 'concatenate_utf8_parts', 'checked': True,
            'passed': True, 'job_id': manifest['job']['id'], 'registration_sha256': identity,
            'parts': parts, 'audit': describe(manifest['job']['audit_path'], raw)}


def verify_assembly(manifest, identity, expected_parts):
    receipt, failure = receipt_paths(manifest)
    if os.path.lexists(failure):
        raise BudgetStop('audit assembly failed; no further admission')
    ready = canonical(ready_path(manifest))
    if not ready.is_file() or not os.path.samefile(receipt, ready):
        raise BudgetStop('audit assembly lacks its completed preservation witness')
    read_regular(ready, 131072, links=2)
    raw, parts = read_parts(manifest)
    if not same_json(parts, expected_parts):
        raise BudgetStop('audit parts differ from completed native Writes')
    current = read_regular(manifest['job']['audit_path'], MAX_PARTS * MAX_PART_BYTES)
    if current != raw:
        raise BudgetStop('assembled audit differs from exact native part bytes')
    from .contract import strict_json
    report = strict_json(read_regular(receipt, 131072, links=2))
    if not same_json(report, expected_receipt(manifest, identity, raw, parts)):
        raise BudgetStop('audit assembly receipt differs from current bytes or registration')
    return report


def validate_output(manifest):
    """Pure checker requires the registered assembly, never a bare final file."""
    path = Path(manifest['job']['attempt_dir']).parent.parent / 'registration.json'
    configuration(manifest, path)
    raw = read_regular(path, 16777216)
    from .contract import strict_json
    if not same_json(strict_json(raw), manifest):
        raise BudgetStop('staged audit manifest differs from its registration')
    _, parts = read_parts(manifest)
    return verify_assembly(manifest, hashlib.sha256(raw).hexdigest(), parts)


def summary(manifest, report):
    """Bounded Bash stdout; the full part roster stays outside native output."""
    receipt, _ = receipt_paths(manifest)
    return {'schema_version': 1, 'operation': 'concatenate_utf8_parts', 'passed': True,
            'job_id': report['job_id'], 'registration_sha256': report['registration_sha256'],
            'part_count': len(report['parts']), 'audit_sha256': report['audit']['sha256'],
            'audit_bytes': report['audit']['bytes'],
            'receipt_sha256': hashlib.sha256(read_regular(receipt, 131072, links=2)).hexdigest()}


def closure_paths(manifest, registration_path, result):
    """Validate result-bound staged provenance before a successor pins it."""
    if configuration(manifest, registration_path) is None:
        return set()
    identity = hashlib.sha256(read_regular(registration_path, 16777216)).hexdigest()
    phase = result.get('evidence', {}).get('phase3', {})
    writes, assembly = phase.get('audit_parts'), phase.get('audit_assembly')
    if not isinstance(writes, list) or not writes or not isinstance(assembly, dict):
        raise BudgetStop('staged predecessor lacks native part/assembly provenance')
    parts = [entry['part'] for entry in writes]
    report = verify_assembly(manifest, identity, parts)
    if (not same_json(assembly.get('receipt'), report) or
            assembly.get('receipt_sha256') != summary(manifest, report)['receipt_sha256'] or
            result.get('registration_sha256') != identity or
            result.get('audit_sha256') != report['audit']['sha256']):
        raise BudgetStop('staged predecessor assembly differs from its accepted result')
    receipt, _ = receipt_paths(manifest)
    return {receipt, ready_path(manifest), *(Path(entry['path']) for entry in parts)}


def assemble(manifest, identity):
    """Exclusive assembly; success receipt follows all output writes and checks."""
    if configuration(manifest) is None:
        raise BudgetStop('staged audit output is not selected')
    receipt, failure = receipt_paths(manifest)
    canonical(receipt); canonical(failure)
    ready = canonical(ready_path(manifest))
    if os.path.lexists(failure) or os.path.lexists(ready):
        raise BudgetStop('audit assembly previously failed')
    # Reserve this operation before touching output; a partial receipt cannot retry.
    try:
        with receipt.open('x', encoding='utf-8') as marker:
            raw, parts = read_parts(manifest)
            target = canonical(manifest['job']['audit_path'])
            descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            with os.fdopen(descriptor, 'wb') as handle:
                handle.write(raw); handle.flush(); os.fsync(handle.fileno())
            directory = os.open(canonical(target.parent), os.O_RDONLY | os.O_NOFOLLOW)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
            if read_parts(manifest) != (raw, parts) or read_regular(target, MAX_PARTS * MAX_PART_BYTES) != raw:
                raise BudgetStop('audit parts or assembled bytes changed during assembly')
            report = expected_receipt(manifest, identity, raw, parts)
            marker.write(json.dumps(report, sort_keys=True) + '\n')
            marker.flush(); os.fsync(marker.fileno())
        directory = os.open(canonical(receipt.parent), os.O_RDONLY | os.O_NOFOLLOW)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
        # Last fallible preservation operation. No fsync/cleanup follows this
        # witness: loss on reboot fails closed; reentry never repairs it.
        os.link(receipt, ready, follow_symlinks=False)
        return report
    except BaseException:
        try:
            with failure.open('x', encoding='utf-8') as handle:
                handle.write('{"passed":false}\n')
        except OSError:
            pass  # Missing readiness cannot be repaired by later invocation.
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--registration', required=True, type=Path)
    args = parser.parse_args()
    from .registration import sha, validate_registration
    manifest = validate_registration(args.registration)
    configuration(manifest, args.registration)
    report = assemble(manifest, sha(args.registration))
    print(json.dumps(summary(manifest, report), sort_keys=True))


if __name__ == '__main__':
    main()
