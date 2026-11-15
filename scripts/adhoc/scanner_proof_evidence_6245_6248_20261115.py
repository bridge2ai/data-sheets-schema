"""Compare saved scanner runs and test results for issues 6245–6248.

Inputs: baseline-frozen.json, candidate-final-v2.json, required.xml in assigned scratch;
Git candidate f5c7c312f and current worktree. Output: comparison.json and stdout.
No source imports or execution; no external requests. Date: 2026-11-15.
"""
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
BASE = 'f5c7c312f'
SKILL = '.claude/skills/d4d-generation-specificity-audit/'


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def main():
    scratch = Path(sys.argv[1])
    before = json.loads((scratch / 'baseline-frozen.json').read_text())
    after = json.loads((scratch / 'candidate-final-v2.json').read_text())
    changed = git('diff', BASE, '--name-only').decode().splitlines()
    assets = {}
    for path in git('ls-tree', '-r', '--name-only', BASE, SKILL).decode().splitlines():
        old = git('show', BASE + ':' + path)
        new = (ROOT / path).read_bytes()
        assets[path] = {'before': hashlib.sha256(old).hexdigest(),
                        'after': hashlib.sha256(new).hexdigest(), 'changed': old != new}
    tests = {}
    for case in ET.parse(scratch / 'required.xml').getroot().iter('testcase'):
        name = case.attrib['classname']
        group = tests.setdefault(name, {'passed': 0, 'failed': 0, 'errors': 0, 'skipped': 0})
        status = ('failed' if case.find('failure') is not None else
                  'errors' if case.find('error') is not None else
                  'skipped' if case.find('skipped') is not None else 'passed')
        group[status] += 1
    focused = {}
    focused_path = scratch / 'final-focused-v2.xml'
    if focused_path.is_file():
        for case in ET.parse(focused_path).getroot().iter('testcase'):
            name = case.attrib['classname']
            group = focused.setdefault(name, {'passed': 0, 'failed': 0, 'errors': 0, 'skipped': 0})
            status = ('failed' if case.find('failure') is not None else
                      'errors' if case.find('error') is not None else
                      'skipped' if case.find('skipped') is not None else 'passed')
            group[status] += 1
    scanner = SKILL + 'scan.py'
    def constants(raw):
        return [ast.dump(node, include_attributes=False) for node in ast.parse(raw).body
                if isinstance(node, (ast.Assign, ast.AnnAssign))]
    old_scanner = git('show', BASE + ':' + scanner)
    new_scanner = (ROOT / scanner).read_bytes()
    def functions(raw):
        return {node.name: ast.dump(node, include_attributes=False)
                for node in ast.parse(raw).body if isinstance(node, ast.FunctionDef)}
    old_functions, new_functions = functions(old_scanner), functions(new_scanner)
    reruns = {}
    for path in sorted(scratch.glob('serial-*.xml')):
        rows = []
        for case in ET.parse(path).getroot().iter('testcase'):
            status = ('failed' if case.find('failure') is not None else
                      'errors' if case.find('error') is not None else
                      'skipped' if case.find('skipped') is not None else 'passed')
            rows.append({'class': case.attrib['classname'], 'name': case.attrib['name'], 'status': status})
        reruns[path.name] = rows
    result = {
        'base': git('rev-parse', BASE).decode().strip(),
        'head': git('rev-parse', 'HEAD').decode().strip(),
        'changed_files': changed,
        'scanner_assets': assets,
        'tests': tests,
        'final_focused_tests': focused,
        'serial_reruns': reruns,
        'required_test_totals': {status: sum(row[status] for row in tests.values())
                                 for status in ('passed', 'failed', 'errors', 'skipped')},
        'final_focused_totals': {status: sum(row[status] for row in focused.values())
                                 for status in ('passed', 'failed', 'errors', 'skipped')},
        'scanner_module_constants_unchanged': constants(old_scanner) == constants(new_scanner),
        'changed_scanner_functions': [name for name in sorted(old_functions.keys() | new_functions.keys())
                                      if old_functions.get(name) != new_functions.get(name)],
        'baseline_exit': before['exit'], 'candidate_exit': after['exit'],
        'baseline_violations': len(before['violations']),
        'candidate_violations': len(after['violations']),
        'same_violations': before['violations'] == after['violations'],
        'changed_report_keys': [key for key in sorted(before.keys() | after.keys())
                                if before.get(key) != after.get(key)],
        'report_key_equality': {key: before.get(key) == after.get(key)
                                for key in sorted(before.keys() | after.keys())},
    }
    raw = json.dumps(result, indent=2, sort_keys=True) + '\n'
    (scratch / 'comparison.json').write_text(raw)
    assert (scratch / 'comparison.json').read_text() == raw
    print(raw, end='')


if __name__ == '__main__':
    main()
