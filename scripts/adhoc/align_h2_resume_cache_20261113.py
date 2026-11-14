#!/usr/bin/env python3
"""Align ordinary test bytecode handling with CI, helper-2 resume, 2026-11-13.
Input/output: run_h2_resume_20261113.py. Keep bytecode outside source and retain
PYTHONDONTWRITEBYTECODE=1 only for the exact offline lanes that require it.
The active correction run retains its recorded original environment.
"""
from pathlib import Path
p = Path(__file__).with_name('run_h2_resume_20261113.py')
s = p.read_text()
old = "    env.update(PYTHONPATH=str(ROOT / 'src'), PYTHONDONTWRITEBYTECODE='1',"
new = "    env.pop('PYTHONDONTWRITEBYTECODE', None)\n    env.update(PYTHONPATH=str(ROOT / 'src'),"
assert old in s
p.write_text(s.replace(old, new))
