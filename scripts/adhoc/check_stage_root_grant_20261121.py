#!/usr/bin/env python3
"""PR6302 stage-grant static checks and specificity evidence, 2026-11-21.

Inputs: committed archive checkout and fresh output directory argument.
Outputs: syntax/character evidence, complete scanner log and scanner reports.
This helper parses source; it never imports generation code or starts native.
"""
import ast
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
BASE = 'a3f07fa5df57c48888861196d1a0066363342f47'


def main():
    out = Path(sys.argv[1]).resolve()
    out.mkdir(parents=True, exist_ok=False)
    head = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip()
    paths = subprocess.check_output(['git', '-C', str(ROOT), 'diff', '--name-only', BASE, head],
                                    text=True).splitlines()
    parsed = []
    for name in paths:
        if name.endswith('.py'):
            ast.parse((ROOT / name).read_text(), filename=name)
            parsed.append(name)
    diff = subprocess.check_output(['git', '-C', str(ROOT), 'diff', '--unified=0', BASE, head])
    forbidden = [line for line in diff.splitlines() if line.startswith(b'+')
                 and not line.startswith(b'+++') and bytes([64]) in line]
    record = {'commit': head, 'base': BASE, 'parsed': parsed,
              'added_lines_with_forbidden_character': len(forbidden)}
    (out / 'static.json').write_text(json.dumps(record, indent=2) + '\n')
    if forbidden:
        raise ValueError('added lines contain forbidden character; inspect local diff')
    command = [sys.executable, '-B', str(ROOT / '.claude/skills/d4d-generation-specificity-audit/scan.py'),
               '--root', str(ROOT), '--report', str(out / 'specificity.md'),
               '--json', str(out / 'specificity.json')]
    with (out / 'specificity.log').open('xb') as log:
        result = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
    record['specificity_exit_code'] = result.returncode
    (out / 'static.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(record, indent=2))
    return result.returncode


if __name__ == '__main__':
    raise SystemExit(main())
