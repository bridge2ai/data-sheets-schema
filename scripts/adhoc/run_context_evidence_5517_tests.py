"""Offline #5517 focused tests with quiet lock and 3600s deadline, 2026-11-08.

Inputs: local source/tests and existing Python environment. Outputs: log/XML in
the authorized scratch root. No native agent executable or provider is invoked.
"""
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / "scratch-codex-5517"
LOCK = ROOT.parent / "plans/native_quiet_window.lock"
assert not LOCK.exists(), "quiet-window lock exists; do not start pytest"
mode = sys.argv[1]
assert mode in {"canary", "focused", "literal", "evaluation"}
label = mode + ("-" + sys.argv[2] if len(sys.argv) > 2 else "")
assert label.replace("-", "").isalnum()
selection = {
    "canary": ["tests/test_context_evidence_verbatim.py::test_literal_check_does_not_accept_terms_or_casefolding"],
    "focused": ["tests/test_evaluation_context_files.py", "tests/test_context_evidence_verbatim.py::test_literal_check_does_not_accept_terms_or_casefolding"],
    "literal": ["tests/test_context_evidence_verbatim.py"],
    "evaluation": ["tests/test_evaluation/test_general_context.py", "tests/test_evaluation/test_semantic_context_scope.py"],
}[mode]
env = dict(os.environ, PYTHONPATH=f"{ROOT}/src:{ROOT}", PYTHONDONTWRITEBYTECODE="1", TMPDIR=str(SCRATCH), TMP=str(SCRATCH), TEMP=str(SCRATCH))
command = [sys.executable, "-m", "pytest", *selection, "-q", "-n", "2", "-p", "no:cacheprovider", "--basetemp", str(SCRATCH / f"pytest-{label}"), "--junitxml", str(SCRATCH / f"{label}.xml")]
with (SCRATCH / f"{label}.log").open("x") as log:
    log.write(f"Interpreter: {sys.executable}\nCommand: {command!r}\nDeadline: 3600 seconds\n")
    log.flush()
    process = subprocess.Popen(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    deadline = time.monotonic() + 3600
    while process.poll() is None:
        if time.monotonic() >= deadline or LOCK.exists():
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
            log.write("Stopped for deadline or quiet-window lock.\n")
            sys.exit(124)
        time.sleep(1)
print(f"{mode}: exit {process.returncode}; log {SCRATCH / (label + '.log')}")
sys.exit(process.returncode)
