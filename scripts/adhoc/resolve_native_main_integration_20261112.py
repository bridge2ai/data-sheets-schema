#!/usr/bin/env python3
"""Resolve G04's reviewed scanner conflicts and retain main protected bytes.

Date: 2026-11-12. Inputs: the assigned in-progress 5871/main merge.
Outputs: resolved files and .temp/native-main-integration/merge-resolution.json.
No tests, private composition, native/provider calls or publication.
"""
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
NATIVE = '1a137b58860416a31618de44173180d021dfcc61'
MAIN = '7ad8c9e7295f1575ae9108ea62c12c83b1dd4db1'
SCAN = '.claude/skills/d4d-generation-specificity-audit/scan.py'
SKILL = '.claude/skills/d4d-generation-specificity-audit/SKILL.md'
PROTECTED = [
    'src/data_sheets_schema/shared_generation.py',
    'src/data_sheets_schema/api_runner.py',
    'src/download/prompts/canonical_hashes.yaml',
    'tests/utils/run_spec_boundary_contracts.json',
]


def git(*args):
    return subprocess.check_output(['/usr/bin/git', *args], cwd=ROOT)


def sha(value):
    return hashlib.sha256(value).hexdigest()


def resolve(text, choices):
    pattern = re.compile(r'^<<<<<<< HEAD\n(.*?)^=======\n(.*?)^>>>>>>> ' + MAIN + r'\n', re.M | re.S)
    matches = list(pattern.finditer(text))
    assert len(matches) == len(choices), (len(matches), len(choices))
    counter = iter(choices)
    def select(match):
        choice = next(counter)
        return {'native': match[1], 'main': match[2], 'both': match[1] + '\n' + match[2]}[choice]
    result = pattern.sub(select, text)
    assert not re.search(r'^(<<<<<<<|=======|>>>>>>>)', result, re.M)
    return result


def main():
    assert ROOT.name == 'codex-native-main-integration-20261112'
    assert git('rev-parse', 'HEAD').decode().strip() == NATIVE
    assert git('rev-parse', 'MERGE_HEAD').decode().strip() == MAIN
    assert set(git('diff', '--name-only', '--diff-filter=U').decode().splitlines()) == {SCAN, SKILL}
    out = ROOT / '.temp/native-main-integration'
    out.mkdir(parents=True, exist_ok=True)
    evidence = out / 'merge-resolution.json'
    assert not evidence.exists(), 'preserve earlier resolution evidence'
    ledger = []
    for path, choices in [(SCAN, ['main'] * 9), (SKILL, ['native', 'both'])]:
        original = (ROOT / path).read_text()
        resolved = resolve(original, choices)
        if path == SCAN:
            ast.parse(resolved, filename=path)
        else:
            old = ('The U3-F B2\nplain-container-alias gap and F3d helper-stdout gap remain tracked under #5657\nand N1; this contract does not claim to repair them.')
            new = ('The integration also retains main\'s plain-alias and direct module-command\ndiscovery changes documented below. Copied-alias and imported helper-stdout\nlimitations remain documented there; this native contract does not repair them.')
            assert old in resolved
            resolved = resolved.replace(old, new, 1)
        ledger.append({
            'path': path, 'kind': 'content', 'blocks': len(choices),
            'stage_blobs': {str(n): sha(git('show', f':{n}:{path}')) for n in (1, 2, 3)},
            'conflicted_sha256': sha(original.encode()),
            'resolved_sha256': sha(resolved.encode()), 'choices': choices,
        })
        (ROOT / path).write_text(resolved)
    subprocess.run(['/usr/bin/git', 'restore', '--source', MAIN, '--staged', '--worktree', '--', *PROTECTED], cwd=ROOT, check=True)
    hashes = []
    for path in PROTECTED:
        expected = git('show', f'{MAIN}:{path}')
        actual = (ROOT / path).read_bytes()
        assert actual == expected, path
        hashes.append({'path': path, 'main_sha256': sha(expected), 'candidate_sha256': sha(actual), 'equal': True})
    v1 = 'src/data_sheets_schema/native_subscription_guard.py'
    assert (ROOT / v1).read_bytes() == git('show', f'{NATIVE}:{v1}')
    data = {'native_parent': NATIVE, 'main_parent': MAIN, 'conflicts': ledger,
            'protected_files': hashes, 'v1_sha256': sha((ROOT / v1).read_bytes()),
            'scope': 'main command-discovery updates plus native source contracts; protected files equal main; v1 unchanged'}
    evidence.write_text(json.dumps(data, indent=2) + '\n')
    assert json.loads(evidence.read_text()) == data
    print(str(evidence))
    print(sha(evidence.read_bytes()))


if __name__ == '__main__':
    main()
