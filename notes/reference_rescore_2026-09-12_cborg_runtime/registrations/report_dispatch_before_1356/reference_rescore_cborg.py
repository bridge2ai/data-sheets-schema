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
DATE = "2026-09-12_cborg_runtime"
TRANSPORT = {
    "provider": "LBL CBORG",
    "base_url": "https://api.cborg.lbl.gov",
    "credential_source": "CBORG_API_KEY",
    "runtime": "Claude Code via CBORG Anthropic-compatible API",
    "runtime_version": "2.1.269 (Claude Code)",
    "additional_cli_flags": [],
    "credential_isolation": "fresh .cborg-cli-config directory inside each isolated rating workspace",
    "required_tools": ["Bash", "Read", "Write"],
    "runtime_model_identifier": "claude-opus-5",
    "output_model_identity_basis": "Configured API identifier, independently checked against returned CLI/runtime evidence; not model self-identification of weights.",
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
            "CLAUDE_CODE_SIMPLE", "CLAUDE_CONFIG_DIR",
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
    validate = runner.validate_candidate
    scoring_prompt = runner.job_prompt

    def prompt_with_execution_metadata(manifest, job):
        identity = manifest["transport"]["runtime_model_identifier"]
        return scoring_prompt(manifest, job) + (
            "\nExecution metadata supplied by the launcher (outside the record):\n"
            "The model fields in this evaluation identify the configured API/runtime identifier. "
            "They are execution provenance, not an introspective claim about underlying model weights. "
            "Use the supplied canonical identifier for model.name and model.evaluator_model; "
            "do not substitute a remembered training identity or the record's generator identity. "
            "The retained runtime trace will independently check these values and reject any actual route mismatch.\n"
            + json.dumps({"provider": manifest["transport"]["provider"],
                          "requested_selector": manifest["requested_model"],
                          "model.name": identity, "model.evaluator_model": identity,
                          "model.model_identity_note": "API/runtime identifier supplied by the launcher and verified against the retained runtime trace; not an identification of underlying weights."}, indent=2)
            + "\nAll scoring criteria, evidence requirements and the definition check above remain unchanged.\n"
        )

    def validate_with_transport(path, job, manifest, events):
        verify_runtime_transport(events)
        return validate(path, job, manifest, events)

    runner.validate_candidate = validate_with_transport
    runner.job_prompt = prompt_with_execution_metadata
    return runner


def verify_runtime_transport(events: list[dict]) -> None:
    initializers = [e for e in events if e.get("type") == "system" and e.get("subtype") == "init"]
    if len(initializers) != 1:
        raise ValueError("missing or ambiguous evaluator initialization")
    init = initializers[0]
    if not set(TRANSPORT["required_tools"]).issubset(init.get("tools") or []):
        raise ValueError("evaluator initialization is missing a required tool")
    if init.get("apiKeySource") != "ANTHROPIC_API_KEY":
        raise ValueError("evaluator did not select the explicit API key")
    if init.get("claude_code_version") != TRANSPORT["runtime_version"].split()[0]:
        raise ValueError("evaluator initialization has an unexpected CLI version")


def freeze(runner):
    manifest = runner.freeze()
    manifest["transport"] = TRANSPORT
    manifest["issue"] = 1343
    manifest["condition_boundary"] = {
        "reason": "#1343: use configured and returned API/runtime identifiers for provenance after two preliminary sessions self-identified differently. The scoring definitions stay fixed; all 56 prompts receive identical execution metadata in a fresh output condition.",
        "previous_registration": "notes/reference_rescore_2026-09-12_cborg/manifest.json",
        "previous_registration_sha256": runner.digest(ROOT / "notes/reference_rescore_2026-09-12_cborg/manifest.json"),
        "prior_measurements": "Preserved; the one accepted preliminary canary and all failed attempts remain separate and are not counted among this condition's 56 ratings.",
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
    # --bare removes Write even when --tools explicitly requests it (#1340).
    # Safe/restricted modes still suppress customizations and confine tools.
    # The parent runner owns and removes this fresh temporary workspace.
    config = Path.cwd() / ".cborg-cli-config"
    config.mkdir(mode=0o700)
    env["CLAUDE_CONFIG_DIR"] = str(config)
    os.execve(executable, [executable, *args], env)


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
