#!/usr/bin/env python3
"""Run U3-D tests offline without editable-install source leakage, 2026-11-07.

Inputs: this checkout, the invoking physical venv, explicit tests/ nodes.
Outputs: a NEW external evidence directory with isolated test venv, logs,
JUnit, source/bootstrap/network witnesses and a bounded execution outcome.
Copied from the committed U3-A runner, with explicit native executable path
denial added. No native executable or provider is invoked. Test fixtures must
remain synthetic. Run with the dependency venv's Python using -S -P -B.
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


ROOT = Path(__file__).resolve().parents[2]
# The same launcher is retained in the composed scratch archive, which is
# nested below scratch-native-u3d. Never silently check a different lock there.
_executions = [path for path in ROOT.parents if path.name == "d4d-executions"]
if len(_executions) != 1:
    raise RuntimeError("expected one enclosing d4d-executions directory")
EXECUTIONS = _executions[0]
LOCK = EXECUTIONS / "plans/native_quiet_window.lock"
DEADLINE = 3600
NATIVE_PATHS = (
    '/Users/marcin/.local/bin/claude',
    '/Users/marcin/.local/bin/agy',
    '/Users/marcin/.nvm/versions/node/v22.16.0/bin/codex',
    '/Users/marcin/.nvm/versions/node/v22.16.0/bin/gemini',
    '/opt/homebrew/bin/claude', '/usr/local/bin/claude',
)


def locked():
    return os.path.lexists(LOCK)


def sandbox_profile():
    # Read-only path resolution does not invoke or authenticate any executable.
    # Deny both named routes and physical targets. Synthetic Python test peers
    # are separate fixtures, never a real native executable under another label.
    paths = sorted({path for item in NATIVE_PATHS for path in (item, str(Path(item).resolve()))})
    return ('(version 1)\n(allow default)\n(deny network*)\n(deny process-exec\n'
            + ''.join('  (literal ' + json.dumps(path) + ')\n' for path in paths) + ')\n')


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
        "PYTHONPATH": str(ROOT / "src") + os.pathsep + str(ROOT),
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "PYTEST_ADDOPTS": "",
        "UV_OFFLINE": "1", "PIP_NO_INDEX": "1", "GIT_NO_LAZY_FETCH": "1",
        "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_SYSTEM": "/dev/null",
    }


def dependency_site():
    if not (sys.flags.no_site and sys.flags.safe_path and sys.dont_write_bytecode):
        raise RuntimeError("invoke parent with the dependency venv Python -S -P -B")
    prefix = Path(sys.executable).absolute().parent.parent
    site = prefix / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages"
    if not (prefix / "pyvenv.cfg").is_file() or not site.is_dir() or site.resolve() != site:
        raise RuntimeError("expected physical venv dependency directory")
    return site


def source_evidence(root, out, env):
    """Bind tracked edits and nonignored untracked bytes to the test launch.

    This is a prelaunch snapshot, not a claim that concurrent source edits are
    safe. Status retains Git's filename quoting; the NUL-delimited inventory
    separately handles names containing newlines. Symlinks bind link text and
    are never followed into a different checkout.
    """
    def git(*args):
        return subprocess.check_output(['git', *args], cwd=root, env=env)

    tracked = git('diff', '--binary', 'HEAD')
    status = git('status', '--porcelain', '--untracked-files=all')
    names = git('ls-files', '--others', '--exclude-standard', '-z')
    files = []
    for raw_name in names.split(b'\0'):
        if not raw_name:
            continue
        name = os.fsdecode(raw_name)
        path = root / name
        if path.is_symlink():
            content = os.fsencode(os.readlink(path))
            kind = 'symlink'
        elif path.is_file():
            content = path.read_bytes()
            kind = 'file'
        else:
            raise RuntimeError('cannot snapshot untracked path: ' + name)
        files.append({'path': name, 'kind': kind, 'size': len(content),
                      'sha256': hashlib.sha256(content).hexdigest()})
    (out / 'tested.diff').write_bytes(tracked)
    (out / 'tested.status').write_bytes(status)
    save(out / 'tested-untracked.json', {
        'scope': 'git ls-files --others --exclude-standard; ignored caches excluded',
        'files': files})
    return {'tested_diff_sha256': digest(out / 'tested.diff'),
            'tested_status_sha256': digest(out / 'tested.status'),
            'tested_untracked_sha256': digest(out / 'tested-untracked.json')}


def origin_witness():
    import data_sheets_schema
    package = ROOT / "src/data_sheets_schema"
    raw_paths = [str(path) for path in data_sheets_schema.__path__]
    paths = [str(Path(path).resolve()) for path in raw_paths]
    # Collection may repeat this checkout's src on sys.path; namespace packages
    # then repeat the same location. Preserve that evidence without admitting
    # an empty namespace or even one foreign location.
    if not paths or any(path != str(package) for path in paths):
        raise RuntimeError("mixed project namespace: " + repr(paths))
    editable = [repr(finder) for finder in sys.meta_path
                if "__editable__" in repr(finder)]
    if editable:
        raise RuntimeError("editable-install import finder is active")
    origins = {}
    for name, module in tuple(sys.modules.items()):
        if name != "data_sheets_schema" and not name.startswith("data_sheets_schema."):
            continue
        path = getattr(module, "__file__", None)
        if path is not None:
            resolved = Path(path).resolve()
            if not resolved.is_relative_to(package):
                raise RuntimeError("foreign project module: " + name + " " + str(resolved))
            origins[name] = str(resolved)
        for item in getattr(module, "__path__", ()):
            if not Path(item).resolve().is_relative_to(package):
                raise RuntimeError("foreign project subpackage: " + name)
    return {"python": sys.executable, "prefix": sys.prefix,
            "package_paths_raw": raw_paths,
            "package_paths": paths, "module_origins": origins,
            "sys_path": list(sys.path), "editable_finders": editable,
            "no_user_site": bool(sys.flags.no_user_site),
            "safe_path": bool(sys.flags.safe_path),
            "dont_write_bytecode": sys.dont_write_bytecode}


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
    if not (sys.flags.no_user_site and sys.flags.safe_path and sys.dont_write_bytecode):
        raise RuntimeError("test child requires no-user-site, safe-path and no-bytecode")
    if Path(sys.prefix).resolve() != out / "venv":
        raise RuntimeError("test child is outside the isolated evidence venv")
    save(out / "network.json", network_witness())
    save(out / "origins-before.json", origin_witness())
    # Ordinary child startup is intentionally tested: it must not execute the
    # dependency venv's .pth files or fall back to its editable project checkout.
    witness = subprocess.run(
        [sys.executable, "-P", "-B", str(Path(__file__).resolve()), "--child-check"],
        cwd=ROOT, env=os.environ.copy(), capture_output=True, text=True,
        timeout=30, check=True)
    save(out / "subprocess-origins.json", json.loads(witness.stdout))
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
    pth = site / "u3a_paths.pth"
    pth.write_text("".join(str(path) + "\n" for path in paths), encoding="utf-8")
    # The controlled sitecustomize shadows any dependency-site customization.
    # Plain .pth path entries do not recursively process that site's .pth files.
    custom = site / "sitecustomize.py"
    custom.write_text("# U3-A isolated test environment; no external site hooks.\n", encoding="utf-8")
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


def parent(args):
    if locked():
        raise SystemExit("quiet window active; no tests started")
    dependencies = dependency_site()
    out = args.out.absolute()
    if out != out.resolve() or not out.is_relative_to(EXECUTIONS):
        raise ValueError("output must be a new literal path under d4d-executions")
    if any((parent / ".git").exists() for parent in (out, *out.parents)
           if parent.is_relative_to(EXECUTIONS)):
        raise ValueError("evidence must be outside every source worktree")
    out.mkdir(mode=0o700, parents=False, exist_ok=False)
    (out / "home").mkdir(); (out / "tmp").mkdir()
    python = make_test_venv(out, dependencies)
    env = clean_environment(out, python.parent)
    profile = out / "network-denied.sb"
    profile.write_text(sandbox_profile(), encoding="utf-8")
    command = ["/usr/bin/sandbox-exec", "-f", str(profile), str(python),
               "-P", "-B", str(Path(__file__).resolve()), "--worker",
               "--out", str(out), "--workers", str(args.workers)]
    if args.collect_only:
        command.append("--collect-only")
    command += args.nodes
    commit = subprocess.check_output(["git", "--no-replace-objects", "rev-parse", "HEAD"],
                                     cwd=ROOT, env=env, text=True).strip()
    evidence = source_evidence(ROOT, out, env)
    save(out / "plan.json", {"command": command, "source_root": str(ROOT),
         **evidence,
         "source_commit": commit, "runner_sha256": digest(Path(__file__)),
         "sandbox_sha256": digest(profile), "environment": env,
         "deadline_seconds": DEADLINE, "workers": args.workers,
         "scope": "offline synthetic validation; no native binary/provider permission"})
    # Parent process observation is outside the network-denied test subtree.
    # Load only the physical dependency path, never site.addsitedir/.pth hooks.
    sys.path.append(str(dependencies))
    import psutil
    if locked():
        save(out / "outcome.json", {"status": "blocked_quiet_window", "launched": False})
        return 75
    started = time.monotonic()
    child = None; owned = None; interrupted = None; paused = False
    forced_cleanup = False
    with (out / "pytest.log").open("xb") as log:
        try:
            child = subprocess.Popen(command, cwd=ROOT, env=env, stdout=log,
                                     stderr=subprocess.STDOUT, start_new_session=True)
            owned = OwnedProcesses(psutil, child.pid)
            while child.poll() is None:
                owned.observe()
                if time.monotonic() - started >= DEADLINE:
                    interrupted = "deadline"
                    break
                requested = locked()
                if requested and not paused:
                    owned.signal(signal.SIGSTOP); paused = True
                elif paused and not requested:
                    owned.signal(signal.SIGCONT); paused = False
                time.sleep(60 if paused else 0.25)
        except BaseException as exc:
            interrupted = type(exc).__name__
        finally:
            if owned is not None:
                owned.observe()
                if paused:
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
    parser.add_argument("--out", type=Path)
    parser.add_argument("--workers", type=int, choices=(0, 1, 2), default=0)
    parser.add_argument("--collect-only", action="store_true")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--child-check", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("nodes", nargs="*")
    args = parser.parse_args()
    if args.child_check:
        print(json.dumps({"origins": origin_witness(), "network": network_witness()}))
        return 0
    if args.out is None or not args.nodes:
        parser.error("--out and at least one explicit tests/ node are required")
    for node in args.nodes:
        path = node.split("::", 1)[0]
        if path != "tests" and (not path.startswith("tests/") or ".." in Path(path).parts):
            parser.error("only repository-relative tests/ nodes are supported")
    return worker(args) if args.worker else parent(args)


if __name__ == "__main__":
    raise SystemExit(main())
