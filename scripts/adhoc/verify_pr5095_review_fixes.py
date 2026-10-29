#!/usr/bin/env python3
"""PR #5095 F1/F2/F4/F6/F7 verification, 2026-10-28.

Inputs: local Git base, working builder, pytest nodes, existing Python environment.
Outputs: serial mutation logs/JSON and CHORUS registration/roster byte comparisons.
Offline only. Temporary source mutations are restored in finally; no Git writes.
Use --basetemp outside a checkout when authorized: foreign-tree fixtures and
launcher log tests deliberately refuse directories inside the checkout.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
BUILDER = ROOT / "scripts/build_api_registrations.py"
TEST = "tests/test_preflight_resource_authority.py::"
BASE = "57784daadcc109839e4c76260ee4e5fd415a1c21"


def environment():
    env = dict(os.environ)
    for name in tuple(env):
        if name.startswith(("ANTHROPIC_", "CBORG_", "OPENAI_", "D4D_")) or name.endswith(("_API_KEY", "_AUTH_TOKEN", "_ACCESS_TOKEN")):
            env.pop(name)
    env.update(PYTHONPATH=str(ROOT / "src"), PYTHONDONTWRITEBYTECODE="1", GIT_NO_LAZY_FETCH="1")
    return env


def replace_once(source, old, new=""):
    assert source.count(old) == 1, f"mutation anchor is not unique: {old!r}"
    return source.replace(old, new, 1)


def mutations(args):
    original = BUILDER.read_bytes()
    source = original.decode()
    cases = {
        "checkout-root": (
            '        if checkout_at(selected) != selected:\n'
            '            raise ValueError("--worktree must be the root of a data-sheets-schema checkout")\n',
            "", "test_worktree_must_be_checkout_root"),
        "mixed-namespace": (
            '    if any(Path(path).resolve() != _expected_package for path in _selected_package.__path__):\n'
            '        raise SystemExit(\n'
            '            "--worktree package imports are mixed with another checkout; use the selected checkout\'s own venv, "\n'
            '            "or python -S with site-packages on PYTHONPATH"\n'
            '        )\n',
            "", "test_copied_cli_refuses_invalid_import_authority[mixed-namespace]"),
        "source-package": (
            'if _selected_bootstrap_root is not None and not (candidate_src / "data_sheets_schema" / "api_runner.py").is_file():\n'
            '    raise SystemExit("--worktree must contain the data_sheets_schema source package")\n',
            "", "test_copied_cli_refuses_invalid_import_authority[missing-package]"),
        "missing-draft-vocabulary": (
            '    elif worktree is not None:\n'
            '        raise FileNotFoundError(f"selected worktree vocabulary is missing: {vocab_path}")\n',
            "", "test_synthesized_context_requires_selected_vocabulary"),
        "draft-worktree-pass-through": (
            '                write_to_disk=write_to_disk,\n                worktree=worktree,\n',
            '                write_to_disk=write_to_disk,\n',
            "test_synthesized_context_requires_selected_vocabulary"),
        "absolute-vocabulary": (
            'DEFAULT_VOCABULARIES_PATH = Path("src/data_sheets_schema/b2ai_registry_vocabularies.yaml")',
            'DEFAULT_VOCABULARIES_PATH = ROOT / "src" / "data_sheets_schema" / "b2ai_registry_vocabularies.yaml"',
            "test_positional_draft_context_worktree_selects_vocabulary"),
        "cli-resource-binding": (
            '@_worktree_resources\ndef cli(', 'def cli(',
            "test_copied_cli_selects_foreign_tree_from_another_checkout"),
    }
    results = {}
    try:
        for name in args.case or cases:
            old, new, node = cases[name]
            command = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                       "-o", "addopts=", f"--basetemp={args.basetemp}", TEST + node]
            row = {"command": command}
            results[name] = row
            for phase in ("control", "mutated"):
                BUILDER.write_bytes(original if phase == "control" else replace_once(source, old, new).encode())
                result = subprocess.run(command, cwd=ROOT, env=environment(), capture_output=True, text=True, timeout=180)
                log = result.stdout + result.stderr
                (args.evidence / f"{name}-{phase}.log").write_text(log)
                row[phase] = {"exit_code": result.returncode,
                              "summary": [line for line in log.splitlines() if " passed" in line or " failed" in line]}
                print(name, phase, row[phase], flush=True)
                if phase == "control" and result.returncode:
                    row["result"] = "blocked: control fails"
                    break
                if phase == "mutated":
                    row["result"] = "killed" if result.returncode == 1 and " failed" in log else "unexpected"
            BUILDER.write_bytes(original)
    finally:
        BUILDER.write_bytes(original)
        (args.evidence / "mutations.json").write_text(json.dumps(results, indent=2) + "\n")
    assert all(row["result"] == "killed" for row in results.values()), results


def build_at_ref(args):
    # __file__ and cwd stay fixed, so changing only the builder code cannot
    # produce path-only differences in the registered inputs or output path.
    code = (BUILDER.read_bytes() if args.ref == "WORKTREE" else
            subprocess.check_output(["git", "show", f"{args.ref}:scripts/build_api_registrations.py"], cwd=ROOT))
    sys.argv = [str(BUILDER), "-p", "CHORUS", "-l", "wave5_review_bytes",
                "-o", str(args.evidence / "prepared"), "--replace"]
    exec(compile(code, str(BUILDER), "exec"), {"__name__": "__main__", "__file__": str(BUILDER)})


def compare_bytes(args):
    # All imported production code and model-facing resources must still match
    # the base. Only the builder is swapped; tests/helper files are not imported.
    changed = subprocess.check_output(
        ["git", "diff", "--name-only", args.base, "--", "src", ".claude", "data", "pyproject.toml", "poetry.lock"], cwd=ROOT,
    ).decode().strip()
    assert not changed, f"base comparison needs identical dependencies/resources: {changed}"
    files = ("registration_chorus_wave5_review_bytes.json", "roster_wave5_review_bytes.json")
    captures = {}
    for label, ref in (("base", args.base), ("head", "WORKTREE")):
        command = [sys.executable, str(Path(__file__).resolve()), "build", "--ref", ref,
                   "--evidence", str(args.evidence)]
        result = subprocess.run(command, cwd=ROOT, env=environment(), capture_output=True, text=True, timeout=120)
        (args.evidence / f"build-{label}.log").write_text(result.stdout + result.stderr)
        assert result.returncode == 0, result.stdout + result.stderr
        captures[label] = {}
        for name in files:
            raw = (args.evidence / "prepared" / name).read_bytes()
            (args.evidence / f"{label}-{name}").write_bytes(raw)
            captures[label][name] = raw
    assert captures["base"] == captures["head"], "registration/roster bytes differ"
    report = {"base": args.base, "equal": True, "artifacts": {
        name: {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
        for name, raw in captures["head"].items()}}
    (args.evidence / "bytes.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("mutations", "compare-bytes", "build"))
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument("--basetemp", type=Path, default=ROOT / ".codex-pt")
    parser.add_argument("--base", default=BASE)
    parser.add_argument("--ref", default="WORKTREE")
    parser.add_argument("--case", action="append")
    args = parser.parse_args()
    args.evidence = args.evidence.resolve()
    args.evidence.mkdir(parents=True, exist_ok=True)
    {"mutations": mutations, "compare-bytes": compare_bytes, "build": build_at_ref}[args.action](args)


if __name__ == "__main__":
    main()
