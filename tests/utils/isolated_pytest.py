"""Run one ordinary pytest case in a bounded, offline subprocess.

The default route needs no Git metadata, clean checkout or review tools.
A review runner may explicitly select a SHA-bound external evidence adapter;
ordinary test collection and execution do not import that adapter.
"""
import argparse
from collections import Counter
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import shutil
import socket
import sys
import time

REVIEW_ENV = "D4D_ISOLATED_TEST_REVIEW"
NODE_ENV = "D4D_ISOLATED_TEST_NODE"
PID_ENV = "D4D_ISOLATED_TEST_PID"


def save(path, value):
    with Path(path).open("x") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


def dependency_configuration(root):
    paths = []
    for value in sys.path:
        if not value:
            continue
        path = Path(value)
        if path.is_absolute() and path.exists() and not path.resolve().is_relative_to(root):
            if str(path) not in paths:
                paths.append(str(path))
    return {"paths": paths, "prefix": sys.prefix, "exec_prefix": sys.exec_prefix}


def bootstrap(root, configuration):
    if not (sys.flags.no_site and sys.flags.safe_path and sys.dont_write_bytecode):
        raise ValueError("isolated pytest child requires -S -P -B")
    values = json.loads(Path(configuration).read_text())
    paths = values["paths"]
    if (not isinstance(paths, list) or not all(isinstance(p, str) and Path(p).is_absolute() for p in paths)
            or not isinstance(values["prefix"], str) or not isinstance(values["exec_prefix"], str)):
        raise ValueError("invalid explicit dependency configuration")
    sys.prefix, sys.exec_prefix = values["prefix"], values["exec_prefix"]
    sys.path[:0] = [str(root / "src"), str(root), *paths]


def child_environment():
    env = {key: value for key, value in os.environ.items() if key not in
           {"PYTHONPATH", "PYTHONHOME", "PYTEST_CURRENT_TEST", "PYTEST_PLUGINS",
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD", REVIEW_ENV, NODE_ENV, PID_ENV,
            "D4D_SG2_CHILD_CASE", "D4D_SG2_CHILD_PID"}
           and not key.startswith(("PYTEST_XDIST_", "D76_", "ANTHROPIC_", "CBORG_", "OPENAI_",
                                   "AZURE_", "AWS_", "GOOGLE_API_", "GEMINI_", "VERTEX_"))
           and not re.search(r"(API_KEY|ACCESS_KEY|SECRET|TOKEN|CREDENTIAL)", key, re.I)
           and not key.upper().endswith("_PROXY")}
    env.update(PYTHONDONTWRITEBYTECODE="1", PYTEST_ADDOPTS="", PIP_NO_INDEX="1",
               UV_OFFLINE="1", HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1")
    return env


def review_adapter(root):
    raw = os.environ.get(REVIEW_ENV)
    if raw is None:
        return None
    value = json.loads(raw)
    if set(value) != {"root", "runner", "sha256", "head"} or value["root"] != str(root):
        raise ValueError("explicit review adapter does not bind this source root")
    path = Path(value["runner"])
    if not path.is_absolute() or path.is_symlink() or path.resolve(strict=True) != path or not path.is_relative_to(root):
        raise ValueError("review adapter must be a physical file within this source")
    if hashlib.sha256(path.read_bytes()).hexdigest() != value["sha256"]:
        raise ValueError("explicit review adapter changed")
    if not re.fullmatch("[0-9a-f]{40}", value["head"]):
        raise ValueError("explicit review adapter requires an exact commit")
    return value


def run_isolated_pytest(request, tmp_path, *, root, seconds, label, evidence_name="isolated-pytest"):
    """Return True after the parent completed the case; False in its exact child."""
    node = request.node.nodeid
    marker = os.environ.get(NODE_ENV)
    if marker is not None:
        if marker != node or os.environ.get(PID_ENV) != str(os.getpid()):
            raise ValueError("isolated pytest child marker differs from its exact node/PID")
        return False
    root = Path(root).resolve(strict=True)
    tmp_path = Path(tmp_path)
    output, log = tmp_path / evidence_name, tmp_path / (evidence_name + ".log")
    if output.exists() or output.is_relative_to(root):
        raise ValueError("fresh isolated evidence outside source required")
    dependencies = tmp_path / (evidence_name + "-dependencies.json")
    save(dependencies, dependency_configuration(root))
    adapter = review_adapter(root)
    entry = adapter["runner"] if adapter is not None else str(Path(__file__).resolve())
    command = [sys.executable, "-S", "-P", "-B", entry, "--root", str(root), "--node", node,
               "--output", str(output), "--dependencies", str(dependencies)]
    if adapter is not None:
        command += ["--expect-head", adapter["head"]]
    from tests.utils import subprocess_deadline
    with log.open("xb") as stream:
        completed = subprocess_deadline.run(command, cwd=root, env=child_environment(),
            stream=stream, evidence=tmp_path / (evidence_name + "-supervisor"), seconds=seconds)
    assert not completed.expired, f"{label} exceeded the {seconds}-second subprocess deadline; retained log: {log}"
    assert completed.returncode == 0, log.read_text(errors="replace")[-20000:]
    report = json.loads((output / "outcome.json").read_text())
    assert report["nodeid"] == node and report["passed"] is True
    assert (output / "pytest.xml").stat().st_size > 0
    if adapter is not None:
        assert report["review_attestation"] is True and report["head"] == adapter["head"]
    else:
        assert report["review_attestation"] is False
    return True


def install_offline_guard(output, denials):
    def local(host):
        if isinstance(host, bytes):
            host = host.decode("ascii", errors="strict")
        if host == "localhost":
            return True
        try:
            return ipaddress.ip_address(host).is_loopback
        except (TypeError, ValueError):
            return False

    def refuse(event):
        denials.append(event)
        with (output / "guard-denials.jsonl").open("a") as stream:
            stream.write(json.dumps({"event": event}) + "\n")
        raise RuntimeError("isolated offline test refuses " + event)

    def audit(event, args):
        if event in {"socket.connect", "socket.sendto", "socket.bind"}:
            if getattr(args[0], "family", None) == socket.AF_UNIX:
                return
            address = args[-1]
            if not (isinstance(address, tuple) and local(address[0])):
                refuse(event)
        elif event in {"socket.getaddrinfo", "socket.gethostbyname", "socket.gethostbyaddr"}:
            if not local(args[0]):
                refuse(event)
        elif event == "subprocess.Popen":
            executable, argv, cwd, env = args
            name = Path(os.fsdecode(executable)).name
            if name in {"claude", "codex", "gemini", "gh", "curl", "wget", "ssh"}:
                command = os.fsdecode(executable)
                path = Path(command) if "/" in command else Path(shutil.which(command, path=(env or os.environ).get("PATH")) or "/missing")
                if not path.is_absolute():
                    path = Path(cwd or Path.cwd()) / path
                if not path.resolve().is_relative_to(output):
                    refuse(event + ":" + name)
    sys.addaudithook(audit)


def execute_case(root, node, output, *, plugins=(), before_run=None):
    """Execute one ordinary case and collect phases, without source attestation."""
    output.mkdir()
    denials = []
    install_offline_guard(output, denials)
    if before_run is not None:
        before_run()
    import pytest
    os.environ[NODE_ENV], os.environ[PID_ENV] = node, str(os.getpid())

    class Evidence:
        selected = []
        reports = []

        def pytest_collection_finish(self, session):
            self.selected = [item.nodeid for item in session.items]

        def pytest_runtest_logreport(self, report):
            self.reports.append({"nodeid": report.nodeid, "when": report.when,
                "outcome": report.outcome, "duration_seconds": report.duration,
                "xfail": getattr(report, "wasxfail", None)})

    observer = Evidence()
    started = time.monotonic()
    result = int(pytest.main([node, "-q", "-p", "no:cacheprovider", "--rootdir", str(root),
        "-c", str(root / "pyproject.toml"), "--basetemp", str(output / "cases"),
        "--junitxml", str(output / "pytest.xml")], plugins=[observer, *plugins]))
    complete = (observer.selected == [node] and len(observer.reports) == 3
        and Counter(row["when"] for row in observer.reports) == Counter({"setup": 1, "call": 1, "teardown": 1})
        and all(row["nodeid"] == node and row["outcome"] == "passed" and row["xfail"] is None
                for row in observer.reports))
    return {"nodeid": node, "pid": os.getpid(), "selected": observer.selected,
        "reports": observer.reports, "returncode": result, "complete": complete,
        "zero_guard_denials": not denials, "wall_seconds": time.monotonic() - started,
        "passed": result == 0 and complete and not denials, "review_attestation": False,
        "scope": "one serial ordinary pytest child; no Git or source-attestation requirement"}


def argument_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--node", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dependencies", type=Path, required=True)
    return parser


def main():
    args = argument_parser().parse_args()
    root = args.root.resolve(strict=True)
    if root != Path(__file__).resolve().parents[2]:
        raise ValueError("isolated child utility must come from its selected source")
    output = args.output.resolve()
    if output.exists() or output.is_relative_to(root):
        raise ValueError("fresh child evidence outside source required")
    bootstrap(root, args.dependencies)
    report = execute_case(root, args.node, output)
    save(output / "outcome.json", report)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

