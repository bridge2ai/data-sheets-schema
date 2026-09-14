"""Prepare a reviewed, hash-bound experiment manifest without model calls."""
from datetime import datetime, timezone
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import yaml

from data_sheets_schema import api_runner, agent_pin, chunking, evidence_score, profiles, schema_digest
from data_sheets_schema.evaluation.evaluate_d4d_llm import D4DLLMEvaluator, LLMEvaluationConfig
from data_sheets_schema.registry import load_registry

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SERIES = "generalized_v10_2026-09-13"
PROJECTS = ["CHORUS", "AI_READI", "CM4AI", "VOICE", "VOICE_PEDIATRIC"]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    keep(path, json.dumps(value, indent=2) + "\n")


def keep(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_text(encoding="utf-8") != text:
            raise ValueError(f"refusing to replace changed registration artifact: {path}")
        return
    with path.open("x", encoding="utf-8") as stream:
        stream.write(text)


def spec_for(job):
    return api_runner.RunSpec(project=job["project"], arm="baseline", method=job["method"],
        bundle=Path(job["bundle"]), label=job["label"], condition="generic_v9",
        manifest=Path(job["manifest"]), chunk_manifest=Path(job["chunks"]),
        profile=job["profile"], profile_basis="stated by the registered caller",
        run_date=job.get("run_date", "2026-09-14"),
        runtime=job["runtime"], provider="LBL CBORG (proxy to Anthropic)")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=HERE)
    parser.add_argument("--cohort", default="generalized_v10")
    parser.add_argument("--label-date", default="2026-09-13")
    parser.add_argument("--run-date", default="2026-09-14")
    parser.add_argument("--prior-billing", type=Path)
    parser.add_argument("--prior-cost-usd")
    parser.add_argument("--previous-attempt-audit", type=Path)
    parser.add_argument("--per-job-attempt-caps", type=Path,
                        help="JSON mapping of explicitly approved job IDs to whole-attempt USD caps; preparation grants no launch approval")
    parser.add_argument("--render-only", action="store_true")
    args = parser.parse_args()
    output = args.output.resolve()
    if (args.prior_billing is None) != (args.prior_cost_usd is None):
        parser.error("prior billing and its registered total must be supplied together")
    registry = load_registry(ROOT / "data/preprocessed/source_manifest.yaml")
    cases = [{"project": p, "manifest": str(registry.path),
              "bundle": str(registry.bundle(p)),
              "chunks": str(chunking.manifest_for(registry.bundle(p), source_manifest=registry.path)),
              "profile": "bridge2ai", "replicates": 3, "purpose": "manuscript_cohort",
              "shared_source_project": registry.shared_source_project(p)}
             for p in PROJECTS]
    external = HERE / "external_clinical"
    kids = HERE / "kids_first"
    external_status = "awaiting_source_registration"
    if (kids / "manifest.yaml").is_file():
        kids_registry = load_registry(kids / "manifest.yaml")
        cases.append({"project": "KIDS_FIRST", "manifest": str(kids_registry.path),
                      "bundle": str(kids_registry.bundle("KIDS_FIRST")),
                      "chunks": str(kids / "chunks.yaml"), "profile": "neutral",
                      "replicates": 1, "purpose": "external_general_user_canary"})
        external_status = "registered"
    pins = {}
    # Full package implementation, schemas and shipped instructions are inputs.
    # Explicit rglob includes ignored files; compiled/cache files are not code.
    for directory, suffixes in [(ROOT / "src/data_sheets_schema", {".py", ".yaml", ".json"}),
                                (ROOT / ".claude/agents", {".md"}),
                                (ROOT / ".claude/commands", {".md"}),
                                (ROOT / "src/download/prompts", {".md", ".json"})]:
        for path in sorted(directory.rglob("*")):
            if path.is_file() and path.suffix in suffixes:
                pins[str(path)] = sha(path)
    for path in [ROOT / "pyproject.toml", ROOT / "poetry.lock",
                 ROOT / ".github/workflows/d4d_assistant_deterministic.config",
                 ROOT / "data/rubric/rubric10.txt", ROOT / "data/rubric/rubric20.txt",
                 HERE / "model_catalogue.json", HERE / "token_count_probe.json",
                 HERE / "budgeted_cborg.py", HERE / "run_api_canary.py", Path(__file__)]:
        pins[str(path)] = sha(path)
    if not args.render_only:
        pins[str(output / "api_initial_admission.json")] = sha(output / "api_initial_admission.json")
    if args.prior_billing:
        pins[str(args.prior_billing.resolve())] = sha(args.prior_billing)
    if args.previous_attempt_audit:
        pins[str(args.previous_attempt_audit.resolve())] = sha(args.previous_attempt_audit)
    if args.per_job_attempt_caps:
        cap_policy_bytes = args.per_job_attempt_caps.read_bytes()
        pins[str(args.per_job_attempt_caps.resolve())] = hashlib.sha256(cap_policy_bytes).hexdigest()
        per_job_attempt_caps = json.loads(cap_policy_bytes)
    for path in sorted(external.iterdir()):
        if path.is_file():
            pins[str(path)] = sha(path)
    if external_status == "registered":
        # Include ignored original responses as well as the extracted inputs.
        # Their bytes remain local; capture receipts expose their hashes.
        for path in sorted(kids.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                pins[str(path)] = sha(path)
    jobs = []
    for case in cases:
        for key in ("manifest", "bundle", "chunks"):
            pins[case[key]] = sha(case[key])
        mapping = chunking.load_manifest(Path(case["chunks"]))
        chunking.validate_manifest_mapping(mapping, Path(case["bundle"]).read_bytes(), mapping["bundle"])
        for replicate in range(1, case["replicates"] + 1):
            for arm, runtime, method in [("api", "Claude API (direct)", "claudecode_api"),
                                         ("agentic", "Claude Code", "claudecode_agent")]:
                identifier = f"{case['project']}_{arm}_rep{replicate}"
                job = {**case, "id": identifier, "execution_arm": arm, "runtime": runtime,
                       "method": method, "replicate": replicate,
                       "canary": replicate == 1 and case["project"] in {"CHORUS", "KIDS_FIRST"},
                       "run_date": args.run_date,
                       "label": f"{args.label_date}_claude-opus-5-{arm}-{args.cohort.replace('_','-')}-{case['project'].lower()}_rep{replicate}"}
                spec = spec_for(job)
                # Use the public CLI's corpus layout so provenance/receipt
                # helpers resolve the same full/core files as generation.
                # Dataset-qualified labels isolate each attempt's directories.
                job["output_directory"] = str(spec.metadata_dir)
                job["output_directories"] = sorted({str(spec.full_path.parent), str(spec.core_path.parent)})
                instruction = output / "prompts" / f"{identifier}.md"
                instruction.parent.mkdir(parents=True, exist_ok=True)
                keep(instruction, spec.instruction)
                pins[str(instruction)] = sha(instruction)
                job.update(render_spec=spec.render_spec(), input_identity=spec.input_identity(),
                           instruction=str(instruction), instruction_sha256=sha(instruction),
                           outputs={"full": str(spec.full_path), "core": str(spec.core_path),
                                    "provenance": str(spec.provenance_path), "report": str(spec.report_path)})
                if arm == "api":
                    job["offline_plan"] = api_runner.plan(spec)
                    request = api_runner.build_phase(spec, "full", carry={})
                    initial = output / "initial_requests" / f"{identifier}.json"
                    settings = api_runner._model_settings()
                    save(initial, {"model": settings["name"], "system": request.system,
                         "messages": request.messages, "thinking": settings.get("thinking"),
                         "max_tokens": api_runner.phase_max_tokens(spec, "full", settings["max_tokens"], model=settings["name"])})
                    pins[str(initial)] = sha(initial)
                    job["initial_request"] = str(initial)
                if any(Path(p).exists() for p in job["output_directories"]):
                    raise ValueError(f"planned output directory already exists: {identifier}")
                jobs.append(job)
    instruments = {}
    evaluator = D4DLLMEvaluator(LLMEvaluationConfig(model="claude-opus-5", max_tokens=32000), client=object())
    for n in (10, 20):
        for suffix in ("", "-semantic"):
            name = f"d4d-rubric{n}{suffix}"
            path = agent_pin.agent_path(name)
            instruments[name] = {"definition": str(path), "definition_sha256": sha(path),
                "preamble": agent_pin.spawn_preamble(name), "challenge": agent_pin.challenge(name),
                "rubric": str(ROOT / f"data/rubric/rubric{n}.txt"), "quoted_definition_sha256": None,
                "observed_runtime_model": None, "canary_status": "not_run"}
        text = evaluator._build_system_prompt(f"rubric{n}")
        path = output / "prompts" / f"rubric{n}_api_system.md"
        keep(path, text)
        pins[str(path)] = sha(path)
        instruments[f"rubric{n}_api_quality"] = {"system_prompt": str(path), "system_prompt_sha256": sha(path),
                                                  "max_tokens": 32000, "temperature": None, "canary_status": "not_run"}
    fitness = []
    for profile_name in ("neutral", "bridge2ai"):
        profile = profiles.profile_named(profile_name)
        for class_name in ("Dataset", "CoreDataset"):
            schema_path = ROOT / (api_runner.CORE_SCHEMA_PATH if class_name == "CoreDataset" else api_runner.FULL_SCHEMA_PATH)
            snapshot = evidence_score.slot_specification_snapshot(class_name, schema_path, profile=profile)
            fitness.append({"profile": profile_name, "class": class_name,
                            "generation_digest_md5": snapshot[0], "specification_sha256": snapshot[3]})
    catalogue = json.loads((HERE / "model_catalogue.json").read_bytes())
    selected_model = next(row for row in catalogue["models"] if row["model"] == "claude-opus-5")
    manifest = {"schema_version": 1, "series": f"{args.cohort}_{args.label_date}", "registered_at": datetime.now(timezone.utc).isoformat(),
        "status": "awaiting_preflight_review" if external_status == "registered" else "draft_external_sources_pending", "repository": str(ROOT),
        "code_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "code_commit_basis": "source implementation base; experiment controllers and inputs are identified by pinned_files; the actual launch commit is retained in the attempt receipt",
        "python": sys.executable, "python_version": sys.version,
        "model": selected_model, "provider_base_url": "https://api.cborg.lbl.gov",
        "claude_version": subprocess.check_output(["/Users/marcin/.local/bin/claude", "--version"], text=True).strip(),
        "budget": {"additional_usd": 200, "per_attempt_usd": 5, "authorization": "user: +$200, 2026-09-13",
                   "ledger_path": str(output / "billing.json"),
                   "prices_per_token": {"input": 0.000005, "output": 0.000025, "cache_write": 0.00000625, "cache_read": 0.0000005},
                   "unknown_charge_policy": "retain reservation and stop", "automatic_whole_attempt_retries": 0,
                   "funding": "cap-limited staged sequence; the proposed full matrix is not assumed fully funded"},
        "generation": {"template_condition": "generic_v9", "cohort_version": args.cohort,
                       "api_max_attempts": 1, "sdk_max_retries": 0,
                       "api_phase_deadline_seconds": api_runner.PHASE_WALL_CLOCK_SECONDS,
                       "agentic_attempt_deadline_seconds": 1800,
                       "agentic_cli_budget_flag_default_usd": 5,
                       "agentic_cli_budget_flag_basis": "The CLI and transport both use the registration-qualified attempt's effective ledger cap, including any approved per-job exception.",
                       "effort_policy": "API adaptive provider default; agentic runtime default, observed separately. No claim of matched realized reasoning effort.",
                       "external_canary": {"project": "KIDS_FIRST", "profile": "neutral", "status": external_status,
                                           "basis": "user nomination of the Kids First Data Resource and its AJHG publication on 2026-09-13",
                                           "source_capture_authorization": "user requires links, documentation and information about participating datasets, 2026-09-13",
                                           "paper_doi": "10.1016/j.ajhg.2026.07.010",
                                           "article_representation": "indexed metadata and abstract; publisher full-text retrieval unavailable",
                                           "catalogue_studies": 36, "source_documents": 55,
                                           "source_manifest": str(kids / "manifest.yaml"),
                                           "applicability_context": str(kids / "applicability.yaml")},
                       "synthetic_fixture": "offline software checks only; excluded from the scientific canary/cohort",
                       "canary_order": ["CHORUS_api_rep1", "CHORUS_agentic_rep1", "KIDS_FIRST_api_rep1", "KIDS_FIRST_agentic_rep1"],
                       "rep1_canaries_count_in_cohort_if_unchanged": True,
                       "jobs": jobs},
        "evaluations": {"instruments": instruments, "fitness_specifications": fitness,
                        "presence_rubrics": [10, 20], "semantic_rubrics": [10, 20],
                        "proposed_production_semantic_primary_ratings": 120,
                        "proposed_production_semantic_extra_repeat_ratings": 80,
                        "expansion_gate": "current full/core inputs, applicability, job-level outputs and budget registered after generation acceptance; no implicit cohort launch",
                        "historical_adjudication": "separate from new ratings and original historical verdicts"},
        "preservation_inventory": str(HERE / "historical_inventory.json"),
        "preservation_inventory_sha256": sha(HERE / "historical_inventory.json"),
        "pinned_files": pins}
    if args.per_job_attempt_caps:
        from budgeted_cborg import Ledger, registered_attempt_caps
        manifest["budget"]["per_job_attempt_usd"] = per_job_attempt_caps
        # Validate the roster and amounts without opening or seeding a ledger.
        # The actual attempt prefixes use the final registration hash at launch.
        Ledger(output / "billing.json", manifest_sha256="preparation-validation-only",
               total_cap=manifest["budget"]["additional_usd"],
               attempt_cap=manifest["budget"]["per_attempt_usd"],
               attempt_caps_usd=registered_attempt_caps(manifest, "preparation-validation-only"))
    if args.prior_billing:
        manifest["budget"]["continuation"] = {
            "checkpoint": str(args.prior_billing.resolve()), "sha256": sha(args.prior_billing),
            "cost_usd": args.prior_cost_usd,
            "basis": "Settled charges from the rejected prior condition; same additional allocation, new attempt identities."}
    if args.previous_attempt_audit:
        audit = json.loads(args.previous_attempt_audit.read_bytes())
        manifest["prior_attempt_artifacts"] = [
            {"path": value["original_path"], "sha256": value["sha256"]}
            for value in audit["copies"].values()]
    if not args.render_only:
        save(output / "registration.json", manifest)
    else:
        save(output / "rendered_jobs.json", {"generation": manifest["generation"], "budget": manifest["budget"]})
    print(json.dumps({"generation_jobs": len(jobs), "registered_canaries": sum(j["canary"] for j in jobs),
                      "required_canaries": 4, "external_status": external_status,
                      "input_pins": len(pins), "additional_budget_usd": 200}))


if __name__ == "__main__":
    main()
