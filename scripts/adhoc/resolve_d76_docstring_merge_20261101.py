#!/usr/bin/env python3
"""Apply and verify the lead's sole D76 merge resolution (2026-11-01).

Inputs: exact 23dd/14a merge with one docstring conflict. Outputs: that resolved
file and a fresh external JSON/diff evidence directory. Serves PR #5213/D76.
Offline; refuses any other conflict or change within _lexical_relative.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OURS = '23dd522925f7b192eeadb20fb942b761801bc693'
MAIN = '14a527b7a04026a51d2ae55f8e046e662fd6fa60'
SOURCE = 'src/data_sheets_schema/evaluation/arm_comparison.py'
TEST = 'tests/test_arm_comparison.py'


def git(*args):
    return subprocess.check_output(['git', '-c', 'protocol.allow=never', *args], cwd=ROOT)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def function(raw):
    text = raw.decode()
    matches = [node for node in ast.parse(text).body
               if isinstance(node, ast.FunctionDef) and node.name == '_lexical_relative']
    if len(matches) != 1:
        raise ValueError('expected exactly one _lexical_relative')
    node = matches[0]
    lines = text.splitlines(keepends=True)
    return ''.join(lines[node.lineno - 1:node.end_lineno]).encode()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists() or output.is_relative_to(ROOT):
        raise ValueError('fresh external evidence directory required')
    if git('rev-parse', 'HEAD').decode().strip() != OURS or git('rev-parse', 'MERGE_HEAD').decode().strip() != MAIN:
        raise ValueError('unexpected merge parents')
    conflicts = git('diff', '--name-only', '--diff-filter=U').decode().splitlines()
    if conflicts != [SOURCE]:
        raise ValueError('additional or different conflict; stop without resolution')
    before = (ROOT / SOURCE).read_bytes()
    pattern = re.compile(rb'^<<<<<<< HEAD\n(.*?)^=======\n(.*?)^>>>>>>> ' + MAIN.encode() + rb'\n', re.M | re.S)
    pieces = list(pattern.finditer(before))
    if len(pieces) != 1:
        raise ValueError('expected exactly one authorized docstring conflict')
    candidate = pattern.sub(lambda match: match[1], before)
    ours = git('show', OURS + ':' + SOURCE)
    if function(candidate) != function(ours):
        raise ValueError('resolved function is not byte-identical to 23dd, including its docstring')
    # Prove both alternatives are docstring-only, rather than taking a whole file.
    other = pattern.sub(lambda match: match[2], before)
    left, right = ast.parse(candidate), ast.parse(other)
    for tree in (left, right):
        node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == '_lexical_relative')
        if not (isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant)
                and isinstance(node.body[0].value.value, str)):
            raise ValueError('conflict is not a function docstring')
        node.body.pop(0)
    if ast.dump(left, include_attributes=False) != ast.dump(right, include_attributes=False):
        raise ValueError('conflict changes more than the docstring')
    if git('ls-files', '--unmerged', '--', TEST):
        raise ValueError('arm comparison tests did not auto-merge')
    indexed_test = git('show', ':' + TEST)
    if indexed_test != (ROOT / TEST).read_bytes():
        raise ValueError('arm comparison tests differ from their auto-merged index')
    output.mkdir(parents=True)
    (output / 'conflict-before.diff').write_bytes(git('diff', '--cc', '--', SOURCE))
    (output / 'unmerged-stages.txt').write_bytes(git('ls-files', '--unmerged'))
    (ROOT / SOURCE).write_bytes(candidate)
    if (ROOT / SOURCE).read_bytes() != candidate:
        raise ValueError('resolution did not persist')
    diff = git('diff', OURS, '--', SOURCE)
    (output / 'resolved-versus-23dd.diff').write_bytes(diff)
    report = {'ours': OURS, 'main': MAIN, 'conflicts': conflicts,
              'resolution': 'take only 23dd docstring, preserving automatic merge elsewhere',
              'function_byte_identical_to_23dd': True, 'conflict_only_docstring': True,
              'whole_source_equal_to_23dd': candidate == ours,
              'tests_auto_merged': True, 'tests_sha256': sha(indexed_test),
              'source_before_sha256': sha(before), 'source_after_sha256': sha(candidate),
              'function_sha256': sha(function(candidate)), 'diff_sha256': sha(diff)}
    (output / 'verification.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(json.dumps(report, sort_keys=True))


if __name__ == '__main__':
    main()
