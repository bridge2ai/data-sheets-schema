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
import re
import shutil
import subprocess
import sys
import tempfile

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
#: The cohort a production registration carries unless one is given; the
#: fixture tests use another, so their label can never collide with a real
#: record's (#2218, #2228).
DEFAULT_COHORT = "generalized_direct_v1"
#: The playbooks the instruction reaches; the transcript observer and the
#: record gates need nothing else from the toolchain.
CLI_FLAGS = ["--print", "--safe-mode", "--restricted", "--strict-mcp-config", "--disable-slash-commands",
             "--no-session-persistence", "--prompt-suggestions", "false", "--output-format", "stream-json",
             "--verbose", "--permission-mode", "dontAsk", "--tools", "Read,Write,Bash"]
#: `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` is the name the 2.1.272 binary
#: reads (#2207); the older spelling is kept for the records that carry it.
CHILD_ENVIRONMENT = {"DISABLE_NON_ESSENTIAL_MODEL_CALLS": "1", "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
                     "DISABLE_TELEMETRY": "1", "CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS": "1",
                     # The runtime is asked for the 200k build the native arm
                     # observed, not the 1M one it reports as `claude-opus-5[1m]`
                     # (#2266); whether it honours this on the subscription is
                     # observed only by the first run.
                     "CLAUDE_CODE_DISABLE_1M_CONTEXT": "1",
                     # An isolated config directory would otherwise look for a
                     # keychain item suffixed by that directory and find no
                     # login. Set and empty, this makes the runtime use the
                     # maintainer's own login item. No token enters the env.
                     "CLAUDE_SECURESTORAGE_CONFIG_DIR": ""}
#: Never present in the child's environment: the run must authenticate by the
#: maintainer's login, never by a key, and must never be redirected. A second
#: layer behind `PER_JOB_NAMES` (#2244), and what the launcher refuses in its
#: own parent environment. Built from a string scan of the pinned 2.1.272
#: binary (#2270): credentials and tokens, base URLs and cloud-provider
#: switches, proxies in every spelling, TLS and certificate overrides,
#: settings and config paths, model, effort and token overrides. Not claimed
#: complete. `CBORG_API_KEY` is policy, not something the binary reads: the
#: CBORG arms' key must never be near this arm. `CLAUDE_EFFORT` is deliberately
#: absent: the recorder reads it to corroborate a header and a maintainer's
#: shell may carry it; the child never receives it, since it is not a
#: pass-through name.
FORBIDDEN_ENVIRONMENT = (
    # credentials and tokens
    "ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "CLAUDE_API_KEY", "CLAUDE_CODE_OAUTH_TOKEN",
    "CLAUDE_CODE_OAUTH_REFRESH_TOKEN", "CLAUDE_CODE_SESSION_ACCESS_TOKEN", "CLAUDE_CODE_GATEWAY_TOKEN",
    "CLAUDE_CODE_OAUTH_TOKEN_FILE_DESCRIPTOR", "CLAUDE_CODE_API_KEY_FILE_DESCRIPTOR", "CBORG_API_KEY",
    "AWS_BEARER_TOKEN_BEDROCK", "ANTHROPIC_FOUNDRY_API_KEY", "ANTHROPIC_FOUNDRY_AUTH_TOKEN", "ANTHROPIC_AWS_API_KEY",
    # base URLs, hosts and cloud-provider switches
    "ANTHROPIC_BASE_URL", "ANTHROPIC_API_HOST", "CLAUDE_CODE_API_BASE_URL", "ANTHROPIC_BEDROCK_BASE_URL",
    "ANTHROPIC_VERTEX_BASE_URL", "ANTHROPIC_FOUNDRY_BASE_URL", "ANTHROPIC_AWS_BASE_URL",
    "ANTHROPIC_GOOGLE_CLOUD_BASE_URL", "ANTHROPIC_BEDROCK_MANTLE_BASE_URL", "ANTHROPIC_CUSTOM_HEADERS",
    "CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX", "CLAUDE_CODE_USE_FOUNDRY",
    "CLAUDE_CODE_SKIP_BEDROCK_AUTH", "CLAUDE_CODE_SKIP_VERTEX_AUTH", "CLAUDE_CODE_SKIP_FOUNDRY_AUTH",
    "CLAUDE_CODE_SKIP_ANTHROPIC_AWS_AUTH", "CLAUDE_CODE_SKIP_MANTLE_AUTH",
    # proxies, in every spelling the binary reads
    "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY", "http_proxy", "https_proxy", "all_proxy", "no_proxy",
    "GLOBAL_AGENT_HTTP_PROXY", "GLOBAL_AGENT_HTTPS_PROXY", "GLOBAL_AGENT_NO_PROXY",
    "CLAUDE_CODE_PROXY_URL", "CLAUDE_CODE_HTTP_PROXY", "CLAUDE_CODE_HTTPS_PROXY",
    # TLS and certificates
    "NODE_EXTRA_CA_CERTS", "NODE_TLS_REJECT_UNAUTHORIZED", "NODE_USE_SYSTEM_CA", "SSL_CERT_FILE", "SSL_CERT_DIR",
    "CLAUDE_CODE_CLIENT_CERT", "CLAUDE_CODE_CLIENT_KEY", "CLAUDE_CODE_CLIENT_KEY_PASSPHRASE", "CLAUDE_CODE_CERT_STORE",
    # settings, config and process options
    "CLAUDE_CODE_MANAGED_SETTINGS_PATH", "CLAUDE_CODE_REMOTE_SETTINGS_PATH", "ANTHROPIC_CONFIG_DIR", "ANTHROPIC_BETAS",
    "NODE_OPTIONS",
    # model, effort and token overrides
    "ANTHROPIC_MODEL", "ANTHROPIC_DEFAULT_MODEL", "ANTHROPIC_DEFAULT_OPUS_MODEL", "ANTHROPIC_DEFAULT_SONNET_MODEL",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL", "ANTHROPIC_DEFAULT_FABLE_MODEL", "ANTHROPIC_SMALL_FAST_MODEL",
    "ANTHROPIC_CUSTOM_MODEL_OPTION", "CLAUDE_CODE_SUBAGENT_MODEL", "CLAUDE_CODE_SUBAGENT_MODEL_FORCE",
    "CLAUDE_CODE_EFFORT_LEVEL", "CLAUDE_CODE_MAX_OUTPUT_TOKENS", "CLAUDE_CODE_MAX_CONTEXT_TOKENS",
    "MAX_THINKING_TOKENS")
#: A job id is one path component of this shape (#2252, #2276): it names the
#: attempt directory and nothing else may. The preparer refuses to mint one
#: that is not, so the launcher's refusal is never the first.
JOB_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]*")
#: What the launcher's own process may pass through to the child.
PARENT_PASSTHROUGH = ("PATH", "HOME", "USER", "SHELL", "TMPDIR", "LANG", "LC_ALL", "TERM")
#: The only names a registration's job may add to the child's environment
#: (#2244): what the recorder reads to find the manifest, the profile and the
#: launch instruction. Any other name is refused whatever its value, so a
#: registration cannot add a proxy, a base URL, a TLS or model override, or
#: shadow a registered constant.
PER_JOB_NAMES = ("D4D_MANIFEST", "D4D_PROFILE", "D4D_LAUNCH_INSTRUCTION")
#: What the runtime is expected to report as the registered model's limits
#: (#2246): the native registration's offline observation of the same model
#: through CBORG (`native_controls/prepare_overlay.py`). Asserted, not
#: observed on this transport, until the first run; a difference is a
#: validation problem, since a different context window is a different
#: instrument.
EXPECTED_LIMITS = {"contextWindow": 200000, "maxOutputTokens": 64000}
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
    (#2204), the job may add only `PER_JOB_NAMES` (#2244), and a registered
    environment must equal the preparer's."""
    if registered is not None and registered != CHILD_ENVIRONMENT:
        raise DirectStop("the registered child environment differs from the preparer's")
    per_job = dict(per_job or {})
    forbidden = sorted(name for name in FORBIDDEN_ENVIRONMENT if name in per_job)
    if forbidden:
        raise DirectStop("the child environment must not carry provider keys or redirection: " + ", ".join(forbidden))
    unexpected = sorted(set(per_job) - set(PER_JOB_NAMES))
    if unexpected:
        raise DirectStop("a job may add only " + ", ".join(PER_JOB_NAMES)
                         + " to the child's environment; refused: " + ", ".join(unexpected))
    if not all(isinstance(value, str) for value in per_job.values()):
        raise DirectStop("a job's environment values must be strings")
    env = {k: v for k, v in os.environ.items() if k in PARENT_PASSTHROUGH}
    env.update(CHILD_ENVIRONMENT)
    env.update(per_job)
    env.update(CLAUDE_CONFIG_DIR=str(config_dir))
    # Reached only if a constant above is edited to admit one: kept as the
    # last check on the environment as assembled.
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
    project = args.project
    identifier = f"{project}_{EXECUTION_ARM}_rep1"
    if not JOB_ID.fullmatch(identifier):
        raise DirectStop(f"the job id minted for project {project!r} is not a single path component")
    registry = generation.load_registry(repository / "data/preprocessed/source_manifest.yaml")
    bundle = registry.bundle(project)
    case = {"project": project, "manifest": str(registry.path), "bundle": str(bundle),
            "chunks": str(generation.chunking.manifest_for(bundle, source_manifest=registry.path)),
            "profile": "bridge2ai", "replicates": 1, "purpose": "direct_arm_canary",
            "shared_source_project": registry.shared_source_project(project)}
    mapping = generation.chunking.load_manifest(Path(case["chunks"]))
    generation.chunking.validate_manifest_mapping(mapping, Path(case["bundle"]).read_bytes(), mapping["bundle"])
    job = {**case, "id": identifier, "execution_arm": EXECUTION_ARM, "runtime": RUNTIME, "method": METHOD,
           "replicate": 1, "canary": True, "run_date": args.run_date, "render_version": args.render_version,
           "label": f"{args.label_date}_{MODEL}-{EXECUTION_ARM}-{args.cohort.replace('_', '-')}-{project.lower()}_rep1"}
    try:
        spec = generation.api_runner.RunSpec(
            project=project, arm="baseline", method=METHOD, bundle=Path(case["bundle"]), label=job["label"],
            condition=args.condition, manifest=Path(case["manifest"]), chunk_manifest=Path(case["chunks"]),
            profile=case["profile"], profile_basis="stated by the registered caller",
            render_version=args.render_version, run_date=args.run_date,
            runtime=RUNTIME, provider=PROVIDER, reasoning_effort=EFFORT, prompt_text_env=True)
    except ValueError as error:
        # Includes the key's refusal outside agentic renderers 9 and later
        # (#2313), which is how a non-agentic rendering is refused (#2324).
        raise DirectStop(f"the direct arm's rendering specification is refused: {error}") from error
    output = args.output.resolve()
    if output.exists():
        raise DirectStop(f"registration directory already exists: {output}")
    limits = {"contextWindow": int(args.context_window), "maxOutputTokens": int(args.max_output_tokens)}
    if any(value <= 0 for value in limits.values()):
        raise DirectStop("the expected runtime limits must be positive")
    limits_basis = ("the preparer's defaults: the native registration's offline observation of the same model "
                    "through CBORG; not observed on this transport until the first run (#2246)"
                    if limits == EXPECTED_LIMITS else
                    "given on the preparer's command line (--context-window / --max-output-tokens); not the native "
                    "registration's observation and not observed on this transport until the first run (#2267)")
    # Every check on the rendering runs before anything is written (#2317).
    if "--reasoning-effort " + EFFORT not in spec.instruction:
        raise DirectStop("the rendered recorder line does not assert the registered effort")
    if (f"# Provider: {PROVIDER}" not in spec.instruction or f"# Agent runtime: {RUNTIME}" not in spec.instruction
            or f"# Model: {MODEL}" not in spec.instruction):
        raise DirectStop("the rendered header does not state the direct arm's runtime, provider and model")
    recorder = [line for line in spec.instruction.splitlines() if " -m data_sheets_schema.cli provenance record" in line]
    # The runtime refuses a prescribed line carrying a shell expansion under
    # dontAsk (#2282). It also refused, in every ending, a line whose
    # specification carried a manifest path with an apostrophe (twice in the
    # specification, quoted by the shell as '"'"'), while admitting one
    # apostrophe in a small specification. The trigger is the runtime's brace
    # check on an argument joined from quoted pieces, which the command
    # policy's literal check now models (#2308, #2399); refusing any
    # apostrophe here stays as a second layer. Either would disqualify the
    # run at its last step.
    if not recorder or any("${" in line or "--prompt-text-env D4D_LAUNCH_INSTRUCTION" not in line for line in recorder):
        raise DirectStop("the rendered recorder line must read the launch instruction by --prompt-text-env, with no shell expansion")
    if "'" in json.dumps(spec.render_spec()):
        raise DirectStop("the render specification carries an apostrophe, which the runtime refuses in a prescribed line")
    job["output_directory"] = str(spec.metadata_dir)
    job["output_directories"] = sorted({str(spec.full_path.parent), str(spec.core_path.parent)})
    if any(Path(p).exists() for p in job["output_directories"]):
        raise DirectStop("planned output directory already exists; never overwrite an earlier run")
    instruction = output / "prompts" / f"{identifier}.md"
    per_job = {"D4D_MANIFEST": case["manifest"], "D4D_PROFILE": case["profile"], "D4D_LAUNCH_INSTRUCTION": str(instruction)}
    assert set(per_job) == set(PER_JOB_NAMES)
    # The login is probed in the child's exact environment, in a throwaway
    # configuration directory beside the registration directory, before
    # anything of the registration is written: a refused login leaves
    # nothing behind (#2317).
    output.parent.mkdir(parents=True, exist_ok=True)
    probe_config = Path(tempfile.mkdtemp(prefix=f".{output.name}.auth-probe-", dir=output.parent))
    try:
        auth = auth_evidence(str(executable), child_environment(probe_config, CHILD_ENVIRONMENT, per_job))
    finally:
        shutil.rmtree(probe_config, ignore_errors=True)
    instruction.parent.mkdir(parents=True)
    python = sys.executable
    try:
        instruction.write_text(spec.instruction, encoding="utf-8")
        job.update(render_spec=spec.render_spec(), input_identity=spec.input_identity(),
                   instruction=str(instruction), instruction_sha256=sha(instruction),
                   outputs={"full": str(spec.full_path), "core": str(spec.core_path),
                            "provenance": str(spec.provenance_path), "report": str(spec.report_path)})
        policy = build_command_policy(job, python, str(repository))
    except ValueError as error:
        # A registered spelling the runtime would refuse, or any policy that
        # cannot be built, leaves nothing behind (#2317, #2369): the
        # registration directory did not exist before this call.
        shutil.rmtree(output, ignore_errors=True)
        raise DirectStop(f"the registered command policy cannot be built: {error}") from error
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
                                  "checked after the run against the effort the runtime reports on every tool callback",
                  "limits_expected": limits, "limits_basis": limits_basis},
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


def parser():
    """The command line, as a factory so a test can parse through the real one (#2258)."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="a fresh registration directory")
    parser.add_argument("--project", default="CHORUS")
    parser.add_argument("--claude-executable", default=str(Path.home() / ".local/share/claude/versions/2.1.272"))
    parser.add_argument("--condition", default="generic_v9")
    parser.add_argument("--render-version", type=int, default=17)
    parser.add_argument("--cohort", default=DEFAULT_COHORT)
    parser.add_argument("--label-date", default=datetime.now(timezone.utc).date().isoformat())
    parser.add_argument("--run-date", default=datetime.now(timezone.utc).date().isoformat())
    parser.add_argument("--deadline-seconds", type=int, default=21600)
    parser.add_argument("--runaway-guard-usd", default="60")
    parser.add_argument("--context-window", type=int, default=EXPECTED_LIMITS["contextWindow"],
                        help="the context window the runtime is expected to report for the registered model (#2246)")
    parser.add_argument("--max-output-tokens", type=int, default=EXPECTED_LIMITS["maxOutputTokens"])
    return parser


def main():
    build(parser().parse_args())


if __name__ == "__main__":
    main()
