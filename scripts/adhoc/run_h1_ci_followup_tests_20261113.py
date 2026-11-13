#!/usr/bin/env python3
"""Run bounded offline issue6192 checks with unchanged G07 isolation, 2026-11-13.
Input: fixed assigned follow-up worktree, explicit tests and physical dependency
venv. Output: fresh sibling scratch cohorts with stock origin/network/JUnit and
cleanup evidence. Only source/output roots and wrapper identity are adapted.
No provider/native executable/network permissions; max two xdist workers.
"""
import hashlib
from pathlib import Path
import sys

E=Path('/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions')
DONOR=E/'codex-native-main-integration-20261112/scripts/adhoc/run_native_g07_tests_20261112.py'
DONOR_SHA='061aaf35413b7493da0216b378d88bd39b41464fd7167001ff535af13afb31fa'
ROOT=E/'codex-native-h1-ci-followups-20261113'
SCRATCH=E/'scratch-native-h1-ci-followups-20261113'
raw=DONOR.read_bytes()
if hashlib.sha256(raw).hexdigest()!=DONOR_SHA:
    raise RuntimeError('Stock runner changed; review before reuse')
namespace={'__name__':'h1_stock_followup','__file__':str(DONOR)}
exec(compile(raw,str(DONOR),'exec'),namespace)
if ROOT.resolve(strict=True)!=ROOT:
    raise RuntimeError('Assigned worktree must be physical')
namespace.update(ROOT=ROOT,SCRIPT_ROOT=ROOT,SCRATCH_BASE=SCRATCH,
                 SCRATCH=SCRATCH/'tests',__file__=str(Path(__file__).resolve()))
if __name__=='__main__':
    raise SystemExit(namespace['main']())
