#!/usr/bin/env python3
"""D73/#5212 review fixes: offline pytest with external basetemps, 2026-10-31.

Inputs: pytest arguments and --basetemp under the owner's scratch-5212fix.
Outputs: a phase/collection/environment report in that basetemp. Supports the
requested xdist shard; all workers inherit the OS network/write sandbox.
"""
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / "scratch-5212fix"
args = sys.argv[1:]
base = Path(args[args.index("--basetemp") + 1]).resolve()
assert base.is_relative_to(SCRATCH) and base != SCRATCH
assert not base.exists(), "preserve prior validation evidence"
sys.path.insert(0, str(Path(__file__).resolve().parent))
from d41_legacy_controls_20261029 import bootstrap

environment = bootstrap(ROOT, SCRATCH)
tempfile.tempdir = str(SCRATCH / "temporary")
os.environ.pop("PYTEST_DISABLE_PLUGIN_AUTOLOAD", None)
venv = Path(sys.executable).parent.parent
os.environ.update(VIRTUAL_ENV=str(venv), PATH=str(venv / "bin") + os.pathsep + os.environ["PATH"],
                  POETRY_VIRTUALENVS_CREATE="false", POETRY_CACHE_DIR=str(SCRATCH / "poetry"))
git_binary = shutil.which("git")
assert git_binary
environment["head"] = subprocess.check_output([git_binary, "rev-parse", "HEAD"], text=True).strip()
environment["tracked_diff"] = subprocess.check_output([git_binary, "diff", "HEAD", "--stat"], text=True)
environment["latch_journal_sha256"] = hashlib.sha256((ROOT / "src/data_sheets_schema/latch_journal.py").read_bytes()).hexdigest()
environment["regression_test_sha256"] = hashlib.sha256((ROOT / "tests/test_d68_legacy_readonly.py").read_bytes()).hexdigest()
binary_dir = SCRATCH / "offline-bin"
binary_dir.mkdir(exist_ok=True)
wrapper = binary_dir / "git"
wrapper.write_text((ROOT / "scripts/adhoc/d68_local_git_20261030.sh").read_text().replace(
    "__D68_GIT_BINARY__", shlex.quote(git_binary)))
wrapper.chmod(0o700)
os.environ["PATH"] = str(binary_dir) + os.pathsep + os.environ["PATH"]

def no_remote_git(event, arguments):
    if event == "subprocess.Popen" and Path(os.fsdecode(arguments[0])).name == "git":
        argv = arguments[1]
        if isinstance(argv, (list, tuple)) and any(word in {"fetch", "ls-remote", "push", "pull"} for word in argv[1:]):
            raise RuntimeError("D73 validation forbids remote Git commands")

sys.addaudithook(no_remote_git)
import pytest

class Observe:
    def __init__(self):
        self.reports, self.errors, self.selected, self.workers = [], [], [], {}

    def pytest_collection_finish(self, session):
        self.selected = [item.nodeid for item in session.items]

    @pytest.hookimpl(optionalhook=True)
    def pytest_xdist_node_collection_finished(self, node, ids):
        self.workers[node.gateway.id] = list(ids)
        if self.selected:
            assert self.selected == list(ids), "worker collections differ"
        self.selected = list(ids)

    def pytest_collectreport(self, report):
        if report.failed:
            self.errors.append({"nodeid": report.nodeid, "message": str(report.longrepr)})

    def pytest_runtest_logreport(self, report):
        self.reports.append({"nodeid": report.nodeid, "when": report.when,
            "outcome": report.outcome, "duration": report.duration,
            **({"message": str(report.longrepr)} if report.failed else {})})

observer = Observe()
code = pytest.main([*args, "-p", "no:cacheprovider"], plugins=[observer])
base.mkdir(exist_ok=True, parents=True)
destination = base / "d73-result.json"
destination.write_text(json.dumps({"exit_code": int(code), "command": args,
    "environment": environment, "selected": observer.selected, "reports": observer.reports,
    "collection_errors": observer.errors, "worker_collections": observer.workers}, indent=2) + "\n")
assert destination.stat().st_size
raise SystemExit(code)
