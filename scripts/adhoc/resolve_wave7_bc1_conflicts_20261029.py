#!/usr/bin/env python3
# Purpose: reproduce only reviewed ordinary-file resolutions in the BC1 packet.
# Inputs: exact conflict files/heads; outputs: resolved ordinary source plus fresh JSON proof.
# Refs BC1 Wave7 Task5 and #5158/#5162/#5164/#5210/#5212/#5211; 2026-10-29.
"""No protected edits, checkout commands, provider calls or tests."""
import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
PROTECTED = ROOT / 'src/data_sheets_schema/shared_generation.py'
PROTECTED_SHA = '1c4436b5ea689fcd674c848a722dd9a86495692ad83401682f3d805f49acb6d6'
A13 = 'cd07f2a3738e146eeaa30ae86d35d3161eb3413b'
A23 = '90312e30e8d957e3b79510abe9ea768967983224'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('reviewed replacement is not unique: ' + repr(old))
    return text.replace(old, new, 1)


def a13(text):
    pattern = re.compile(r'^<<<<<<< HEAD\n(.*?)^=======\n(.*?)^>>>>>>> ' + A13 + r'\n', re.M | re.S)
    hunks = list(pattern.finditer(text))
    if len(hunks) != 9:
        raise ValueError('A13 requires exactly the nine reviewed conflict hunks')
    ours = [h.group(1) for h in hunks]
    theirs = [h.group(2) for h in hunks]
    sizing_check = (
        '                try:\n'
        '                    sized = check_registration_sizing(reg_file, raw)\n'
        '                except ValueError as exc:\n'
        '                    raise click.ClickException(str(exc)) from exc\n')
    check = once(theirs[6], '                verified[(proj, lbl)]',
                 sizing_check + '                verified[(proj, lbl)]')
    check = once(check, '                click.echo(f"  ✓ {proj}: {reg_file.name}")\n',
        '                click.echo(f"  ✓ {proj}: {reg_file.name}" + '
        '(f" (sized: {sizing_path(reg_file).name})" if sized else ""))\n')
    replacements = [
        ours[0] + theirs[0],
        'import math\nimport os\nimport sys\nimport threading\nimport types\n',
        once(ours[2], 'def prepare_registration(', '@_worktree_resources\ndef prepare_registration('),
        once(ours[3], '    bc1_fan_in: int = 2,\n',
             '    bc1_fan_in: int = 2,\n    worktree: Path | str | None = None,\n'),
        ours[4] + '                worktree=worktree,\n',
        '',
        check,
        once(ours[7], '                    sizing_record=records.get(proj),\n',
             '                    sizing_record=records.get(proj),\n                    worktree=worktree,\n'),
        theirs[8] + once(ours[8],
             '            click.echo(f"  ✓ {proj}: registration_id={reg[\'registration_id\']} sha256={reg_sha}")\n', ''),
    ]
    result, offset = [], 0
    for match, replacement in zip(hunks, replacements):
        result.extend((text[offset:match.start()], replacement))
        offset = match.end()
    result.append(text[offset:])
    resolved = ''.join(result)
    resolved = once(resolved,
        '    active_audit_limits = resolve_audit_limits(project, partition, audit_limits, arm=arm)\n',
        '    active_audit_limits = resolve_audit_limits(project, partition, audit_limits, arm=arm,\n'
        '        bounded_carry_version=bounded_carry_version, bc1_fan_in=bc1_fan_in)\n')
    return resolved


def a23(text):
    return once(text,
        '<<<<<<< HEAD\n'
        '            # Written with the registration, once every check has passed.\n'
        '=======\n'
        '            from scripts.build_draft_contexts import serialize_draft_context\n\n'
        '>>>>>>> ' + A23 + '\n',
        '            from scripts.build_draft_contexts import serialize_draft_context\n\n'
        '            # Written with the registration, once every check has passed.\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('merge', choices=['a13', 'a23'])
    parser.add_argument('--expected-input-sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    target = ROOT / 'scripts/build_api_registrations.py'
    raw = target.read_bytes()
    if target.is_symlink() or sha(raw) != args.expected_input_sha256:
        raise ValueError('source differs from the reviewed conflict file')
    if sha(PROTECTED.read_bytes()) != PROTECTED_SHA:
        raise ValueError('protected source differs; stop without restoring')
    out = args.output
    if not out.is_absolute() or out.resolve() != out or out.exists() or out.is_relative_to(ROOT):
        raise ValueError('fresh external physical evidence path required')
    incoming, resolve = {'a13': (A13, a13), 'a23': (A23, a23)}[args.merge]
    resolved = resolve(raw.decode()).encode()
    if any(line.startswith((b'<<<<<<< ', b'=======', b'>>>>>>> ')) for line in resolved.splitlines()):
        raise ValueError('unresolved conflict marker')
    proof = {'merge': args.merge, 'incoming': incoming, 'path': str(target.relative_to(ROOT)),
             'before_sha256': sha(raw), 'after_sha256': sha(resolved),
             'helper_sha256': sha(Path(__file__).read_bytes()),
             'protected_sha256': PROTECTED_SHA, 'review': 'Codex parent read-only review before application',
             'scope': 'ordinary conflict union only; no tests or protected edits'}
    with out.open('x') as stream:
        json.dump(proof, stream, indent=2, sort_keys=True)
        stream.write('\n')
    target.write_bytes(resolved)
    if target.read_bytes() != resolved or sha(PROTECTED.read_bytes()) != PROTECTED_SHA:
        raise ValueError('post-write verification failed')
    print(json.dumps(proof, sort_keys=True))


if __name__ == '__main__':
    main()
