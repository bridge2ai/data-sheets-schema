#!/usr/bin/env python3
# Purpose: prove which canonical CHORUS wire bytes changed across inherited prompt assets.
# Inputs: two completed offline wire captures and exact Git bases; output: compact reversible differences.
# Refs #5210 / #5157 and D38; 2026-10-28. No providers or production writes.
import argparse
from copy import deepcopy
import difflib
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OLD = 'f8c5ac73caba610d40c49aaceddb31ead3590a72'
NEW = '04799422669fb2bd9f571bf8c0800dfc4b0ef008'
ASSETS = ('.claude/commands/d4d-uniform-rules-v2.md', 'src/download/prompts/d4d_generic_arm_prompt_v10.md')
PHASES = ('reconcile_full', 'report', 'report_regate')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def git(*args):
    env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    env.update(GIT_NO_LAZY_FETCH='1', GIT_OPTIONAL_LOCKS='0')
    return subprocess.check_output(['git', '--no-replace-objects', *args], cwd=ROOT, env=env)


def differences(left, right, path=()):
    if type(left) is not type(right):
        yield path, left, right
    elif isinstance(left, dict):
        if left.keys() != right.keys():
            raise ValueError('wire object keys differ: ' + str(path))
        for key in sorted(left):
            yield from differences(left[key], right[key], (*path, key))
    elif isinstance(left, list):
        if len(left) != len(right):
            raise ValueError('wire array lengths differ: ' + str(path))
        for index, (a, b) in enumerate(zip(left, right)):
            yield from differences(a, b, (*path, index))
    elif left != right:
        yield path, left, right


def replace_at(document, path, value):
    selected = document
    for step in path[:-1]:
        selected = selected[step]
    selected[path[-1]] = value


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--old', type=Path, required=True)
    parser.add_argument('--new', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('fresh output required')
    outcomes = {name: json.loads((root / 'outcome.json').read_bytes()) for name, root in [('old', args.old), ('new', args.new)]}
    if not all(o['passed'] and o['source_unchanged'] and o['returncode'] == 0 for o in outcomes.values()):
        raise ValueError('completed unchanged successful captures required')
    assets, transforms = [], []
    for path in ASSETS:
        old, new = git('show', OLD + ':' + path), git('show', NEW + ':' + path)
        left, right = old.decode().splitlines(keepends=True), new.decode().splitlines(keepends=True)
        hunks = []
        for kind, i, j, k, m in difflib.SequenceMatcher(a=left, b=right, autojunk=False).get_opcodes():
            if kind != 'equal':
                hunk = {'path': path, 'old_lines': [i + 1, j], 'new_lines': [k + 1, m],
                        'old': ''.join(left[i:j]), 'new': ''.join(right[k:m])}
                hunks.append(hunk)
                transforms.append(hunk)
        assets.append({'path': path, 'old_sha256': sha(old), 'new_sha256': sha(new), 'hunks': hunks})
    results = {}
    for phase in PHASES:
        old_raw = (args.old / (phase + '.canonical.json')).read_bytes()
        new_raw = (args.new / (phase + '.canonical.json')).read_bytes()
        for name, raw in [('old', old_raw), ('new', new_raw)]:
            row = outcomes[name]['wires'][phase]
            if sha(raw) != row['sha256'] or len(raw) != row['bytes']:
                raise ValueError('wire bytes do not match captured outcome')
        old, new = json.loads(old_raw), json.loads(new_raw)
        if canonical(old) != old_raw or canonical(new) != new_raw:
            raise ValueError('capture is not canonical fixture JSON')
        rebuilt, changes = deepcopy(old), []
        for path, left, right in differences(old, new):
            if not isinstance(left, str) or not isinstance(right, str):
                raise ValueError('non-string model-facing change: ' + str(path))
            transformed, used = left, []
            for hunk in transforms:
                count = transformed.count(hunk['old']) if hunk['old'] else 0
                if count:
                    transformed = transformed.replace(hunk['old'], hunk['new'])
                    used.append({'asset': hunk['path'], 'old_lines': hunk['old_lines'], 'occurrences': count})
            # Capture reversible character edits plus their UTF-8 byte offsets.
            edits, reconstructed = [], left
            operations = difflib.SequenceMatcher(a=left, b=right, autojunk=True).get_opcodes()
            for kind, i, j, k, m in operations:
                if kind != 'equal':
                    edits.append({'old_character_span': [i, j],
                        'old_byte_span': [len(left[:i].encode()), len(left[:j].encode())],
                        'old': left[i:j], 'new': right[k:m]})
            for edit in reversed(edits):
                i, j = edit['old_character_span']
                if reconstructed[i:j] != edit['old']:
                    raise ValueError('reversible edit old bytes differ')
                reconstructed = reconstructed[:i] + edit['new'] + reconstructed[j:]
            if reconstructed != right:
                raise ValueError('reversible edits do not reproduce changed string')
            replace_at(rebuilt, path, reconstructed)
            changes.append({'path': list(path), 'old_sha256': sha(left.encode()), 'new_sha256': sha(right.encode()),
                            'edits': edits, 'inherited_asset_hunks_applied': used,
                            'asset_hunks_explain_exact_string': transformed == right})
        if canonical(rebuilt) != new_raw:
            raise ValueError('reversible patch does not reproduce exact new canonical bytes')
        results[phase] = {'old_sha256': sha(old_raw), 'new_sha256': sha(new_raw),
            'old_bytes': len(old_raw), 'new_bytes': len(new_raw), 'changes': changes,
            'canonical_patch_replay_byte_identical': True,
            'only_inherited_asset_hunks': all(c['asset_hunks_explain_exact_string'] for c in changes),
            'old_golden_reproduced': outcomes['old']['wires'][phase]['matches_old_golden']}
    protected = (*ASSETS, 'src/download/prompts/canonical_hashes.yaml', 'src/data_sheets_schema/shared_generation.py')
    output = {'old_base': OLD, 'new_base': NEW, 'old_evidence': str(args.old), 'new_evidence': str(args.new),
        'old_outcome_sha256': sha((args.old / 'outcome.json').read_bytes()),
        'new_outcome_sha256': sha((args.new / 'outcome.json').read_bytes()),
        'assets': assets, 'phases': results,
        'protected_asset_diff': git('diff', OLD, NEW, '--', *protected).decode(),
        'inherited_protected_commits': git('log', '--format=%H %s', OLD + '..' + NEW, '--', *protected).decode(),
        'scientific_acceptance': 'not_assessed'}
    with args.output.open('x') as stream:
        json.dump(output, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps({p: {k: v for k, v in row.items() if k != 'changes'} for p, row in results.items()}, sort_keys=True))


if __name__ == '__main__':
    main()
