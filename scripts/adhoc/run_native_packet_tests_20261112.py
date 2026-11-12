#!/usr/bin/env python3
"""Offline G07 packet and capture test runner, 2026-11-12.

Purpose: validate the assigned branch or its exact private packet composition.
Inputs: this assigned worktree, a physical dependency venv, explicit tests/ nodes.
Outputs: new sibling scratch-h3-packet-builder-20261112/tests cohorts, with isolated venv, logs, JUnit, origin/network and cleanup evidence.
Adapted from run_native_u3a_tests_20261107.py; no provider or real native binary.
Invoke with the dependency venv Python -S -P -B. The caller runs cohorts serially.
"""
from __future__ import annotations

import argparse
import errno
import hashlib
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time
import venv


SCRIPT_ROOT = Path(__file__).resolve().parents[2]
ROOT = SCRIPT_ROOT
if SCRIPT_ROOT.name != "codex-native-packet-builder-20261112":
    raise RuntimeError("runner helper must stay in the assigned branch")


def execution_root(source_root):
    """Keep the real quiet-window location when a source archive is nested."""
    candidates = [path for path in source_root.parents if path.name == "d4d-executions"]
    if (len(candidates) != 1 or candidates[0] != candidates[0].resolve(strict=True)
            or not (candidates[0] / "plans").is_dir()):
        raise RuntimeError("source must be below the canonical d4d-executions root")
    return candidates[0]


EXECUTIONS = execution_root(ROOT)
SCRATCH_BASE = EXECUTIONS / "scratch-h3-packet-builder-20261112"
SCRATCH = SCRATCH_BASE / "tests"
LOCK = EXECUTIONS / "plans/native_quiet_window.lock"
DEFAULT_DEADLINE = 3600
NATIVE_PATHS = (
    "/Users/marcin/.local/bin/claude", "/Users/marcin/.local/bin/agy",
    "/Users/marcin/.nvm/versions/node/v22.16.0/bin/codex",
    "/Users/marcin/.nvm/versions/node/v22.16.0/bin/gemini",
    "/opt/homebrew/bin/claude", "/opt/homebrew/bin/codex",
    "/opt/homebrew/bin/gemini", "/usr/local/bin/claude",
    "/usr/local/bin/codex", "/usr/local/bin/gemini",
)


def sandbox_profile():
    """Deny network/native execution and writes outside source plus sibling scratch."""
    paths = sorted({path for item in NATIVE_PATHS
                    for path in (item, str(Path(item).resolve()))})
    return (
        '(version 1)\n(allow default)\n(deny network*)\n'
        '(deny process-exec (regex #"/(claude|codex|gemini|agy)(/|$)"))\n'
        '(deny process-exec\n'
        + ''.join('  (literal ' + json.dumps(path) + ')\n' for path in paths)
        + ')\n(deny file-write* (require-all\n'
        '  (require-not (subpath ' + json.dumps(str(ROOT)) + '))\n'
        '  (require-not (subpath ' + json.dumps(str(SCRATCH_BASE)) + '))\n'
        '  (require-not (literal "/dev/null"))\n'
        '  (require-not (literal "/dev/tty"))))\n'
    )


def save(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def clean_environment(out, interpreter_directory):
    # Allowlist before child Python startup, including collection/module fixtures.
    return {
        "PATH": str(interpreter_directory) + ":/usr/bin:/bin:/usr/sbin:/sbin",
        "HOME": str(out / "home"), "TMPDIR": str(out / "tmp"),
        "LANG": "en_US.UTF-8", "PYTHONNOUSERSITE": "1",
        "PYTHONSAFEPATH": "1", "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONPATH": str(ROOT / "src"),
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "PYTEST_ADDOPTS": "",
        "UV_OFFLINE": "1", "PIP_NO_INDEX": "1", "GIT_NO_LAZY_FETCH": "1",
        "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_SYSTEM": "/dev/null",
        "GIT_OPTIONAL_LOCKS": "0",
    }


def dependency_site():
    if not (sys.flags.no_site and sys.flags.safe_path and sys.dont_write_bytecode):
        raise RuntimeError("invoke parent with the dependency venv Python -S -P -B")
    prefix = Path(sys.executable).absolute().parent.parent
    site = prefix / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages"
    if not (prefix / "pyvenv.cfg").is_file() or not site.is_dir() or site.resolve() != site:
        raise RuntimeError("expected physical venv dependency directory")
    return site


def origin_witness():
    from tests.utils.native_test_environment import origin_witness as witness
    return witness(ROOT)


def network_witness():
    sock = socket.socket()
    try:
        try:
            sock.bind(("127.0.0.1", 0))
        except OSError as exc:
            if exc.errno != errno.EPERM:
                raise
            return {"network_bind_denied": True, "errno": exc.errno,
                    "pid": os.getpid(), "scope": "inherited OS deny network*"}
        raise RuntimeError("OS network denial self-check unexpectedly bound a socket")
    finally:
        sock.close()


def worker(args):
    out = args.out.resolve(strict=True)
    if out == SCRATCH or not out.is_relative_to(SCRATCH):
        raise RuntimeError("test output must stay under the assigned sibling scratch root")
    if not (sys.flags.no_user_site and sys.flags.safe_path and sys.dont_write_bytecode):
        raise RuntimeError("test child requires no-user-site, safe-path and no-bytecode")
    if Path(sys.prefix).resolve() != out / "venv":
        raise RuntimeError("test child is outside the isolated evidence venv")
    save(out / "network.json", network_witness())
    save(out / "origins-before.json", origin_witness())
    # Ordinary child startup is intentionally tested: it must not execute the
    # dependency venv's .pth files or fall back to its editable project checkout.
    witness = subprocess.run(
        [sys.executable, "-P", "-B", str(Path(__file__).resolve()), "--tree", str(ROOT), "--child-check"],
        cwd=ROOT, env=os.environ.copy(), capture_output=True, text=True,
        timeout=30, check=True)
    save(out / "subprocess-origins.json", json.loads(witness.stdout))
    if args.scanner:
        command = [sys.executable, '-P', '-B', str(ROOT / '.claude/skills/d4d-generation-specificity-audit/scan.py'),
                   '--root', str(ROOT), '--report', str(out / 'scanner.md'), '--json', str(out / 'scanner.json'), '--full-json']
        save(out / 'scanner-command.json', {'args': command})
        code = subprocess.call(command, cwd=ROOT, env=os.environ.copy())
        save(out / 'origins-after.json', origin_witness())
        save(out / 'worker-outcome.json', {'returncode': code, 'source_origin_checks_passed': True})
        return code
    import pytest
    command = ["-q", "-o", "addopts=", "-p", "no:cacheprovider",
               "--basetemp", str(out / "cases"),
               "--junitxml", str(out / "pytest.xml")]
    if args.workers:
        command += ["-p", "xdist.plugin", "-n", str(args.workers)]
    if args.collect_only:
        command += ["--collect-only"]
    command += args.nodes
    save(out / "pytest-command.json", {"args": command})
    code = int(pytest.main(command))
    save(out / "origins-after.json", origin_witness())
    save(out / "worker-outcome.json", {"returncode": code,
         "source_origin_checks_passed": True})
    return code


def make_test_venv(out, dependencies):
    location = out / "venv"
    venv.EnvBuilder(with_pip=False, symlinks=True).create(location)
    site = location / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages"
    paths = [ROOT / "src", ROOT]
    fairscape = ROOT / "fairscape_models"
    if (fairscape / "fairscape_models").is_dir():
        paths.append(fairscape)
    paths.append(dependencies)
    if any("\n" in str(path) or "\r" in str(path) for path in paths):
        raise RuntimeError("newline in bootstrap path")
    pth = site / "native_integration_paths.pth"
    pth.write_text("".join(str(path) + "\n" for path in paths), encoding="utf-8")
    # The controlled sitecustomize shadows any dependency-site customization.
    # Plain .pth path entries do not recursively process that site's .pth files.
    custom = site / "sitecustomize.py"
    custom.write_text("# Native integration test environment; no external site hooks.\n", encoding="utf-8")
    python = location / "bin/python"
    save(out / "bootstrap.json", {
        "dependency_site": str(dependencies), "test_python": str(python),
        "underlying_python": str(python.resolve()),
        "underlying_python_sha256": digest(python.resolve()),
        "paths": [str(path) for path in paths],
        "files": {str(path): digest(path) for path in
                  (location / "pyvenv.cfg", pth, custom)},
        "scope": "same underlying interpreter, new test-only prefix and registered interpreter path; dependency .pth files are not executed"})
    return python


class OwnedProcesses:
    """Track observed descendants by PID/creation time; never signal reused PIDs."""
    def __init__(self, psutil, pid):
        self.psutil = psutil
        root = psutil.Process(pid)
        self.known = {(pid, root.create_time())}
        self.errors = []

    def live(self):
        result = []
        for pid, created in tuple(self.known):
            try:
                process = self.psutil.Process(pid)
                if process.create_time() == created and process.is_running() and process.status() != self.psutil.STATUS_ZOMBIE:
                    result.append(process)
            except self.psutil.NoSuchProcess:
                pass
            except self.psutil.Error as exc:
                self.errors.append(type(exc).__name__)
        return result

    def observe(self):
        for process in self.live():
            try:
                for child in process.children(recursive=True):
                    try:
                        self.known.add((child.pid, child.create_time()))
                    except self.psutil.NoSuchProcess:
                        pass
            except self.psutil.NoSuchProcess:
                pass
            except self.psutil.Error as exc:
                self.errors.append(type(exc).__name__)

    def signal(self, number):
        self.observe()
        for process in self.live():
            try:
                process.send_signal(number)
            except self.psutil.NoSuchProcess:
                pass
            except self.psutil.Error as exc:
                self.errors.append(type(exc).__name__)


class QuietWindow:
    """Detect acquisition each runner tick; poll a held lock at most each 60 s."""
    def __init__(self, lock, clock=None):
        self.lock = lock
        self.clock = time.monotonic if clock is None else clock
        self.paused = False
        self.next_removal_check = 0.0

    def update(self, owned):
        if self.paused and self.clock() < self.next_removal_check:
            return
        requested = self.lock.exists()
        if requested:
            # Start the interval after the actual filesystem observation.
            self.next_removal_check = self.clock() + 60
        if requested and not self.paused:
            owned.signal(signal.SIGSTOP)
            self.paused = True
        elif self.paused and not requested:
            owned.signal(signal.SIGCONT)
            self.paused = False


def parent(args):
    if LOCK.exists():
        raise SystemExit("quiet window active; no tests started")
    dependencies = dependency_site()
    out = args.out.absolute()
    if SCRATCH != SCRATCH.resolve():
        raise ValueError("test output root must not traverse a symlink")
    if out != out.resolve() or out.parent != SCRATCH:
        raise ValueError("output must be a new direct child of the assigned test root")
    SCRATCH.mkdir(parents=True, exist_ok=True)
    out.mkdir(mode=0o700, parents=False, exist_ok=False)
    (out / "home").mkdir(); (out / "tmp").mkdir()
    python = make_test_venv(out, dependencies)
    env = clean_environment(out, python.parent)
    profile = out / "network-denied.sb"
    profile.write_text(sandbox_profile(), encoding="utf-8")
    command = ["/usr/bin/sandbox-exec", "-f", str(profile), str(python),
               "-P", "-B", str(Path(__file__).resolve()), "--worker",
               "--tree", str(ROOT), "--out", str(out), "--workers", str(args.workers),
               "--timeout-seconds", str(args.timeout_seconds)]
    if args.collect_only:
        command.append("--collect-only")
    if args.scanner:
        command += ["--scanner"]
    command += args.nodes
    commit = subprocess.check_output(["git", "--no-replace-objects", "rev-parse", "HEAD"],
                                     cwd=ROOT, env=env, text=True).strip()
    save(out / "plan.json", {"command": command, "source_root": str(ROOT),
         "source_commit": commit, "runner_sha256": digest(Path(__file__)),
         "scratch_root": str(SCRATCH), "quiet_window_lock": str(LOCK),
         "sandbox_sha256": digest(profile), "environment": env,
         "deadline_seconds": args.timeout_seconds, "workers": args.workers,
         "scope": "offline synthetic validation; no native binary/provider permission"})
    # Parent process observation is outside the network-denied test subtree.
    # Load only the physical dependency path, never site.addsitedir/.pth hooks.
    sys.path.append(str(dependencies))
    import psutil
    if LOCK.exists():
        save(out / "outcome.json", {"status": "blocked_quiet_window", "launched": False})
        return 75
    started = time.monotonic()
    child = None; owned = None; interrupted = None
    forced_cleanup = False
    quiet = QuietWindow(LOCK)
    with (out / "pytest.log").open("xb") as log:
        try:
            child = subprocess.Popen(command, cwd=ROOT, env=env, stdout=log,
                                     stderr=subprocess.STDOUT, start_new_session=True)
            owned = OwnedProcesses(psutil, child.pid)
            while child.poll() is None:
                owned.observe()
                if time.monotonic() - started >= args.timeout_seconds:
                    interrupted = "deadline"
                    break
                quiet.update(owned)
                time.sleep(0.25)
        except BaseException as exc:
            interrupted = type(exc).__name__
        finally:
            if owned is not None:
                owned.observe()
                if quiet.paused:
                    owned.signal(signal.SIGCONT)
                survivors = owned.live()
                if survivors:
                    forced_cleanup = True
                    owned.signal(signal.SIGTERM)
                    until = time.monotonic() + 5
                    while owned.live() and time.monotonic() < until:
                        time.sleep(0.1)
                    if owned.live():
                        owned.signal(signal.SIGKILL)
                if child is not None:
                    try:
                        child.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        interrupted = interrupted or "cleanup_timeout"
            elif child is not None and child.poll() is None:
                # Tracker construction failed. Stop only the child handle we
                # created; record uncertainty rather than certifying cleanup.
                forced_cleanup = True
                child.terminate()
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait(timeout=5)
    survivors = [] if owned is None else [p.pid for p in owned.live()]
    errors = [] if owned is None else owned.errors
    worker_path = out / "worker-outcome.json"
    worker = json.loads(worker_path.read_bytes()) if worker_path.exists() else None
    completed = child is not None and child.returncode is not None and child.returncode >= 0 and worker is not None
    cleanup_verified = completed and not survivors and not errors and interrupted is None and not forced_cleanup
    code = 124 if interrupted == "deadline" else (125 if not cleanup_verified else child.returncode)
    outcome = {"returncode": code, "worker_returncode": None if child is None else child.returncode,
        "worker": worker, "interrupted": interrupted, "seconds": time.monotonic() - started,
        "cleanup_verified": cleanup_verified, "observed_surviving_pids": survivors,
        "forced_cleanup": forced_cleanup,
        "observation_errors": errors,
        "observed_processes": [] if owned is None else sorted(owned.known),
        "cleanup_scope": "observed descendants by PID and creation time; no proof about never-observed orphans"}
    save(out / "outcome.json", outcome)
    print(json.dumps(outcome), flush=True)
    return int(code)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tree", type=Path, required=True)
    parser.add_argument("--scanner", action="store_true")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--workers", type=int, choices=(0, 1, 2), default=0)
    parser.add_argument("--collect-only", action="store_true")
    parser.add_argument("--timeout-seconds", type=int, default=DEFAULT_DEADLINE,
                        help="bounded cohort wall time, 1 to 14400 seconds; default 3600")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--child-check", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("nodes", nargs="*")
    args = parser.parse_args()
    global ROOT
    tree = args.tree.absolute()
    if tree.resolve(strict=True) != tree:
        parser.error('source tree must be a physical path')
    if tree != SCRIPT_ROOT:
        if tree.name != 'tree' or tree.parent.parent != SCRATCH_BASE:
            parser.error('only assigned branch or private G07 composition is allowed')
        manifest = json.loads((tree.parent / 'composition.json').read_bytes())
        if manifest.get('status') != 'composed_not_tested' or manifest.get('tree') != str(tree):
            parser.error('private composition manifest is not ready')
        commit = subprocess.check_output(['/usr/bin/git', 'rev-parse', 'HEAD'], cwd=tree, text=True).strip()
        if commit != manifest['composition_commit']:
            parser.error('private source HEAD differs from composition manifest')
        for row in manifest['packets']:
            if digest(tree / row['path']) != row['postimage_sha256']:
                parser.error('private protected postimage changed')
    ROOT = tree
    if args.child_check:
        print(json.dumps({"origins": origin_witness(), "network": network_witness()}))
        return 0
    if not 1 <= args.timeout_seconds <= 14400:
        parser.error("--timeout-seconds must be between 1 and 14400")
    if args.out is None or (not args.nodes and not args.scanner) or (args.nodes and args.scanner):
        parser.error("--out and either explicit tests/ nodes or --scanner are required")
    for node in args.nodes:
        path = node.split("::", 1)[0]
        if path != "tests" and (not path.startswith("tests/") or ".." in Path(path).parts):
            parser.error("only repository-relative tests/ nodes are supported")
    return worker(args) if args.worker else parent(args)


if __name__ == "__main__":
    raise SystemExit(main())
