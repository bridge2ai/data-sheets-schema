#!/usr/bin/env python3
"""Compare the complete #5213 stack scanner arrays (2026-11-03).

Inputs: the frozen BC1+G2 report, a final-commit scanner report and its source
archive. Output: a fresh external directory with exact arrays, positional
mismatches, dispatch citations and source/producer SHA-256 identities. This
stdlib-only helper never scans, imports package code, changes Git or calls a
provider. Array order, duplicate findings and every finding field are retained.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
BASELINE_COMMIT = '72324b4cab74156c86b6bde5cea14d2e49d16595'
BASELINE_SHA256 = '7113b38be3040b5801ae3a36f856fd4e4092721b46a0703d20dbb25892e062c2'
TYPED = 'src/data_sheets_schema/typed_audit_runtime.py'
SCANNER = '.claude/skills/d4d-generation-specificity-audit/scan.py'
PHASES = ('typed_audit_worker', 'typed_audit_omission', 'typed_audit_integration')
SOURCES = (SCANNER, TYPED, 'src/data_sheets_schema/api_runner.py',
           'src/data_sheets_schema/bc1_runtime.py',
           'src/data_sheets_schema/shared_generation.py',
           'src/download/prompts/canonical_hashes.yaml')
LISTED = ['audit_batches', 'audit_grammar', 'audit_omissions',
          'evidence_assertions', 'grounding', 'scope', 'source_metadata']


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def require(ok, message):
    if not ok:
        raise ValueError(message)


def git(*args):
    env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    env.update(GIT_NO_LAZY_FETCH='1', GIT_OPTIONAL_LOCKS='0',
               GIT_CONFIG_GLOBAL='/dev/null', GIT_CONFIG_NOSYSTEM='1')
    return subprocess.check_output(['git', '--no-replace-objects', '-c',
        'protocol.allow=never', '-C', str(ROOT), *args], env=env)


def exact(left, right):
    """JSON value equality including scalar types, list order and multiplicity."""
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(exact(left[k], right[k]) for k in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(exact(a, b) for a, b in zip(left, right))
    return left == right


def pairs(items):
    result = {}
    for key, value in items:
        require(key not in result, 'duplicate JSON key: ' + key)
        result[key] = value
    return result


def invalid_constant(value):
    raise ValueError('nonfinite JSON constant: ' + value)


def load(path):
    raw = path.read_bytes()
    value = json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid_constant)
    return value, {'path': str(path.resolve()), 'bytes': len(raw), 'sha256': sha(raw)}


def report_arrays(report):
    require(report['self_test']['passed'] is True and type(report['exit']) is int
            and report['exit'] in (0, 1), 'scanner did not complete normally')
    violations = report['violations']
    listed = report['facts']['model_facing_modules']['listed_not_derived']
    require(type(violations) is list and type(listed) is list, 'scanner arrays missing')
    require(type(report['totals']['violations']) is int
            and len(violations) == report['totals']['violations'], 'violation total differs')
    require(all(type(row) is dict and row.get('violation') is True
                and row.get('path') and row.get('gates_in') for row in violations),
            'malformed violation object')
    require(all(type(name) is str for name in listed), 'malformed module list')
    return {'violations': violations, 'listed_not_derived': listed}


def comparison(before, after):
    differences = []
    for index in range(max(len(before), len(after))):
        old, new = index < len(before), index < len(after)
        if old and new and exact(before[index], after[index]):
            continue
        row = {'index': index, 'baseline_present': old, 'candidate_present': new}
        if old:
            row['baseline'] = before[index]
        if new:
            row['candidate'] = after[index]
        differences.append(row)
    return {'equal': exact(before, after), 'baseline': before, 'candidate': after,
            'positional_differences': differences}


def dispatch_evidence(report, source):
    tree = ast.parse(source, filename=TYPED)
    def single(name):
        nodes = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef,
                                                       ast.ClassDef)) and n.name == name]
        require(len(nodes) == 1 and isinstance(nodes[0], ast.FunctionDef),
                'typed entry identity differs: ' + name)
        return nodes[0]
    selector, entry = single('_bc1'), single('run')
    require(not selector.decorator_list and not entry.decorator_list, 'decorated typed entry')
    expected_selector = ast.parse('''def _bc1(spec):
    from .bc1_selection import enabled
    if enabled(spec):
        from . import bc1_runtime
        return bc1_runtime
    return None
''').body[0]
    shape = lambda node: ast.dump(node, include_attributes=False)
    require(shape(selector) == shape(expected_selector), 'typed selector body differs')
    expected_dispatch = ast.parse('''if selected := _bc1(spec):
    return selected.run(spec, carry=carry, client=client, settings=settings, usage=usage)
''').body[0]
    matches = [node for node in entry.body if shape(node) == shape(expected_dispatch)]
    require(len(matches) == 1, 'expected exactly one structural BC1 dispatch')
    dispatch = matches[0]
    prefix = entry.body[:entry.body.index(dispatch)]
    require(prefix and isinstance(prefix[0], ast.Expr)
            and isinstance(prefix[0].value, ast.Constant)
            and isinstance(prefix[0].value.value, str), 'caller-contract docstring missing')
    expected_prefix = ast.parse('''from .latch_journal import refuse_legacy_execution
refuse_legacy_execution(spec)
''').body
    require([shape(node) for node in prefix[1:]] == [shape(node) for node in expected_prefix],
            'merged legacy refusal prefix differs')
    citations = [f'{TYPED}:{selector.lineno}', f'{TYPED}:{dispatch.lineno}']
    rows = {}
    for phase in PHASES:
        evidence = report['api_meaning']['followup_turns'][phase]
        selected = [row for row in evidence['via'] if type(row.get('bounded_carry_version')) is int
                    and row['bounded_carry_version'] == 1]
        require(selected and all(exact(row.get('dispatch_evidence'), citations) for row in selected),
                'scanner did not derive the actual merged dispatch: ' + phase)
        require(any(call.startswith('src/data_sheets_schema/bc1_runtime.py:')
                    for call in evidence['calls']), 'BC1 runtime call missing: ' + phase)
        rows[phase] = evidence
    return {'derived': True, 'citations': citations, 'followup_rows': rows,
            'selector_ast': shape(selector), 'dispatch_ast': shape(dispatch),
            'entry_prefix': ''.join(source.splitlines(keepends=True)[entry.lineno - 1:dispatch.end_lineno]),
            'limit': 'Confirms scanner citations and this structural dispatch; not imported-guard purity.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    require(not git('status', '--porcelain=v1', '--untracked-files=all'), 'producer must be clean')
    head = git('rev-parse', 'HEAD').decode().strip()
    require(head == args.commit and len(head) == 40, 'producer must equal released final commit')
    source = args.source_root.resolve(strict=True)
    baseline, baseline_pin = load(args.baseline)
    candidate, candidate_pin = load(args.candidate)
    require(baseline_pin['sha256'] == BASELINE_SHA256 and baseline['commit'] == BASELINE_COMMIT,
            'frozen baseline identity differs')
    require(candidate['commit'] == head and candidate['root'] == source.name,
            'candidate scan does not name the released source archive')
    old, new = report_arrays(baseline), report_arrays(candidate)
    require(len(old['violations']) == 23 and exact(old['listed_not_derived'], LISTED),
            'expected frozen 23-violation/seven-module baseline differs')
    pins = {}
    for name in SOURCES:
        raw = (source / name).read_bytes()
        require(raw == git('show', head + ':' + name), 'archive source differs: ' + name)
        pins[name] = {'sha256': sha(raw), 'bytes': len(raw)}
    arrays = {name: comparison(old[name], new[name]) for name in old}
    try:
        dispatch = dispatch_evidence(candidate, (source / TYPED).read_text())
    except (KeyError, TypeError, ValueError, SyntaxError) as exc:
        dispatch = {'derived': False, 'error': str(exc)}
    passed = all(row['equal'] for row in arrays.values()) and dispatch['derived']
    result = {'format': 'pr5213_stack_scanner_comparison_v1', 'passed': passed,
        'producer': {'commit': head, 'tree': git('rev-parse', 'HEAD^{tree}').decode().strip(),
                     'helper_sha256': sha(Path(__file__).read_bytes())},
        'source_root': str(source), 'source_digests': pins,
        'baseline': baseline_pin, 'candidate': candidate_pin,
        'arrays': arrays, 'typed_run_dispatch': dispatch,
        'limits': ['No fields, line numbers, duplicates or array order are removed or normalized.',
                   'The 23 unchanged violations and Issue J remain unresolved; equality is not a clean audit.',
                   'Full-archive provenance belongs to the validation launcher; source pins here cover the six named files.']}
    output = args.output
    require(output.is_absolute() and '..' not in output.parts and not output.is_symlink(),
            'output must be a literal absolute external directory')
    require(output.parent.resolve(strict=True) == output.parent and not output.is_relative_to(ROOT)
            and not output.is_relative_to(source), 'output must be outside both source trees')
    output.mkdir(exist_ok=False)
    path = output / 'comparison.json'
    raw = (json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode()
    path.write_bytes(raw)
    require(path.read_bytes() == raw, 'comparison did not persist exactly')
    require(git('rev-parse', 'HEAD').decode().strip() == head and
            not git('status', '--porcelain=v1', '--untracked-files=all'), 'producer changed during comparison')
    print(json.dumps({'passed': passed, 'report': str(path), 'sha256': sha(raw)}))
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
