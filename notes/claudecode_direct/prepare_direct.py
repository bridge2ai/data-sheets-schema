"""Prepare one registered generation job for the direct arm (#2202).

The direct arm is Claude Code on the maintainer's Claude subscription,
talking to Anthropic directly: no local proxy, no CBORG, no ledger. It keeps
the v10 controls that hook the runtime rather than the provider (the
command and file policies, phase history, transcript observation, every
record and receipt gate) and reports cost from the runtime's own terminal
accounting, which is an estimate, not a metered charge.

Preparation is offline: it renders the exact instruction the run will
receive, records the input identity and the runtime pins, and never makes a
model call. The registration lives in a fresh directory; it names its
repository, which must be the checkout this script runs from, and it never
reads or writes anything belonging to the CBORG arms.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CONTROLS = ROOT / "notes" / "matched_cborg_2026-09-13"
sys.path[:0] = [str(ROOT / "src"), str(CONTROLS), str(CONTROLS / "native_controls")]

import prepare_registration as generation           # noqa: E402  the shared job renderer
from native_command_policy import build_command_policy  # noqa: E402
from run_api_canary import sha                       # noqa: E402

METHOD = "claudecode_direct"
RUNTIME = "Claude Code (direct)"
PROVIDER = "Anthropic (Claude subscription, direct)"
MODEL = "claude-opus-5"
EFFORT = "max"
EXECUTION_ARM = "direct"
#: The playbooks the instruction reaches; the transcript observer and the
#: record gates need nothing else from the toolchain.
CLI_FLAGS = ["--print", "--safe-mode", "--restricted", "--strict-mcp-config", "--disable-slash-commands",
             "--no-session-persistence", "--prompt-suggestions", "false", "--output-format", "stream-json",
             "--verbose", "--permission-mode", "dontAsk", "--tools", "Read,Write,Bash"]
#: `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` is the name the 2.1.272 binary
#: reads (#2207); the older spelling is kept for the records that carry it.
CHILD_ENVIRONMENT = {"DISABLE_NON_ESSENTIAL_MODEL_CALLS": "1", "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
                     "DISABLE_TELEMETRY": "1", "CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS": "1",
                     # An isolated config directory would otherwise look for a
                     # keychain item suffixed by that directory and find no
                     # login. Set and empty, this makes the runtime use the
                     # maintainer's own login item. No token enters the env.
                     "CLAUDE_SECURESTORAGE_CONFIG_DIR": ""}
#: Never present in the child's environment: the run must authenticate by the
#: maintainer's login, never by a key, and must never be redirected.
FORBIDDEN_ENVIRONMENT = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL", "CBORG_API_KEY",
                         "CLAUDE_CODE_OAUTH_TOKEN", "ANTHROPIC_CUSTOM_HEADERS", "CLAUDE_CODE_USE_BEDROCK",
                         "CLAUDE_CODE_USE_VERTEX", "CLAUDE_CODE_USE_FOUNDRY", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY")
#: What the launcher's own process may pass through to the child.
PARENT_PASSTHROUGH = ("PATH", "HOME", "USER", "SHELL", "TMPDIR", "LANG", "LC_ALL", "TERM")
#: The runtime's own auxiliary calls (titles, summaries) use a second model
#: (#2207). They are not the datasheet's model; they are recorded, and any
#: model outside this set fails the run.
AUXILIARY_MODELS = ("claude-haiku-4-5", "claude-haiku-4-5-20251001")


class DirectStop(RuntimeError):
    pass


def git_head(repository):
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repository, text=True).strip()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as out:
        json.dump(value, out, indent=2)
        out.write("\n")


def child_environment(config_dir, registered=None, per_job=None):
    """The child's exact environment: the parent's pass-through names, the
    registered child environment, the job's variables and the isolated
    config directory. Every forbidden name is refused wherever it comes from
    (#2204), and a registered environment must equal the preparer's."""
    if registered is not None and registered != CHILD_ENVIRONMENT:
        raise DirectStop("the registered child environment differs from the preparer's")
    env = {k: v for k, v in os.environ.items() if k in PARENT_PASSTHROUGH}
    env.update(CHILD_ENVIRONMENT)
    env.update(per_job or {})
    env.update(CLAUDE_CONFIG_DIR=str(config_dir))
    present = sorted(name for name in FORBIDDEN_ENVIRONMENT if name in env)
    if present:
        raise DirectStop("the child environment must not carry provider keys or redirection: " + ", ".join(present))
    return env


def auth_evidence(executable, env):
    """What the runtime reports about the login it will use, in the child's
    exact environment: method, plan and provider only. No token, email or
    organisation is recorded."""
    raw = subprocess.check_output([executable, "auth", "status", "--json"], env=env, text=True, timeout=60)
    status = json.loads(raw)
    keep = {k: status.get(k) for k in ("loggedIn", "authMethod", "apiProvider", "subscriptionType")}
    if keep != {"loggedIn": True, "authMethod": "claude.ai", "apiProvider": "firstParty", "subscriptionType": "max"}:
        raise DirectStop(f"the runtime is not on the maintainer's claude.ai login: {keep}")
    return keep


def build(args):
    repository = ROOT
    if Path.cwd().resolve() != repository:
        raise DirectStop("prepare from the checkout root that the registration will name")
    executable = Path(args.claude_executable).resolve(strict=True)
    version = subprocess.check_output([str(executable), "--version"], text=True).strip()
    registry = generation.load_registry(repository / "data/preprocessed/source_manifest.yaml")
    project = args.project
    bundle = registry.bundle(project)
    case = {"project": project, "manifest": str(registry.path), "bundle": str(bundle),
            "chunks": str(generation.chunking.manifest_for(bundle, source_manifest=registry.path)),
            "profile": "bridge2ai", "replicates": 1, "purpose": "direct_arm_canary",
            "shared_source_project": registry.shared_source_project(project)}
    mapping = generation.chunking.load_manifest(Path(case["chunks"]))
    generation.chunking.validate_manifest_mapping(mapping, Path(case["bundle"]).read_bytes(), mapping["bundle"])
    identifier = f"{project}_{EXECUTION_ARM}_rep1"
    job = {**case, "id": identifier, "execution_arm": EXECUTION_ARM, "runtime": RUNTIME, "method": METHOD,
           "replicate": 1, "canary": True, "run_date": args.run_date, "render_version": args.render_version,
           "label": f"{args.label_date}_{MODEL}-{EXECUTION_ARM}-{args.cohort.replace('_', '-')}-{project.lower()}_rep1"}
    spec = generation.api_runner.RunSpec(
        project=project, arm="baseline", method=METHOD, bundle=Path(case["bundle"]), label=job["label"],
        condition=args.condition, manifest=Path(case["manifest"]), chunk_manifest=Path(case["chunks"]),
        profile=case["profile"], profile_basis="stated by the registered caller",
        render_version=args.render_version, run_date=args.run_date,
        runtime=RUNTIME, provider=PROVIDER, reasoning_effort=EFFORT)
    if not spec.is_agentic:
        raise DirectStop("the direct arm must render the agentic instruction")
    output = args.output.resolve()
    if output.exists():
        raise DirectStop(f"registration directory already exists: {output}")
    job["output_directory"] = str(spec.metadata_dir)
    job["output_directories"] = sorted({str(spec.full_path.parent), str(spec.core_path.parent)})
    if any(Path(p).exists() for p in job["output_directories"]):
        raise DirectStop("planned output directory already exists; never overwrite an earlier run")
    instruction = output / "prompts" / f"{identifier}.md"
    instruction.parent.mkdir(parents=True)
    instruction.write_text(spec.instruction, encoding="utf-8")
    job.update(render_spec=spec.render_spec(), input_identity=spec.input_identity(),
               instruction=str(instruction), instruction_sha256=sha(instruction),
               outputs={"full": str(spec.full_path), "core": str(spec.core_path),
                        "provenance": str(spec.provenance_path), "report": str(spec.report_path)})
    if "--reasoning-effort " + EFFORT not in spec.instruction:
        raise DirectStop("the rendered recorder line does not assert the registered effort")
    if (f"# Provider: {PROVIDER}" not in spec.instruction or f"# Agent runtime: {RUNTIME}" not in spec.instruction
            or f"# Model: {MODEL}" not in spec.instruction):
        raise DirectStop("the rendered header does not state the direct arm's runtime, provider and model")
    python = sys.executable
    policy = build_command_policy(job, python, str(repository))
    system_prompt = HERE / "system.md"
    pins = {}
    for directory, suffixes in [(repository / "src/data_sheets_schema", {".py", ".yaml", ".json"}),
                                (repository / ".claude/agents", {".md"}), (repository / ".claude/commands", {".md"}),
                                (repository / "src/download/prompts", {".md", ".json", ".yaml"})]:
        for path in sorted(directory.rglob("*")):
            if path.is_file() and path.suffix in suffixes:
                pins[str(path)] = sha(path)
    for path in [repository / "pyproject.toml", repository / "poetry.lock", CONTROLS / "prepare_registration.py",
                 CONTROLS / "run_api_canary.py", CONTROLS / "budgeted_cborg.py",
                 *sorted((CONTROLS / "native_controls").glob("*.py")), CONTROLS / "native_controls" / "system.md",
                 HERE / "prepare_direct.py", HERE / "run_direct_canary.py", HERE / "bind_direct_launch.py",
                 system_prompt, instruction,
                 Path(case["manifest"]), Path(case["bundle"]), Path(case["chunks"]), executable]:
        pins[str(path)] = sha(path)
    per_job = {"D4D_MANIFEST": case["manifest"], "D4D_PROFILE": case["profile"], "D4D_LAUNCH_INSTRUCTION": str(instruction)}
    # The login is probed in the child's exact environment, in a throwaway
    # configuration directory that leaves nothing behind.
    probe_config = output / "auth_probe_config"
    probe_config.mkdir(mode=0o700)
    try:
        auth = auth_evidence(str(executable), child_environment(probe_config, CHILD_ENVIRONMENT, per_job))
    finally:
        shutil.rmtree(probe_config, ignore_errors=True)
    registration = {
        "kind": "d4d_direct_arm_registration", "schema_version": 1,
        "registered_at": datetime.now(timezone.utc).isoformat(), "status": "prepared_awaiting_review_ci_and_launch_word",
        "arm": {"method": METHOD, "runtime": RUNTIME, "provider": PROVIDER, "execution_arm": EXECUTION_ARM,
                "transport": "the runtime's own connection to Anthropic; no proxy, no CBORG endpoint, no ledger",
                "cost_basis": "the runtime's terminal accounting (usage and its own cost estimate); not metered per request"},
        "repository": str(repository), "code_commit": git_head(repository),
        "python": python, "python_version": sys.version,
        "model": {"model": MODEL, "effort": EFFORT, "auxiliary_models_permitted": list(AUXILIARY_MODELS),
                  "effort_basis": "asserted by the launcher through --effort and recorded through --reasoning-effort; "
                                  "checked after the run against the effort the runtime reports on every tool callback"},
        "native_runtime": {"executable": str(executable), "version": version,
                           "cli_flags": CLI_FLAGS + ["--effort", EFFORT], "environment": CHILD_ENVIRONMENT,
                           "forbidden_environment": list(FORBIDDEN_ENVIRONMENT),
                           "expected_api_key_source": "none",
                           "auth": auth, "system_prompt": str(system_prompt)},
        "generation": {"condition": args.condition, "render_version": args.render_version,
                       "attempt_deadline_seconds": args.deadline_seconds,
                       "runaway_budget_guard_usd": str(args.runaway_guard_usd),
                       "runaway_guard_basis": "passed to --max-budget-usd so the runtime stops itself on its own estimate; "
                                              "not a metered cap and not a charge against any allocation",
                       "jobs": [job], "canary_order": [identifier]},
        "isolation": {"writes_only_under": job["output_directories"] + ["the attempt directory beside this registration"],
                      "never_touches": ["any CBORG ledger or sequence owner", "any matched_cborg registration or attempt directory",
                                        "claudecode_agent and claudecode_api records"],
                      "config_dir": "a fresh directory per attempt under the attempt directory",
                      "shared_credential_store": "the maintainer's claude.ai login item in the login keychain, which a "
                                                 "token refresh during the run may rewrite (#2208)"},
        "per_job_command_policy": {identifier: policy},
        "per_job_environment": {identifier: per_job},
        "pinned_files": pins,
    }
    path = output / "registration.json"
    save(path, registration)
    print(json.dumps({"registration": str(path), "sha256": sha(path), "job": identifier, "label": job["label"],
                      "instruction_bytes": len(spec.instruction.encode()), "pins": len(pins), "auth": auth}, indent=2))
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="a fresh registration directory")
    parser.add_argument("--project", default="CHORUS")
    parser.add_argument("--claude-executable", default=str(Path.home() / ".local/share/claude/versions/2.1.272"))
    parser.add_argument("--condition", default="generic_v9")
    parser.add_argument("--render-version", type=int, default=17)
    parser.add_argument("--cohort", default="generalized_direct_v1")
    parser.add_argument("--label-date", default=datetime.now(timezone.utc).date().isoformat())
    parser.add_argument("--run-date", default=datetime.now(timezone.utc).date().isoformat())
    parser.add_argument("--deadline-seconds", type=int, default=21600)
    parser.add_argument("--runaway-guard-usd", default="60")
    build(parser.parse_args())


if __name__ == "__main__":
    main()
