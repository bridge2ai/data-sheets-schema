#!/usr/bin/env python3
"""D68-D70/#5212 serial offline pytest launcher, 2026-10-30.

Inputs: pytest args; existing dependency environment. Output: pytest results,
JSON phase ledger in --basetemp. Provider credentials removed before imports;
network audit inherited from retained f8 driver; launch under sandbox profile
for subprocess network and protected-path enforcement. No batch concurrency.
"""
import os
from pathlib import Path
import sys
import json
import tempfile
import subprocess
import shlex
import shutil

sys.path.insert(0, str(Path(__file__).resolve().parent))
from d41_legacy_controls_20261029 import bootstrap

root = Path(__file__).resolve().parents[2]
args = sys.argv[1:]
base = Path(args[args.index("--basetemp") + 1]).resolve()
assert base.is_relative_to(root) and "d4d-executions" in base.parts
base.parent.mkdir(parents=True, exist_ok=True)
environment = bootstrap(root, base.parent)
notes_controls = any(arg.startswith("notes/") for arg in args)
if notes_controls:
    # CI's pinned transport probe rejects a bytecode prefix. Preserve its
    # no-bytecode environment and explicit import paths without editing notes.
    extra = [root / "notes/matched_cborg_2026-09-13",
             root / "notes/matched_cborg_2026-09-13/native_controls",
             root / "notes/matched_cborg_2026-09-13/evaluation_controls"]
    sys.path[:0] = list(map(str, extra))
    os.environ["PYTHONPATH"] += os.pathsep + os.pathsep.join(map(str, extra))
    os.environ.pop("PYTHONPYCACHEPREFIX", None)
    sys.pycache_prefix = None
environment["notes_controls"] = notes_controls
git_binary = shutil.which("git")
assert git_binary
def no_remote_git(event, arguments):
    if event == "subprocess.Popen" and Path(os.fsdecode(arguments[0])).name == "git":
        argv = arguments[1]
        if isinstance(argv, (list, tuple)) and any(word in {"fetch", "ls-remote", "push", "pull"} for word in argv[1:]):
            raise RuntimeError("D68 offline validation refuses Git remote commands, including local fixture remotes")
sys.addaudithook(no_remote_git)
environment["head"] = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
os.environ.pop("PYTEST_DISABLE_PLUGIN_AUTOLOAD", None)
venv = Path(sys.executable).parent.parent
os.environ.update(VIRTUAL_ENV=str(venv), PATH=str(venv / "bin") + os.pathsep + os.environ["PATH"],
                  POETRY_VIRTUALENVS_CREATE="false", POETRY_CACHE_DIR=str(base.parent / "poetry"))
import pytest

class Observe:
    def __init__(self):
        self.reports = []
        self.errors = []
        self.selected = []

    @pytest.hookimpl(trylast=True)
    def pytest_configure(self, config):
        # All live test scratch belongs to the directory excluded by the
        # checkout-preservation fixture, including child-process bytecode.
        scratch = config._tmp_path_factory.getbasetemp()
        temporary = scratch / "temporary"
        temporary.mkdir()
        binary_dir = scratch / "offline-bin"
        binary_dir.mkdir()
        wrapper = binary_dir / "git"
        wrapper.write_text((root / "scripts/adhoc/d68_local_git_20261030.sh").read_text().replace(
            "__D68_GIT_BINARY__", shlex.quote(git_binary)))
        wrapper.chmod(0o700)
        tempfile.tempdir = str(temporary)
        os.environ.update(TMPDIR=str(temporary), PYTHONPYCACHEPREFIX=str(scratch / "pycache"),
                          POETRY_CACHE_DIR=str(scratch / "poetry"), MPLCONFIGDIR=str(scratch / "matplotlib"),
                          PATH=str(binary_dir) + os.pathsep + os.environ["PATH"])
        if notes_controls:
            os.environ.pop("PYTHONPYCACHEPREFIX", None)

    def pytest_collection_finish(self, session):
        self.selected = [item.nodeid for item in session.items]

    def pytest_collectreport(self, report):
        if report.failed:
            self.errors.append({"nodeid": report.nodeid, "message": str(report.longrepr)})

    def pytest_runtest_logreport(self, report):
        self.reports.append({"nodeid": report.nodeid, "when": report.when, "outcome": report.outcome,
                             **({"message": str(report.longrepr)} if report.failed else {})})

observer = Observe()
code = pytest.main([*args, "-p", "no:cacheprovider"], plugins=[observer])
base.mkdir(exist_ok=True, parents=True)
(base / "d68-result.json").write_text(json.dumps({"exit_code": int(code), "command": args,
    "environment": environment, "selected": observer.selected, "reports": observer.reports,
    "collection_errors": observer.errors}, indent=2))
raise SystemExit(code)
