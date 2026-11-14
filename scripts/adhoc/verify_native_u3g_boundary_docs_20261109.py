"""Verify U3-G's eleven D76 declarations change docstrings only, 2026-11-09.

Inputs: fixed pre-repair Git commit and clean committed assigned worktree.
Output: fresh JSON in scratch-native-u1u3/u3g, including per-file byte hashes,
non-docstring AST equality and exact declaration/precondition witnesses.
No project imports, execution, protected-file edits, network or provider use.
"""
import argparse
import ast
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
BASE = '1dd8e898704a193e025635fc5d6e18bd7c3614c4'
OUT = ROOT.parent / 'scratch-native-u1u3/u3g'
EXPECTED = {
    'native_execution_orchestration.py': ('read_final',),
    'native_shared_execution_orchestration.py': ('read_final',),
    'native_generation.py': ('main',),
    'native_subscription_admission.py': ('context', 'load_current'),
    'native_subscription_capture.py': ('capture_subscription', 'activate_capture_word',
        'capture_admission_lease', 'require_current_capture_authority', 'read_capture',
        'read_capture_for_event'),
}


def need(condition, message):
    if not condition:
        raise ValueError(message)


def quiet():
    need(not os.path.lexists(ROOT.parent / 'plans/native_quiet_window.lock'), 'quiet window active')


def git(*args):
    quiet()
    return subprocess.check_output(['/usr/bin/git', '--no-replace-objects', *args], cwd=ROOT,
        env={'PATH': '/usr/bin:/bin', 'GIT_NO_LAZY_FETCH': '1',
             'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_CONFIG_SYSTEM': '/dev/null'}, timeout=30)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


class StripFunctionDocs(ast.NodeTransformer):
    def visit_FunctionDef(self, node):
        self.generic_visit(node)
        if (node.body and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)
                and isinstance(node.body[0].value.value, str)):
            node.body.pop(0)
        return node

    visit_AsyncFunctionDef = visit_FunctionDef


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    quiet()
    need(ROOT.parent.name == 'd4d-executions' and ROOT.resolve() == ROOT, 'assigned physical worktree required')
    need(args.output.is_absolute() and args.output.parent == OUT
         and args.output.resolve() == args.output and not os.path.lexists(args.output),
         'fresh physical assigned output required')
    head = git('rev-parse', 'HEAD').decode().strip()
    git('diff-index', '--quiet', 'HEAD', '--')
    helper = str(Path(__file__).relative_to(ROOT))
    need(git('show', head + ':' + helper) == Path(__file__).read_bytes(), 'helper must be committed')
    paths = {'src/data_sheets_schema/' + name for name in EXPECTED}
    changed = set(git('diff', '--name-only', BASE, head).decode().splitlines())
    need(changed == paths | {helper}, 'repair changed more than five declaration files and this helper')
    rows, declaration_count = [], 0
    for name, wanted in EXPECTED.items():
        relative = 'src/data_sheets_schema/' + name
        before, after = git('show', BASE + ':' + relative), (ROOT / relative).read_bytes()
        need(after == git('show', head + ':' + relative), 'source differs from committed bytes')
        old, new = ast.parse(before), ast.parse(after)
        left = ast.dump(StripFunctionDocs().visit(copy.deepcopy(old)), include_attributes=False)
        right = ast.dump(StripFunctionDocs().visit(copy.deepcopy(new)), include_attributes=False)
        need(left == right, 'non-docstring syntax changed: ' + relative)
        functions = lambda tree: [node for node in ast.walk(tree)
                                  if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
        old_functions, new_functions = functions(old), functions(new)
        need(len(old_functions) == len(new_functions), 'function inventory changed')
        declarations = []
        for old_fn, new_fn in zip(old_functions, new_functions):
            need(old_fn.name == new_fn.name, 'function order changed')
            old_doc, new_doc = ast.get_docstring(old_fn) or '', ast.get_docstring(new_fn) or ''
            if old_doc == new_doc:
                continue
            need(new_fn.name in wanted and 'RunSpec boundary:' not in old_doc,
                 'unexpected or previously declared function changed')
            need(new_doc.startswith(old_doc), 'prior docstring text not preserved')
            need(re.findall(r'^RunSpec boundary:\s*(\S+)\s*$', new_doc, re.MULTILINE)
                 == ['validated-caller'], 'declaration is not exactly validated-caller')
            preconditions = re.findall(r'^RunSpec precondition:\s*(\S.*)$', new_doc, re.MULTILINE)
            need(len(preconditions) == 1, 'exactly one explicit precondition required')
            declarations.append({'function': new_fn.name, 'old_line': old_fn.lineno,
                'new_line': new_fn.lineno,
                'precondition': new_doc.split('RunSpec precondition:', 1)[1].strip(),
                'old_docstring': old_doc, 'new_docstring': new_doc})
        need({row['function'] for row in declarations} == set(wanted)
             and len(declarations) == len(wanted), 'declaration roster differs')
        declaration_count += len(declarations)
        rows.append({'path': relative, 'before_sha256': sha(before), 'after_sha256': sha(after),
            'non_docstring_ast_equal': True, 'declarations': declarations})
    need(declaration_count == 11, 'expected exactly eleven declarations')
    result = {'kind': 'native_u3g_d76_docstring_repair', 'base_commit': BASE, 'source_commit': head,
        'files': rows, 'declaration_count': declaration_count, 'runtime_syntax_unchanged': True,
        'scope': 'Source syntax witness only; runtime and census tests are separate.',
        'helper_sha256': sha(Path(__file__).read_bytes())}
    raw = (json.dumps(result, indent=2, sort_keys=True) + '\n').encode()
    quiet()
    with args.output.open('xb') as stream:
        stream.write(raw)
    need(args.output.read_bytes() == raw, 'evidence readback differs')
    print(json.dumps({'source_commit': head, 'declarations': declaration_count,
                      'sha256': sha(raw), 'output': str(args.output)}))


if __name__ == '__main__':
    main()
