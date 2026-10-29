#!/usr/bin/env python3
"""PR #5212/D57, 2026-10-28: opt existing runner tests into a launch monitor.

Inputs: Python tests using the runner or the shared evidence helper. Outputs:
explicit module usefixtures marks. The monitor captures durable appends, not
mutable journal reads. Dedicated D57 expectation tests remain unwrapped.
"""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXCLUDED = {'test_pr5212_d55_fixes.py', 'test_d42_claude_d55.py', 'test_installed_wheel.py'}


def main():
    changed = []
    for path in sorted((ROOT / 'tests').rglob('test*.py')):
        if path.name in EXCLUDED:
            continue
        source = path.read_text()
        suffix = ('\n\n# D57: retain externally observed journal heads across fixture resumes.\n'
                  'pytestmark = pytest.mark.usefixtures("journal_launch_monitor")\n')
        imported_suffix = suffix.replace('pytestmark =', 'import pytest\npytestmark =')
        if source.endswith(imported_suffix):
            source = source[:-len(imported_suffix)]
        elif source.endswith(suffix):
            source = source[:-len(suffix)]
        tree = ast.parse(source)
        # Match real call/import nodes; strings used by scanner tests and
        # imports of specification alone do not execute the runner.
        calls_runner = any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
            and n.func.attr == 'execute' and ast.unparse(n.func.value) in {'api', 'api_runner', 'self.api'}
            for n in ast.walk(tree))
        imports_runner = any(isinstance(n, ast.ImportFrom) and n.module == 'data_sheets_schema.api_runner'
                             and any(a.name == 'execute' for a in n.names) for n in ast.walk(tree))
        imports_run = any(isinstance(n, ast.ImportFrom) and n.module == 'tests.test_evidence_generation_gate'
                          and any(a.name == 'run' for a in n.names) for n in ast.walk(tree))
        if not (calls_runner or imports_runner or imports_run):
            if path.read_text() != source:
                path.write_text(source)
                changed.append('removed unused monitor: ' + str(path.relative_to(ROOT)))
            continue
        # Preserve module docstrings, future imports and existing pytest marks.
        has_pytest = any(isinstance(n, ast.Import) and any(a.name == 'pytest' and a.asname is None
                                                          for a in n.names) for n in tree.body)
        has_mark = any(isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'pytestmark'
                                                       for t in n.targets) for n in tree.body)
        if has_mark:
            raise ValueError(f'review existing module mark manually: {path}')
        source += ('\n\n# D57: retain externally observed journal heads across fixture resumes.\n'
                   + ('' if has_pytest else 'import pytest\n')
                   + 'pytestmark = pytest.mark.usefixtures("journal_launch_monitor")\n')
        path.write_text(source)
        changed.append(str(path.relative_to(ROOT)))
    print('\n'.join(changed))


if __name__ == '__main__':
    main()
