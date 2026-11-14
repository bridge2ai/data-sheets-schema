#!/usr/bin/env python3
"""Align local test caching and supplemental budget origin, 2026-11-13.
Input/output: run_h2_resume_20261113.py. Keep bytecode outside source and retain
PYTHONDONTWRITEBYTECODE=1 only for the exact offline lanes that require it.
Budget needs local PYTHONPATH to avoid the primary interpreter's stale editable
checkout; native/audit retain their exact CI PYTHONPATH. Active runs are unchanged.
"""
from pathlib import Path
p = Path(__file__).with_name('run_h2_resume_20261113.py')
s = p.read_text()
old = "    env.update(PYTHONPATH=str(ROOT / 'src'), PYTHONDONTWRITEBYTECODE='1',"
new = "    env.pop('PYTHONDONTWRITEBYTECODE', None)\n    env.update(PYTHONPATH=str(ROOT / 'src'),"
s = s.replace(old, new)
s = s.replace("        if args.cohort == 'budget':\n            env.pop('PYTHONPATH', None)\n",
    "        # Supplemental budget uses local src instead of the primary editable checkout.\n")
assert new in s and "env.pop('PYTHONPATH', None)" not in s
p.write_text(s)
