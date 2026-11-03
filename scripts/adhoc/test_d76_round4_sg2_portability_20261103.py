#!/usr/bin/env python3
"""Review-only SG2 portability witnesses for PR #5213, 2026-11-03.

Inputs: a pinned outer archive proof and one dirty/non-Git layout selection.
Outputs: retained nested source, ordinary-pytest log/XML/phases and variant proof.
Not part of ordinary tests/ collection: the six full publication cases run only
as explicitly selected review trials, one at a time with a 1800-second bound.
"""
from collections import Counter
import hashlib
import importlib.util
import ipaddress
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import tarfile
import time

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
NODE = ("tests/test_wave7_5213_d76_registration.py::"
        "test_sg2_root_launch_completes_and_records_registered_paths")
SELF = "scripts/adhoc/test_d76_round4_sg2_portability_20261103.py"


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def save(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


def git(root, *args, check=True):
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(GIT_NO_LAZY_FETCH="1", GIT_CONFIG_GLOBAL="/dev/null",
               GIT_CONFIG_NOSYSTEM="1", GIT_OPTIONAL_LOCKS="0",
               GIT_CEILING_DIRECTORIES=str(root.parent))
    return subprocess.run(["git", "--no-replace-objects", "-c", "protocol.allow=never",
                           "-c", "core.hooksPath=/dev/null", "-C", str(root), *args],
                          env=env, check=check, capture_output=True, text=True)


def extract(proof, destination):
    archive = Path(proof["archive"])
    assert archive.is_file() and not archive.is_symlink()
    assert sha(archive) == proof["archive_sha256"]
    destination.mkdir(exist_ok=True)
    with tarfile.open(archive, "r:") as source:
        for member in source.getmembers():
            path = Path(member.name)
            assert not path.is_absolute() and ".." not in path.parts
            assert not member.isdev() and not member.isfifo()
        source.extractall(destination, filter="data")


def offline_guard(output):
    def local(host):
        if isinstance(host, bytes):
            host = host.decode("ascii", errors="strict")
        if host == "localhost":
            return True
        try:
            return ipaddress.ip_address(host).is_loopback
        except (ValueError, TypeError):
            return False

    def audit(event, args):
        if event in {"socket.connect", "socket.sendto", "socket.bind"}:
            if getattr(args[0], "family", None) == socket.AF_UNIX:
                return
            address = args[-1]
            if isinstance(address, tuple) and local(address[0]):
                return
        elif event in {"socket.getaddrinfo", "socket.gethostbyname", "socket.gethostbyaddr"}:
            if local(args[0]):
                return
        else:
            return
        with (output / "network-denials.jsonl").open("a") as stream:
            stream.write(json.dumps({"event": event}) + "\n")
        raise RuntimeError("portability trial refuses external network: " + event)

    sys.addaudithook(audit)


def child():
    # Execute ordinary pytest from this archive, without site/.pth startup,
    # Git cleanliness checks, or review source/origin-attestation plugins.
    root, node, output, paths = Path(sys.argv[2]), sys.argv[3], Path(sys.argv[4]), Path(sys.argv[5])
    assert sys.flags.no_site and sys.flags.safe_path and sys.dont_write_bytecode
    assert root == ROOT and node.startswith(NODE + "[")
    dependency_config = json.loads(paths.read_text())
    dependencies = dependency_config["paths"]
    assert isinstance(dependencies, list) and all(isinstance(p, str) and Path(p).is_absolute()
                                                 for p in dependencies)
    sys.prefix = dependency_config["prefix"]
    sys.exec_prefix = dependency_config["exec_prefix"]
    sys.path[:0] = [str(root / "src"), str(root), *dependencies]
    output.mkdir()
    offline_guard(output)
    import pytest

    class Evidence:
        selected = []
        reports = []

        def pytest_collection_finish(self, session):
            self.selected = [item.nodeid for item in session.items]

        def pytest_runtest_logreport(self, report):
            row = {"nodeid": report.nodeid, "when": report.when, "outcome": report.outcome,
                   "duration_seconds": report.duration, "xfail": getattr(report, "wasxfail", None)}
            self.reports.append(row)
            with (output / "phases.jsonl").open("a") as stream:
                stream.write(json.dumps(row, sort_keys=True) + "\n")

    evidence = Evidence()
    started = time.monotonic()
    status = int(pytest.main([node, "-v", "-p", "no:cacheprovider", "--rootdir", str(root),
                             "-c", str(root / "pyproject.toml"), "--basetemp", str(output / "cases"),
                             "--junitxml", str(output / "pytest.xml"), "-rfE"], plugins=[evidence]))
    complete = (evidence.selected == [node] and len(evidence.reports) == 3
                and Counter(r["when"] for r in evidence.reports) ==
                    Counter({"setup": 1, "call": 1, "teardown": 1})
                and all(r["nodeid"] == node for r in evidence.reports))
    passed = (status == 0 and complete and
              all(r["outcome"] == "passed" and r["xfail"] is None for r in evidence.reports)
              and not (output / "network-denials.jsonl").exists())
    save(output / "outcome.json", {"nodeid": node, "selected": evidence.selected,
         "reports": evidence.reports, "returncode": status, "complete": complete, "passed": passed,
         "wall_seconds": time.monotonic() - started,
         "source_attestation": False, "mode": "ordinary pytest; no Git precondition",
         "dependency_paths": dependencies})
    return 0 if passed else 1


if __name__ == "__main__":
    if sys.argv[1:2] != ["--ordinary-child"]:
        raise SystemExit("review witness child requires --ordinary-child")
    raise SystemExit(child())

import pytest


@pytest.mark.parametrize("variant", ["dirty-tracked", "non-git"])
@pytest.mark.parametrize("layout", ["none", "explicit", "conventional"])
def test_real_sg2_works_without_clean_git_precondition(tmp_path, variant, layout):
    proof_path = Path(os.environ["D4D_SG2_PORTABILITY_ARCHIVE_PROOF"])
    expected_head = os.environ["D4D_SG2_PORTABILITY_HEAD"]
    assert Path(os.environ["D76_TREE"]) == ROOT
    outer_plan = json.loads((Path(os.environ["D76_OUTPUT"]) / "plan.json").read_text())
    proof = json.loads(proof_path.read_text())
    assert outer_plan["head"] == expected_head == proof["head"]
    assert proof["destination"] == str(ROOT)
    assert outer_plan["archive_proof_sha256"] == sha(proof_path)
    assert git(ROOT, "rev-parse", "HEAD").stdout.strip() == expected_head

    nested = tmp_path / "ordinary-source"
    extract(proof, nested)
    extract(proof["fairscape"], nested / "fairscape_models")
    assert not (nested / ".git").exists()
    changed = None
    if variant == "dirty-tracked":
        git(nested, "init", "--quiet", "--template=")
        objects = Path(git(ROOT, "rev-parse", "--git-path", "objects").stdout.strip())
        if not objects.is_absolute():
            objects = ROOT / objects
        (nested / ".git/objects/info/alternates").write_text(str(objects.resolve(strict=True)) + "\n")
        (nested / ".git/HEAD").write_text(expected_head + "\n")
        git(nested, "read-tree", expected_head)
        assert not git(nested, "diff", "--name-only", "--ignore-submodules=all").stdout.strip()
        path = nested / "README.md"
        assert path.is_file() and not path.is_symlink()
        before = sha(path)
        with path.open("a") as stream:
            stream.write("\n<!-- uncommitted portability witness; no executable change -->\n")
        assert git(nested, "diff", "--name-only", "--ignore-submodules=all").stdout.splitlines() == ["README.md"]
        changed = {"path": "README.md", "before_sha256": before, "after_sha256": sha(path)}
    else:
        observed = git(nested, "rev-parse", "--show-toplevel", check=False)
        assert observed.returncode != 0, observed.stdout

    source_node = "tests/test_wave7_5213_d76_registration.py"
    assert sha(nested / source_node) == sha(ROOT / source_node)
    assert sha(nested / SELF) == sha(Path(__file__))
    dependencies = []
    for entry in sys.path:
        if not entry:
            continue
        path = Path(entry)
        if path.is_absolute() and path.exists() and not path.resolve().is_relative_to(ROOT):
            if str(path) not in dependencies:
                dependencies.append(str(path))
    deps = tmp_path / "dependency-paths.json"
    save(deps, {"paths": dependencies, "prefix": sys.prefix, "exec_prefix": sys.exec_prefix})
    node = NODE + "[" + layout + "]"
    output, log = tmp_path / "ordinary-pytest", tmp_path / "ordinary-pytest.log"
    command = [sys.executable, "-S", "-P", "-B", str(nested / SELF),
               "--ordinary-child", str(nested), node, str(output), str(deps)]
    env = {k: v for k, v in os.environ.items()
           if k not in {"PYTHONPATH", "PYTHONHOME", "PYTEST_CURRENT_TEST", "PYTEST_PLUGINS",
                        "PYTEST_DISABLE_PLUGIN_AUTOLOAD", "D4D_SG2_CHILD_CASE", "D4D_SG2_CHILD_PID"}
           and not k.startswith(("D76_", "D4D_SG2_PORTABILITY_", "D4D_TEST_REVIEW_", "PYTEST_XDIST_",
                                 "ANTHROPIC_", "CBORG_", "OPENAI_", "AZURE_", "AWS_", "GEMINI_",
                                 "GOOGLE_API_", "VERTEX_", "GIT_"))
           and not re.search(r"(API_KEY|ACCESS_KEY|SECRET|TOKEN|CREDENTIAL)", k, re.I)
           and not k.upper().endswith("_PROXY")}
    env.update(PYTHONDONTWRITEBYTECODE="1", PYTEST_ADDOPTS="", PIP_NO_INDEX="1", UV_OFFLINE="1",
               GIT_NO_LAZY_FETCH="1", GIT_CONFIG_GLOBAL="/dev/null", GIT_CONFIG_NOSYSTEM="1",
               GIT_CEILING_DIRECTORIES=str(nested.parent))
    save(tmp_path / "portability.json", {"source_head": expected_head, "variant": variant,
         "layout": layout, "source_archive_sha256": proof["archive_sha256"],
         "fairscape_archive_sha256": proof["fairscape"]["archive_sha256"],
         "source_node_sha256": sha(nested / source_node), "witness_sha256": sha(nested / SELF),
         "tracked_edit": changed, "command": command, "child_mode": "ordinary",
         "review_attestation": False, "deadline_seconds": 1800})
    # This is review-only supervision. The ordinary SG2 node must choose its own
    # default utility; the witness neither patches it nor bypasses its assertions.
    spec = importlib.util.spec_from_file_location("_portability_deadline",
        HERE / "d76_process_deadline_20261102.py")
    supervisor = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = supervisor
    spec.loader.exec_module(supervisor)
    with log.open("wb") as stream:
        completed = supervisor.run(command, cwd=nested, env=env, stream=stream,
                                   evidence=tmp_path / "supervisor", seconds=1800)
    assert not completed.expired, f"SG2 {variant}/{layout} exceeded the 1800-second deadline; log: {log}"
    assert completed.returncode == 0, log.read_text(errors="replace")[-30000:]
    result = json.loads((output / "outcome.json").read_text())
    assert result["selected"] == [node] and result["complete"] and result["passed"]
    assert (output / "pytest.xml").stat().st_size > 0

