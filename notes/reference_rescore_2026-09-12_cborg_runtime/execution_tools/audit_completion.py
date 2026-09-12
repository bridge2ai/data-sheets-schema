"""Verify complete CBORG measurements without any evaluator or generation call.

Run from the repository root in the project environment. This intentionally
uses the frozen audit in partial mode, then supplies the new condition's
completion and preservation checks; the old audit's --complete option names
preservation records belonging only to the previous provider condition.
"""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
import audit_reference_rescore as audit_module
import reference_rescore_cborg_batch as batch


def main():
    if batch.PLAN != Path(__file__).resolve().parents[1]:
        raise ValueError("This dated helper requires its own registered condition; use the current condition helper or check out the recorded revision.")
    r, manifest, registration = batch.load_registered()
    audit_module.r = r
    original_inventory = audit_module.inventory_attempts
    audit_module.inventory_attempts = lambda root, plan, jobs: batch.inventory_with_prelaunch(
        r, registration, original_inventory, root, plan, jobs)
    try:
        audit = audit_module.audit_results(complete=False)
    finally:
        audit_module.inventory_attempts = original_inventory
    prelaunch = [batch.verify_prelaunch_failure(r, ROOT / rel, registration)
                 for rel in registration.get("prelaunch_failures", {})]
    if (audit["status"] != "verified" or audit["accepted"] != audit["planned"] or audit["planned"] != 56
            or audit["unresolved_attempts"] or not audit["session_accounting_complete"]
            or not audit["cost_accounting_complete"]):
        raise ValueError("completion requires all 56 original ratings and complete attempt/usage accounting")
    batch.require_pilot(r, manifest, registration)
    written = [batch.verified_output(r, manifest, job) for job in manifest["jobs"]]
    preserved = {}
    for mapping in (registration["preserved_files"], registration["existing_outputs"]):
        for rel, sha in mapping.items():
            if r.digest(ROOT / rel) != sha:
                raise ValueError(f"pre-batch evidence changed: {rel}")
            preserved[rel] = sha
    for start in (r.PLAN / "manifest.json", r.PLAN / "batch_registration.json"):
        current = json.loads(start.read_bytes())
        seen = set()
        while "supersedes_registration" in current:
            prior = current["supersedes_registration"]
            rel, sha = prior["path"], prior["sha256"]
            if rel in seen or r.digest(ROOT / rel) != sha:
                raise ValueError(f"invalid registration archive: {rel}")
            seen.add(rel)
            preserved[rel] = sha
            current = json.loads((ROOT / rel).read_bytes())
    archives = ROOT / "notes/reference_rescore_2026-09-12_cborg/registrations"
    for stem in ("interruption", "stop-race", "reviewed-retry", "missing-history"):
        prior = json.loads((archives / f"batch-registration-before-{stem}-fix.json").read_bytes())
        path = archives / f"reference_rescore_cborg_batch-before-{stem}-fix.py"
        if r.digest(path) != prior["scheduler_sha256"]:
            raise ValueError(f"archived scheduler changed: {path}")
        preserved[str(path.relative_to(ROOT))] = r.digest(path)
    original = json.loads((archives / "manifest-before-write-tool-fix.json").read_bytes())
    path = archives / "reference_rescore_cborg-before-write-tool-fix.py"
    if r.digest(path) != original["pinned_files"]["scripts/reference_rescore_cborg.py"]:
        raise ValueError("archived original transport changed")
    preserved[str(path.relative_to(ROOT))] = r.digest(path)
    generation = ROOT / "notes/cborg_canaries_2026-09-12"
    v9 = json.loads((generation / "v9_canary_review.json").read_bytes())
    pins = json.loads((generation / "v9_input_pins.json").read_bytes())["pinned_files"]
    for rel, sha in {**pins, **v9["artifact_sha256"]}.items():
        if r.digest(ROOT / rel) != sha:
            raise ValueError(f"v9 canary evidence changed: {rel}")
        preserved[rel] = sha
    for result_path in sorted((r.PLAN / "batch_runs").glob("*/result.json")):
        result = json.loads(result_path.read_bytes())
        if any(row["exit_code"] != 0 for row in result["completed"]):
            # A stopped or failed launch remains in the audit even after a
            # separately registered repair. Do not erase the controller record.
            audit.setdefault("controller_runs_with_worker_failures", []).append(str(result_path.relative_to(ROOT)))
    preliminary = json.loads((ROOT / "notes/reference_rescore_2026-09-12_cborg/preliminary_audit.json").read_bytes())
    audit["verified_local_prelaunch_failures"] = prelaunch
    audit["total_attempts_including_local_preflights"] = audit["actual_model_calls"] + len(prelaunch)
    audit.update({"preliminary_condition": {"path": "notes/reference_rescore_2026-09-12_cborg/preliminary_audit.json", "sessions": preliminary["actual_model_calls"], "accepted_canaries_retained_separately": preliminary["accepted"], "excluded_attempts": preliminary["excluded_original_attempts"], "cli_reported_cost_usd": preliminary["cli_reported_total_cost_usd"]}, "provider": "LBL CBORG", "transport_manifest_sha256": r.digest(r.PLAN / "manifest.json"),
                  "batch_registration_sha256": r.digest(batch.REGISTRATION),
                  "original_successful_write_bindings": len(written),
                  "pre_batch_and_generation_preservation_hashes_verified": len(preserved),
                  "v9_generated_records": v9["generated_records"],
                  "v9_model_requests": v9["model_requests"],
                  "v9_catalogue_price_estimate_usd": v9["catalogue_price_estimate_usd"],
                  "cost_basis": "Evaluation CLI list-price estimates include excluded sessions. Generation uses observed CBORG catalogue rates. Neither is a reconciled invoice; review-tool usage is outside these figures."})
    r.write_json(r.PLAN / "completion_audit.json", audit)
    r.write_json(r.PLAN / "final_written_output_audit.json", {
        "verified_at": r.now(), "manifest_sha256": audit["manifest_sha256"], "accepted": len(written),
        "verification": "Every published rating and retained candidate matches the last successful original evaluator Write at its isolated output path.",
        "model_calls_during_verification": 0, "ratings": written})
    immutable = {**manifest["pinned_files"], **manifest["prior_evaluations"], **preserved}
    for directory in (r.PLAN / "attempts", r.PLAN / "batch_runs"):
        for path in directory.rglob("*"):
            if path.is_file():
                immutable[str(path.relative_to(ROOT))] = r.digest(path)
    for job in manifest["jobs"]:
        immutable[job["output"]] = r.digest(ROOT / job["output"])
    r.write_json(r.PLAN / "measurement_file_hashes.json", {
        "verified_at": r.now(), "search_scope": "Filesystem walk includes ignored attempt and controller files.",
        "files": immutable})
    print(json.dumps({k: v for k, v in audit.items() if k not in ("ratings", "original_calls")}, indent=2))


if __name__ == "__main__":
    main()
