#!/usr/bin/env python3
"""Run PR #5094 production and causal review tests offline, 2026-10-28.

Inputs: clean review/fix checkout based on 8ff18d2e5 and cached attestation utilities
at immutable 808415a0. Outputs: fresh external logs, JUnit, origin/source pins.
No provider, GitHub, or production writes; parent commits helper and results.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import types
import xml.etree.ElementTree as ET

BASE = "8ff18d2e57ceed1ec4de53169163174f26fecebb"
SUPPORT_HEAD = "808415a0db55bd8bda76d42ca5e5982c099f6a6a"
SUPPORT_PATH = "scripts/adhoc/wave3_validation_common_20261027.py"
GROUPS = {
    "causal": ("test_wave4_5094_review",),
    "focused": ("test_wave4_5094_review", "test_report_audit_totals"),
    "existing": ("test_report_audit_totals", "test_report_gate", "test_generation_record_schema", "test_record_required_values", "test_backfill_checks"),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--child", action="store_true")
    parser.add_argument("--head", required=True)
    parser.add_argument("--group", choices=GROUPS, required=True)
    args = parser.parse_args()
    root, output = args.root.resolve(), args.output.resolve()
    modules = GROUPS[args.group]
    os.chdir(root)
    raw = subprocess.check_output(["git", "--no-replace-objects", "show", SUPPORT_HEAD + ":" + SUPPORT_PATH], cwd=root)
    support = types.ModuleType("pr5094_validation_support")
    support.__file__ = str(root / SUPPORT_PATH)
    exec(compile(raw, "git:" + SUPPORT_HEAD + ":" + SUPPORT_PATH, "exec"), support.__dict__)
    support.ROOT = root
    support.MODULES = modules
    if args.child:
        if not sys.flags.no_site or not sys.flags.safe_path or not sys.dont_write_bytecode:
            raise ValueError("Requires -S -P -B")
        venv = Path(sys.executable).parent.parent
        site = venv / "lib" / ("python" + ".".join(map(str, sys.version_info[:2]))) / "site-packages"
        if not (venv / "pyvenv.cfg").is_file() or not site.is_dir():
            raise ValueError("Physical repository venv required")
        sys.prefix = sys.exec_prefix = str(venv)
        sys.path.append(str(site))
        def refuse_network(event, arguments):
            if event in ("socket.connect", "socket.getaddrinfo", "socket.sendto"):
                raise RuntimeError("PR #5094 offline review forbids network: " + event)
        sys.addaudithook(refuse_network)
        support.save(output / "bootstrap.json", {"site_startup": "disabled", "pth_execution": "disabled",
            "executable": sys.executable, "python": sys.version, "sys_path": sys.path,
            "network_control": "Python audit hook, not an OS-level subprocess network sandbox",
            "dependency_bytes_attested": False})
        for name in modules:
            importlib.import_module("tests." + name)
        baseline = json.loads((output / "source-before.json").read_text())
        support.save(output / "origins-before.json", support.origins(baseline))
        import pytest
        command = ["-q", "-p", "no:cacheprovider", "--basetemp", str(output / "cases"),
                   "--junitxml", str(output / "pytest.xml"), *("tests/" + name + ".py" for name in modules)]
        support.save(output / "pytest-command.json", {"arguments": command, "cwd": str(root)})
        try:
            return int(pytest.main(command))
        finally:
            support.save(output / "origins-after.json", support.origins(baseline))
    if output.is_relative_to(root):
        raise ValueError("External outputs required")
    output.mkdir(parents=True, exist_ok=False)
    before = support.source()
    support.save(output / "source-before.json", before)
    if before["head"] != args.head or not before["tracked_exact"] or support.git("status", "--porcelain=v1", "--untracked-files=all"):
        raise ValueError("Untouched exact-head worktree required")
    changed = support.git("diff", "--name-only", BASE, "HEAD", "--", "src", ".claude").decode().splitlines()
    allowed = {"src/data_sheets_schema/report_audit_totals.py", "src/data_sheets_schema/api_runner.py"}
    if not set(changed).issubset(allowed):
        raise ValueError("Review fixes changed a protected or out-of-scope source")
    env = dict(os.environ)
    removed = sorted(key for key in env if key.startswith(("ANTHROPIC_", "CBORG_", "OPENAI_", "GIT_"))
        or key.endswith(("_API_KEY", "_AUTH_TOKEN", "_ACCESS_TOKEN"))
        or key in {"CLAUDE_CODE_OAUTH_TOKEN", "D4D_INSTALL_TESTS", "PYTHONHOME", "PYTEST_PLUGINS"})
    for key in removed:
        env.pop(key)
    env.update(PYTHONDONTWRITEBYTECODE="1", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1", PYTEST_ADDOPTS="",
        PIP_NO_INDEX="1", PIP_DISABLE_PIP_VERSION_CHECK="1", UV_OFFLINE="1", HF_HUB_OFFLINE="1",
        TRANSFORMERS_OFFLINE="1", GIT_NO_LAZY_FETCH="1", GIT_OPTIONAL_LOCKS="0",
        PYTHONPATH=os.pathsep.join(str(root / path) for path in ("src", "scripts", ".")))
    command = [sys.executable, "-S", "-P", "-B", str(Path(__file__).resolve()),
               "--root", str(root), "--output", str(output), "--head", args.head, "--group", args.group, "--child"]
    support.save(output / "plan.json", {"command": command, "head": args.head, "base": BASE, "modules": modules,
        "support_commit": SUPPORT_HEAD, "support_blob": SUPPORT_PATH, "support_sha256": hashlib.sha256(raw).hexdigest(),
        "helper_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "credential_names_removed": removed, "production_changes": changed})
    start = time.monotonic()
    with (output / "pytest.log").open("xb") as stream:
        code = subprocess.run(command, env=env, stdout=stream, stderr=subprocess.STDOUT).returncode
    after = support.source()
    support.save(output / "source-after.json", after)
    counts = dict.fromkeys(modules, 0)
    invalid, skipped, seen = [], [], set()
    if (output / "pytest.xml").is_file():
        for case in ET.parse(output / "pytest.xml").getroot().iter("testcase"):
            identity = (case.get("classname"), case.get("name"))
            name = case.get("classname", "").removeprefix("tests.").split(".")[0]
            if identity in seen or name not in counts or any(case.find(tag) is not None for tag in ("failure", "error")):
                invalid.append({"identity": identity, "tags": [child.tag for child in case]})
            elif case.find("skipped") is not None:
                skipped.append({"identity": identity, "reason": case.find("skipped").get("message")})
            else:
                counts[name] += 1
            seen.add(identity)
    origins_complete = all((output / name).is_file() for name in ("origins-before.json", "origins-after.json"))
    result = {"returncode": code, "source_unchanged": before == after, "passes_by_module": counts,
        "invalid_cases": invalid, "skipped": skipped, "origins_complete": origins_complete,
        "wall_seconds": time.monotonic() - start, "scientific_acceptance": "not assessed",
        "passed": code == 0 and before == after and all(counts.values()) and not invalid and not skipped and origins_complete}
    support.save(output / "outcome.json", result)
    print(json.dumps(result, sort_keys=True), flush=True)
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
