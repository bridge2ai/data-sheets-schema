#!/usr/bin/env python3
"""Prepare isolated D143 tests from exact local sources, 2026-11-13.
Inputs Case C worktree and retained power harness; outputs new harness/scratch,
local fairscape extraction. No network, dependency installation or model call.
"""
from pathlib import Path
import subprocess,tarfile
W=Path(__file__).resolve().parents[2];E=W.parent;R=E/'codex-development-efficiency-20261111';S=E/'scratch-h2-run-limits-20261113'
S.mkdir(exist_ok=False)
source=(R/'scripts/adhoc/run_h2_power_proof_20261113.py').read_text()
source=source.replace('SCRATCH_BASE = EXECUTIONS / "scratch-h2-host-power-20261113"','SCRATCH_BASE = EXECUTIONS / "scratch-h2-run-limits-20261113"')
source=source.replace('if tree not in (SCRIPT_ROOT, POWER_ROOT):','if tree not in (SCRIPT_ROOT, POWER_ROOT, Path('+repr(str(W))+')):')
(R/'scripts/adhoc/run_h2_run_limits_tests_20261113.py').write_text(source)
sub=subprocess.check_output(['/usr/bin/git','ls-tree','HEAD','fairscape_models'],cwd=W).decode().split()[2]
archive=S/'fairscape.tar'
subprocess.run(['/usr/bin/git','archive','--format=tar','--output='+str(archive),sub],cwd=E.parent/'data-sheets-schema/fairscape_models',check=True)
with tarfile.open(archive) as stream:stream.extractall(W/'fairscape_models',filter='data')
print(S)
