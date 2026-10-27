#!/usr/bin/env python3
# Purpose: validate R9b repair-refresh checkpoints with explicit import/source evidence.
# Inputs: committed checkout, expected head, causal/regression group and fresh output.
# Outputs: exact source inventories, module origins, pytest JUnit and outcome JSON.
# Refs #5157/#5210; adapted from validate_e3x_restack_20261026.py at2bbb0dfff.
# Date: 2026-10-27. No provider calls; scripted offline fixtures only.
"""Run with the primary venv Python -S -P -B; never enable .pth startup."""
import argparse
import hashlib
import importlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
TARGET = "0674193f6d4e1b42a6f3afe6d5475c8635cfbdf2"
PROTECTED = ("src/data_sheets_schema/shared_generation.py", "src/data_sheets_schema/api_Generation_v2.py",
             "src/download/prompts/canonical_hashes.yaml")
SCOPES = ("src", "scripts", "tests", "utils", ".claude", ".github", "pyproject.toml", "poetry.lock")
ROSTER = {
    "causal": ("tests/test_download/test_api_runner.py::TestValidatorRepairRefreshCheckpoint",),
    "corruption": ("tests/test_download/test_api_runner.py::TestValidatorRepairRefreshCheckpoint::test_missing_corrupt_or_stale_checkpoint_refuses_before_calls",),
    "regression": ("tests/test_download/test_api_runner.py", "tests/test_usage_ledger.py", "tests/test_report_admission.py"),
}


def git(*args):
    return subprocess.check_output(
        ["git", "--no-replace-objects", *args], cwd=ROOT,
        env=dict(os.environ, GIT_OPTIONAL_LOCKS="0", GIT_NO_LAZY_FETCH="1"),
    )


def save(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


def source():
    records = {}
    for row in git("ls-tree", "-r", "-z", "HEAD", "--", *SCOPES).split(b"\0"):
        if not row:
            continue
        header, name = row.split(b"\t", 1)
        mode, kind, expected = header.decode().split()
        relative = name.decode()
        path = ROOT / relative
        if kind != "blob" or mode not in ("100644", "100755", "120000"):
            raise ValueError("unsupported source entry: " + relative)
        if mode == "120000":
            if not path.is_symlink():
                raise ValueError("expected source symlink: " + relative)
            raw = os.fsencode(os.readlink(path))
        else:
            if not path.is_file() or path.is_symlink() or path.resolve() != path:
                raise ValueError("non-regular or aliased source: " + relative)
            raw = path.read_bytes()
        actual = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
        if actual != expected:
            raise ValueError("tracked source bytes differ from HEAD: " + relative)
        records[relative] = {"mode": mode, "blob": expected, "bytes": len(raw),
                             "sha256": hashlib.sha256(raw).hexdigest()}
    for relative in PROTECTED:
        if not git("ls-tree", TARGET, "--", relative):
            if os.path.lexists(ROOT / relative):
                raise ValueError("absent protected path was introduced: " + relative)
        elif (ROOT / relative).read_bytes() != git("show", TARGET + ":" + relative):
            raise ValueError("protected target bytes changed: " + relative)
    return {"head": git("rev-parse", "HEAD").decode().strip(),
            "status": git("status", "--porcelain=v1").decode(),
            "scope": list(SCOPES), "tracked_files": records,
            "scope_note": "tracked source/config/test bytes; not a complete corpus or dependency inventory"}


def origins(tracked):
    result = {}
    package_root = ROOT / "src/data_sheets_schema"
    tests_root = ROOT / "tests"
    for name, module in tuple(sys.modules.items()):
        if not (name == "data_sheets_schema" or name.startswith("data_sheets_schema.")
                or name == "tests" or name.startswith("tests.")):
            continue
        allowed = tests_root if name == "tests" or name.startswith("tests.") else package_root
        paths = list(getattr(module, "__path__", ()))
        file = getattr(module, "__file__", None)
        if file:
            actual = Path(file).resolve()
            if not actual.is_relative_to(allowed) or actual.relative_to(ROOT).as_posix() not in tracked:
                raise ValueError("foreign or untracked imported module: " + name + " -> " + str(actual))
            paths.append(file)
        for path in paths:
            if not Path(path).resolve().is_relative_to(allowed):
                raise ValueError("foreign namespace path: " + name + " -> " + str(path))
        result[name] = paths
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--group", choices=tuple(ROSTER), required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not sys.flags.no_site or not sys.flags.safe_path or not sys.dont_write_bytecode:
        raise ValueError("requires -S -P -B; ordinary editable-site startup is forbidden")
    output = args.output.absolute()
    if output.resolve() != output or output.is_relative_to(ROOT):
        raise ValueError("evidence must be a fresh physical directory outside the checkout")
    output.mkdir(parents=True, exist_ok=False)
    os.chdir(ROOT)
    before = source()
    save(output / "source-before.json", before)
    if before["head"] != args.head or before["status"]:
        raise ValueError("expected committed clean source head required")
    git("merge-base", "--is-ancestor", TARGET, "HEAD")
    venv = Path(sys.executable).parent.parent
    site = venv / "lib" / ("python" + ".".join(map(str, sys.version_info[:2]))) / "site-packages"
    if not (venv / "pyvenv.cfg").is_file() or not site.is_dir() or site.resolve() != site:
        raise ValueError("physical primary-venv dependency directory required")
    if os.environ.get("PYTHONPATH") or os.environ.get("PYTHONHOME"):
        raise ValueError("bootstrap requires empty PYTHONPATH and PYTHONHOME")
    if any(not p or not Path(p).resolve().is_relative_to(Path(sys.base_prefix).resolve()) for p in sys.path):
        raise ValueError("bootstrap requires empty PYTHONPATH and only standard-library startup paths")
    # Python 3.13 normally establishes these venv prefixes in site.venv().
    # Preserve that interpreter identity without processing any .pth files.
    prefixes_before = {"prefix": sys.prefix, "exec_prefix": sys.exec_prefix}
    sys.prefix = sys.exec_prefix = str(venv)
    sys.path[:] = [str(ROOT / "src"), str(ROOT), *sys.path, str(site)]
    removed = sorted(k for k in os.environ if k.startswith(("ANTHROPIC_", "CBORG_", "OPENAI_"))
                     or k.endswith(("_API_KEY", "_AUTH_TOKEN", "_ACCESS_TOKEN"))
                     or k in {"CLAUDE_CODE_OAUTH_TOKEN", "PYTHONHOME", "PYTEST_PLUGINS", "D4D_INSTALL_TESTS"})
    for key in removed:
        os.environ.pop(key)
    os.environ.update(PYTHONPATH=os.pathsep.join((str(ROOT / "src"), str(ROOT))),
        PYTEST_DISABLE_PLUGIN_AUTOLOAD="1", PYTEST_ADDOPTS="", PYTHONDONTWRITEBYTECODE="1",
        PYTHONPYCACHEPREFIX=str(output / "pycache"), PIP_NO_INDEX="1", UV_OFFLINE="1", GIT_NO_LAZY_FETCH="1")
    sys.pycache_prefix = str(output / "pycache")
    save(output / "environment.json", {"python": sys.version, "executable": sys.executable,
        "sys_path": list(sys.path), "site_startup": "disabled", "pth_execution": "disabled",
        "site_packages": str(site), "plugin_autoload": "disabled", "credential_names_removed": removed,
        "prefixes_before": prefixes_before, "prefix": sys.prefix, "exec_prefix": sys.exec_prefix,
        "base_prefix": sys.base_prefix, "base_exec_prefix": sys.base_exec_prefix,
        "packages": sorted((d.metadata.get("Name", ""), d.version) for d in importlib.metadata.distributions()),
        "dependency_bytes_attested": False, "network_sandbox_claimed": False})
    for module in ("api_runner", "usage_ledger", "receipt_completion"):
        importlib.import_module("data_sheets_schema." + module)
    save(output / "origins-before.json", origins(before["tracked_files"]))
    import pytest
    selected = list(ROSTER[args.group])
    command = ["-q", "-p", "no:cacheprovider", "--basetemp", str(output / "cases"),
               "--junitxml", str(output / "pytest.xml"), *selected]
    if args.group == "regression":
        command.extend(("-k", "not ValidatorRepairRefreshCheckpoint and not Live"))
    save(output / "command.json", {"pytest_args": command, "cwd": str(ROOT)})
    started = time.monotonic()
    code = 1
    try:
        code = int(pytest.main(command))
    finally:
        save(output / "origins-after.json", origins(before["tracked_files"]))
        after = source()
        save(output / "source-after.json", after)
        summary = {"returncode": code if before == after else 1, "pytest_returncode": code,
                   "source_unchanged": before == after,
                   "wall_seconds": time.monotonic() - started, "scientific_acceptance": "not_assessed"}
        if (output / "pytest.xml").is_file():
            cases = list(ET.parse(output / "pytest.xml").getroot().iter("testcase"))
            summary["junit"] = {"cases": len(cases), **{
                key: sum(case.find(tag) is not None for case in cases)
                for key, tag in (("failures", "failure"), ("errors", "error"), ("skipped", "skipped"))}}
        save(output / "outcome.json", summary)
        if before != after:
            code = 1
    return code


if __name__ == "__main__":
    raise SystemExit(main())
