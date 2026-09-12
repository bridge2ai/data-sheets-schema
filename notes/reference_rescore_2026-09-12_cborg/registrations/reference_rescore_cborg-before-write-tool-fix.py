#!/usr/bin/env python3
"""Run the separately registered CBORG reference rescore without replacing v7/v8 scores.

The existing reference runner supplies the frozen prompts and acceptance gates.
This adapter gives the new provider condition its own manifest and output paths,
and acts as the evaluator executable so every session uses CBORG explicitly.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
DATE = "2026-09-12_cborg"
TRANSPORT = {
    "provider": "LBL CBORG",
    "base_url": "https://api.cborg.lbl.gov",
    "credential_source": "CBORG_API_KEY",
    "runtime": "Claude Code via CBORG Anthropic-compatible API",
    "runtime_version": "2.1.269 (Claude Code)",
    "additional_cli_flags": ["--bare"],
    "environment": {
        "DISABLE_NON_ESSENTIAL_MODEL_CALLS": "1",
        "DISABLE_TELEMETRY": "1",
        "CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS": "1",
    },
}


def cborg_environment(source: dict[str, str]) -> dict[str, str]:
    """Select CBORG explicitly; never use inherited direct-provider credentials."""
    key = source.get("CBORG_API_KEY")
    if not key:
        raise ValueError("CBORG_API_KEY is required; no provider fallback is permitted")
    env = dict(source)
    for name in list(env):
        if name.startswith("ANTHROPIC_") or name in {
            "CLAUDE_CODE_OAUTH_TOKEN", "CLAUDE_CODE_USE_BEDROCK",
            "CLAUDE_CODE_USE_VERTEX", "CLAUDE_CODE_USE_FOUNDRY",
            "CLAUDE_CODE_SUBAGENT_MODEL", "CLAUDECODE",
        }:
            env.pop(name)
    env.update(TRANSPORT["environment"])
    env["ANTHROPIC_API_KEY"] = key
    env["ANTHROPIC_BASE_URL"] = TRANSPORT["base_url"]
    return env


def load_runner():
    sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
    spec = importlib.util.spec_from_file_location("cborg_reference_runner", ROOT / "scripts/reference_rescore.py")
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    runner.ROOT = ROOT
    runner.DATE = DATE
    runner.PLAN = ROOT / f"notes/reference_rescore_{DATE}"
    return runner


def freeze(runner):
    manifest = runner.freeze()
    manifest["transport"] = TRANSPORT
    manifest["condition_boundary"] = {
        "reason": "User requested a separate rescore through the CBORG API on 2026-09-12.",
        "previous_registration": "notes/reference_rescore_2026-09-11/manifest.json",
        "previous_registration_sha256": runner.digest(ROOT / "notes/reference_rescore_2026-09-11/manifest.json"),
        "prior_measurements": "Preserved; do not pool or overwrite the earlier provider condition.",
        "semantic_limit": "Frozen rubric20 Q19 text-or-graph rule remains unchanged; mechanical acceptance is not semantic adjudication.",
    }
    for rel in ("scripts/reference_rescore_cborg.py", "src/data_sheets_schema/agent_pin.py"):
        manifest["pinned_files"][rel] = runner.digest(ROOT / rel)
    runner.write_json(runner.PLAN / "manifest.json", manifest)
    return manifest


def route_evaluator(args: list[str]) -> None:
    import subprocess

    executable = shutil.which("claude")
    if not executable:
        raise ValueError("Claude Code is unavailable")
    env = cborg_environment(dict(os.environ))
    version = subprocess.check_output([executable, "--version"], env=env, text=True).strip()
    if version != TRANSPORT["runtime_version"]:
        raise ValueError("Claude Code version differs from the registered transport")
    os.execve(executable, [executable, "--bare", *args], env)


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args[:1] == ["--print"]:
        route_evaluator(args)
        return 1  # execve cannot return on success.
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("freeze", "canary", "accept-canary", "remaining", "report", "audit"))
    parsed = parser.parse_args(args)
    runner = load_runner()
    if parsed.action == "freeze":
        manifest = freeze(runner)
        print(f"Registered {len(manifest['jobs'])} CBORG ratings; no calls made.")
        return 0
    manifest = json.loads((runner.PLAN / "manifest.json").read_bytes())
    if manifest.get("transport") != TRANSPORT:
        raise ValueError("transport differs from the registered CBORG condition")
    runner.verify_frozen(manifest)
    if parsed.action == "report":
        runner.report_results(manifest)
        return 0
    if parsed.action == "audit":
        import audit_reference_rescore as audit
        audit.r = runner
        sys.argv = [sys.argv[0]]
        return audit.main()
    if parsed.action == "accept-canary":
        review = runner.PLAN / "canary_review.md"
        if not review.is_file() or not review.read_text().strip():
            raise ValueError("write the inspected canary review before accepting it")
        runner.accept_canary(manifest)
        return 0
    cborg_environment(dict(os.environ))  # Refuse missing credentials before creating an attempt.
    jobs = manifest["jobs"][:1] if parsed.action == "canary" else manifest["jobs"]
    for job in jobs:
        if parsed.action == "remaining" and (ROOT / job["output"]).exists():
            runner.require_canary(manifest, job)
            runner.successful_receipt(manifest, job)
            continue
        if runner.run_job(manifest, job, str(Path(__file__).resolve()))["status"] != "passed":
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
