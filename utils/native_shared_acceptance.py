"""Opt-in retention runner for two unchanged synthetic public v2 tests (2026-11-08).

Recovered by behavior from de3cc1b23 for native U5 preparation. No execution,
scientific, timing or CI acceptance is certified. The actual tests own their
assertions. They run ordinary Python peers with invented authority, never an
actual native binary. This runner must itself run inside an enclosing
network-denied sandbox; credential removal alone does not establish isolation.
The caller explicitly acknowledges that precondition and supplies the shared
quiet-window lock. A present lock causes refusal, never removal or takeover.
"""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import shutil
import signal
import stat
import subprocess
import sys
import tarfile
import time
import xml.etree.ElementTree as ET


NODES = (
    ("neutral", "tests/test_native_shared_execution.py::test_actual_public_correction_three_workers_and_saved_completion"),
    ("omission", "tests/test_native_shared_execution_variant.py::test_actual_public_merged_omissions_and_all_chunk_statuses"),
)
ORIGINS = (
    "data_sheets_schema.native_shared_selection", "data_sheets_schema.native_shared_receipts",
    "data_sheets_schema.native_shared_capture", "data_sheets_schema.native_execution_authority_v2",
    "data_sheets_schema.native_execution_registration_v2",
    "data_sheets_schema.native_shared_controller_orchestration",
    "data_sheets_schema.native_shared_registration_orchestration",
    "data_sheets_schema.native_shared_execution_orchestration",
)
BOOTSTRAP = """import importlib,json,pathlib,sys
root=pathlib.Path.cwd().resolve()
origins={}
for name in %r:
    path=pathlib.Path(importlib.import_module(name).__file__).resolve()
    if not path.is_relative_to(root/'src'):
        raise ValueError('import outside selected source: '+name+' '+str(path))
    origins[name]=str(path)
print('IMPORT_ORIGINS_VERIFIED '+json.dumps(origins,sort_keys=True),flush=True)
import pytest
raise SystemExit(pytest.main(sys.argv[1:]))
""" % (ORIGINS,)

MAX_SOURCE_BYTES = 8 * 1024 * 1024 * 1024
MAX_SOURCE_ENTRIES = 200000
MAX_LOG_BYTES = 64 * 1024 * 1024
CHILD_SECONDS = 3600
GIT_SECONDS = 30
MAX_GIT_BYTES = 64 * 1024 * 1024


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def git(repo, *args):
    raw = subprocess.check_output(["git", "--no-pager", *args], cwd=repo,
        timeout=GIT_SECONDS, env=dict(child_environment(repo), GIT_OPTIONAL_LOCKS="0",
            GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_SYSTEM=os.devnull))
    if len(raw) > MAX_GIT_BYTES:
        raise ValueError("Git evidence byte bound exceeded")
    return raw.decode()


def quiet(lock):
    if os.path.lexists(lock):
        raise ValueError("quiet-window lock is held; no child may start or continue")


def child_environment(repo):
    """Keep a small environment; never inherit provider/account credentials."""
    allowed = ("PATH", "HOME", "TMPDIR", "TEMP", "TMP", "LANG", "LC_ALL", "SYSTEMROOT")
    result = {key: os.environ[key] for key in allowed if key in os.environ}
    result.update(PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=os.pathsep.join(
        str(repo / name) for name in ("src", "scripts", ".")),
        PYTEST_DISABLE_PLUGIN_AUTOLOAD="1")
    return result


def _regular_pin(path, size):
    """Stream the opened regular file; do not follow a replaced leaf link."""
    from utils.native_ci_evidence import directory
    sha, blob, total = hashlib.sha256(), hashlib.sha1(b"blob " + str(size).encode() + b"\0"), 0
    with directory(path.parent) as parent:
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
    before = os.fstat(fd)
    if not stat.S_ISREG(before.st_mode) or before.st_size != size:
        os.close(fd)
        raise ValueError("source file type or size changed before inspection")
    with os.fdopen(fd, "rb") as handle:
        while raw := handle.read(min(1024 * 1024, size - total + 1)):
            total += len(raw)
            if total > size:
                raise ValueError("source file grew during inspection")
            sha.update(raw); blob.update(raw)
        after = os.fstat(handle.fileno())
        witness = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mode, s.st_mtime_ns, s.st_ctime_ns)
        if total != size or witness(before) != witness(after) or witness(after) != witness(path.lstat()):
            raise ValueError("source file changed during inspection")
    return sha.hexdigest(), blob.hexdigest()


def source(repo):
    """Compare materialized tracked bytes/modes with Git; gitlinks stay opaque."""
    entries, valid, total = {}, True, 0
    for row in git(repo, "ls-tree", "-rz", "HEAD").split("\0"):
        if not row:
            continue
        meta, name = row.split("\t", 1)
        if len(entries) >= MAX_SOURCE_ENTRIES:
            raise ValueError("source entry bound exceeded")
        mode, kind, oid = meta.split()
        if kind == "commit":
            entries[name] = {"mode": mode, "gitlink": oid}
            continue
        path = repo / name
        if not path.exists() and not path.is_symlink():
            entries[name] = {"missing": True}
            valid = False
            continue
        # Refuse an altered ancestor before reading a source file through it.
        if any(parent.is_symlink() for parent in path.parents if parent != repo and parent.is_relative_to(repo)):
            raise ValueError("source ancestor is a symlink")
        if path.is_symlink():
            raw = os.fsencode(os.readlink(path))
            size, sha256 = len(raw), digest(raw)
            actual_blob = hashlib.sha1(b"blob " + str(size).encode() + b"\0" + raw).hexdigest()
        else:
            size = path.lstat().st_size
            if total + size > MAX_SOURCE_BYTES:
                raise ValueError("source byte bound exceeded")
            sha256, actual_blob = _regular_pin(path, size)
        total += size
        if total > MAX_SOURCE_BYTES:
            raise ValueError("source byte bound exceeded")
        actual_mode = "120000" if path.is_symlink() else (
            "100755" if path.stat().st_mode & 0o111 else "100644")
        valid = valid and actual_blob == oid and actual_mode == mode
        entries[name] = {"mode": actual_mode, "git_blob": actual_blob,
                         "sha256": sha256, "bytes": size}
    return {"head": git(repo, "rev-parse", "HEAD").strip(),
            "tree": git(repo, "rev-parse", "HEAD^{tree}").strip(),
            "tracked_exact": valid, "entries": entries}


def junit_pass(path, node):
    root = ET.parse(path).getroot()
    cases = list(root.iter("testcase"))
    return (len(cases) == 1 and cases[0].get("name") == node.split("::")[1]
            and not any(list(root.iter(tag)) for tag in ("failure", "error", "skipped"))
            and all(int(element.get(key, "0")) == 0 for element in root.iter()
                    for key in ("failures", "errors", "skipped")))


def _stop(child):
    """Refuse denied process-group cleanup; still attempt bounded leader reap."""
    refusal = None
    try:
        try:
            os.killpg(child.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    except OSError as exc:
        refusal = exc
    finally:
        try:
            child.wait(timeout=5)
        except subprocess.TimeoutExpired:
            if refusal is not None:
                raise refusal
            raise
    if refusal is not None:
        raise refusal


def pytest_child(repo, output, label, node, *, quiet_lock):
    base = output / "cases" / label
    if base.exists() or base.is_symlink():
        raise ValueError("pytest basetemp must be fresh")
    quiet(quiet_lock)
    command = [sys.executable, "-B", "-c", BOOTSTRAP, "-q", "-p", "no:cacheprovider",
               "-o", "addopts=",
               "--basetemp", str(base), "--junitxml", str(output / (label + ".xml")), node]
    save(output / (label + "-command.json"), {"argv": command, "cwd": str(repo),
        "timeout_seconds": CHILD_SECONDS, "quiet_lock": str(quiet_lock),
        "network_isolation": "required enclosing network-denied sandbox; not established by this helper",
        "credential_policy": "allowlisted child environment; no provider/account variables"})
    with (output / (label + ".log")).open("xb") as log:
        child = subprocess.Popen(command, cwd=repo, stdout=log, stderr=subprocess.STDOUT,
            env=child_environment(repo), start_new_session=True)
        started, wall = time.monotonic(), time.time()
        try:
            while child.poll() is None:
                quiet(quiet_lock)
                if max(time.monotonic() - started, time.time() - wall) >= CHILD_SECONDS:
                    raise TimeoutError("synthetic child exceeded 3600-second bound")
                if os.fstat(log.fileno()).st_size > MAX_LOG_BYTES:
                    raise ValueError("synthetic child log bound exceeded")
                time.sleep(0.1)
            if os.fstat(log.fileno()).st_size > MAX_LOG_BYTES:
                raise ValueError("synthetic child log bound exceeded")
            return child.returncode
        finally:
            _stop(child)


def run(repo, output, expected, *, quiet_lock, network_denied=False):
    output.mkdir(parents=True, exist_ok=False)
    (output / "cases").mkdir()
    outcome = {"status": "failed", "stages": {}, "scientific_acceptance": "not_assessed",
               "native_acceptance": "not_assessed", "scope": "synthetic ordinary-Python software tests only"}
    try:
        if network_denied is not True:
            raise ValueError("enclosing network-denied sandbox must be explicitly acknowledged")
        quiet(quiet_lock)
        baseline = source(repo)
        save(output / "source-before.json", baseline)
        if baseline["head"] != expected or not baseline["tracked_exact"]:
            raise ValueError("exact selected source head and tracked bytes required")
        if git(repo, "status", "--porcelain=v1", "--untracked-files=all"):
            raise ValueError("clean checkout required")
        save(output / "run.json", {"head": expected, "tree": baseline["tree"],
            "python": {"path": sys.executable, "version": sys.version},
            "packages": sorted((d.metadata.get("Name", ""), d.version)
                               for d in importlib.metadata.distributions()),
            "workflow": {k: os.environ.get(k) for k in
                         ("GITHUB_REPOSITORY", "GITHUB_REF", "GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT")},
            "environment_policy": "minimal allowlist; plugin autoload and inherited pytest options disabled",
            "quiet_lock": str(quiet_lock), "network_denied_sandbox": "caller-declared enclosing precondition"})
        for label, node in NODES:
            quiet(quiet_lock)
            code = pytest_child(repo, output, label, node, quiet_lock=quiet_lock)
            outcome["stages"][label] = {"returncode": code, "node": node}
            after = source(repo)
            save(output / ("source-after-" + label + ".json"), after)
            if after != baseline:
                raise ValueError("tracked source changed during " + label)
            if code != 0 or not junit_pass(output / (label + ".xml"), node):
                raise ValueError(label + " must pass exactly one unchanged test without skips")
            outcome["stages"][label]["passed"] = True
        outcome["status"] = "passed"
    except Exception as exc:
        outcome["error"] = type(exc).__name__ + ": " + str(exc)
    finally:
        if "omission" not in outcome["stages"]:
            outcome["omission_not_run"] = "neutral completion and source/JUnit checks did not pass"
        save(output / "outcome.json", outcome)
    return 0 if outcome["status"] == "passed" else 1


def inventory(root):
    from utils.native_ci_evidence import snapshot
    if root.is_symlink():
        raise ValueError("inventory root must not be a symlink")
    if not root.exists():
        return {}
    result = snapshot(root)
    result.pop(".")
    return result


def finalize(repo, output, expected):
    from utils.native_ci_evidence import snapshot
    output.mkdir(parents=True, exist_ok=True)
    upload = output / "upload"
    upload.mkdir(exist_ok=False)
    preservation = {"source_unchanged": False, "expected_head_matches": False,
                    "source_inspection_succeeded": False,
                    "run_reached": (output / "outcome.json").is_file()}
    try:
        current = source(repo)
        before_path = output / "source-before.json"
        preservation.update(source_unchanged=before_path.exists() and
            json.loads(before_path.read_text()) == current,
            expected_head_matches=current["head"] == expected, source_inspection_succeeded=True)
    except Exception as exc:
        error = {"type": type(exc).__name__, "message": str(exc)}
        current = {"inspection_failed": True, "error": error}
        preservation["source_inspection_error"] = error
    save(output / "source-final.json", current)
    save(output / "preservation.json", preservation)
    cases = output / "cases"
    before = archived = after = None
    retained = {"status": "capture_failed", "original_root": str(cases)}
    try:
        before = snapshot(cases)
        with tarfile.open(upload / "cases.tar.gz", "x:gz", dereference=False) as archive:
            archived = snapshot(cases, archive, archive_name="cases")
        after = snapshot(cases)
        retained["status"] = "retained" if before == archived == after else "capture_changed"
    except Exception as exc:
        retained["error"] = {"type": type(exc).__name__, "message": str(exc)}
    retained.update(entries=before, archived=archived, after=after,
        unchanged_during_archive=retained["status"] == "retained")
    save(upload / "case-manifest.json", retained)
    names = ["run.json", "outcome.json", "source-before.json", "source-final.json", "preservation.json"]
    for label, _ in NODES:
        names += [label + ".log", label + ".xml", label + "-command.json", "source-after-" + label + ".json"]
    for name in names:
        path = output / name
        if path.is_file() and not path.is_symlink():
            shutil.copyfile(path, upload / name)
    artifacts = inventory(upload)
    artifacts.pop("artifact-manifest.json", None)
    save(upload / "artifact-manifest.json", artifacts)
    return 0 if (preservation["source_unchanged"] and current.get("tracked_exact") is True
                 and preservation["expected_head_matches"] and retained["status"] == "retained") else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("run", "finalize"))
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--quiet-lock", type=Path,
                        help="Shared quiet-window lock; existence refuses child execution")
    parser.add_argument("--network-denied-sandbox", action="store_true",
                        help="Acknowledge an enclosing network-denied sandbox, not enforced by this helper")
    args = parser.parse_args()
    repo, output = Path.cwd().resolve(), args.output.resolve()
    if not re.fullmatch(r"[0-9a-f]{40}", args.expected_head):
        parser.error("expected-head must be a full commit SHA")
    if output.is_relative_to(repo) or repo.is_relative_to(output):
        parser.error("output must be a separate fresh external directory")
    if args.operation == "run":
        if args.quiet_lock is None or not args.network_denied_sandbox:
            parser.error("run requires --quiet-lock and --network-denied-sandbox")
        return run(repo, output, args.expected_head, quiet_lock=args.quiet_lock.absolute(), network_denied=True)
    return finalize(repo, output, args.expected_head)


if __name__ == "__main__":
    raise SystemExit(main())
