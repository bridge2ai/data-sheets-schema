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
import reference_rescore_cborg_deadline as deadline


def main():
    if batch.PLAN != Path(__file__).resolve().parents[1]:
        raise ValueError("This dated helper requires its own registered condition; use the current condition helper or check out the recorded revision.")
    r, manifest, registration = batch.load_registered()
    audit = deadline.accounted_audit(r, registration)
    prelaunch = [batch.verify_prelaunch_failure(r, ROOT / rel, registration)
                 for rel in registration.get("prelaunch_failures", {})]
    if (audit["status"] != "verified" or audit["accepted"] != audit["planned"] or audit["planned"] != 56
            or audit["unresolved_attempts"] or not audit["session_accounting_complete"]):
        raise ValueError("completion requires all 56 original ratings and accounted session outcomes")
    batch.require_pilot(r, manifest, registration)
    written = [batch.verified_output(r, manifest, job) for job in manifest["jobs"]]
    boundary_path = r.PLAN / "validator_status_registration.json"
    boundary = json.loads(boundary_path.read_bytes())
    earlier = boundary["accepted_outputs_preserved"]
    before_jobs, after_jobs, status_jobs = [], [], []
    import reference_rescore_cborg_validator_status as status
    from datetime import datetime
    if len(manifest["jobs"]) != len(written):
        raise ValueError("original Write inventory differs from the manifest")
    for job, binding in zip(manifest["jobs"], written):
        receipt = r.successful_receipt(manifest, job)
        source = ROOT / binding["original_attempt"]
        events = audit_module.read_trace(source)
        proofs = status.proven_status_calls(r, events, job["rubric"])
        if job["output"] in earlier:
            if (r.digest(ROOT / job["output"]) != earlier[job["output"]]
                    or datetime.fromisoformat(receipt["completed_at"]) >= datetime.fromisoformat(boundary["recorded_at"])):
                raise ValueError("pre-extension measurement does not match the registered boundary")
            before_jobs.append(job["id"])
        else:
            if (datetime.fromisoformat(receipt["started_at"]) < datetime.fromisoformat(boundary["recorded_at"])
                    or receipt.get("validator_exit_status_evidence") != proofs):
                raise ValueError("post-extension receipt lacks its original validation evidence")
            after_jobs.append(job["id"])
        if proofs:
            status_jobs.append(job["id"])
    if len(before_jobs) != len(earlier) or len(before_jobs) != 5 or len(after_jobs) != 51:
        raise ValueError("completed execution-boundary inventory differs from the registration")
    panel_stages = {}
    for job in manifest["jobs"]:
        if job["rubric"] == "rubric10-semantic" and job["cohort"] == "v7" and job["generation_rep"] == 1:
            panel_stages.setdefault(job["project"], set()).add("before" if job["id"] in before_jobs else "after")
    audit["execution_permission_boundary"] = {
        "registration": str(boundary_path.relative_to(ROOT)), "registration_sha256": r.digest(boundary_path),
        "recorded_at": boundary["recorded_at"], "extension": boundary["execution_extension"],
        "accepted_before_job_ids": before_jobs, "accepted_after_job_ids": after_jobs,
        "accepted_status_echo_job_ids": status_jobs,
        "repeat_panels_spanning_boundary": sorted(project for project, stages in panel_stages.items() if len(stages) > 1),
        "qualification": "Five accepted ratings precede the validator-status permission extension and 51 follow it. Scoring prompts, definitions and inputs are unchanged, but execution permissions differ. Cohort comparisons and repeat panels spanning this boundary do not isolate permission effects; small differences cannot be attributed solely to generation version or evaluator variability.",
    }
    deadline_path = r.PLAN / "deadline_registration_1351.json"
    deadline_boundary = json.loads(deadline_path.read_bytes())
    earlier_deadline = deadline_boundary["accepted_outputs_preserved"]
    deadline_before, deadline_after = [], []
    for job, binding in zip(manifest["jobs"], written):
        receipt = r.successful_receipt(manifest, job)
        if job["output"] in earlier_deadline:
            if (r.digest(ROOT / job["output"]) != earlier_deadline[job["output"]]
                    or datetime.fromisoformat(receipt["completed_at"]) >= datetime.fromisoformat(deadline_boundary["recorded_at"])):
                raise ValueError("pre-deadline measurement differs from the registered boundary")
            deadline_before.append(job["id"])
        else:
            source = ROOT / binding["original_attempt"]
            proof = json.loads((source / "execution_deadline.json").read_bytes())
            if (datetime.fromisoformat(receipt["started_at"]) < datetime.fromisoformat(deadline_boundary["recorded_at"])
                    or proof["extension"] != registration["deadline_extension"]
                    or proof["timeout_seconds"] != deadline.SECONDS or proof["timed_out"] is not False
                    or proof["returncode"] != 0):
                raise ValueError("post-deadline measurement lacks matching execution evidence")
            deadline_after.append(job["id"])
    if len(deadline_before) != len(earlier_deadline) or len(deadline_before) != 17 or len(deadline_after) != 39:
        raise ValueError("completed deadline-boundary inventory differs from registration")
    audit["execution_deadline_boundary"] = {
        "registration": str(deadline_path.relative_to(ROOT)), "registration_sha256": r.digest(deadline_path),
        "recorded_at": deadline_boundary["recorded_at"],
        "accepted_before_job_ids": deadline_before, "accepted_after_job_ids": deadline_after,
        "qualification": "Seventeen accepted ratings precede the execution deadline increase from 900 to 1800 seconds; 39 follow it. Scoring prompts, definitions, inputs and the $5 CLI cap are unchanged. This execution boundary can affect completion/selection, so cohort and repeat comparisons do not isolate generation-version or evaluator effects.",
    }
    preserved = {}
    for mapping in (registration["preserved_files"], registration["existing_outputs"]):
        for rel, sha in mapping.items():
            if r.digest(r.ROOT / rel) != sha:
                raise ValueError(f"pre-batch evidence changed: {rel}")
            preserved[rel] = sha
    for start in (r.PLAN / "manifest.json", r.PLAN / "batch_registration.json"):
        current = json.loads(start.read_bytes())
        seen = set()
        while "supersedes_registration" in current:
            prior = current["supersedes_registration"]
            rel, sha = prior["path"], prior["sha256"]
            if rel in seen or r.digest(r.ROOT / rel) != sha:
                raise ValueError(f"invalid registration archive: {rel}")
            seen.add(rel)
            preserved[rel] = sha
            current = json.loads((ROOT / rel).read_bytes())
    archives = ROOT / "notes/reference_rescore_2026-09-12_cborg/registrations"
    snapshots = 0
    for directory in (archives, r.PLAN / "registrations"):
        for registration_path in sorted(directory.glob("batch-registration-before-*-fix.json")):
            stem = registration_path.stem.removeprefix("batch-registration-before-").removesuffix("-fix")
            prior = json.loads(registration_path.read_bytes())
            path = directory / f"reference_rescore_cborg_batch-before-{stem}-fix.py"
            if r.digest(path) != prior["scheduler_sha256"]:
                raise ValueError(f"archived scheduler changed: {path}")
            preserved[str(path.relative_to(ROOT))] = r.digest(path)
            snapshots += 1
    original = json.loads((archives / "manifest-before-write-tool-fix.json").read_bytes())
    path = archives / "reference_rescore_cborg-before-write-tool-fix.py"
    if r.digest(path) != original["pinned_files"]["scripts/reference_rescore_cborg.py"]:
        raise ValueError("archived original transport changed")
    preserved[str(path.relative_to(ROOT))] = r.digest(path)
    generation = ROOT / "notes/cborg_canaries_2026-09-12"
    v9 = json.loads((generation / "v9_canary_review.json").read_bytes())
    pins = json.loads((generation / "v9_input_pins.json").read_bytes())["pinned_files"]
    for rel, sha in {**pins, **v9["artifact_sha256"]}.items():
        if r.digest(r.ROOT / rel) != sha:
            raise ValueError(f"v9 canary evidence changed: {rel}")
        preserved[rel] = sha
    for result_path in sorted((r.PLAN / "batch_runs").glob("*/result.json")):
        result = json.loads(result_path.read_bytes())
        if any(row["exit_code"] != 0 for row in result["completed"]):
            # A stopped or failed launch remains in the audit even after a
            # separately registered repair. Do not erase the controller record.
            audit.setdefault("controller_runs_with_worker_failures", []).append(str(result_path.relative_to(ROOT)))
    preliminary = json.loads((ROOT / "notes/reference_rescore_2026-09-12_cborg/preliminary_audit.json").read_bytes())
    archive_record_path = r.PLAN / "report_dispatch_preservation_1356.json"
    archive_record = json.loads(archive_record_path.read_bytes())
    if (archive_record["manifest_sha256"] != r.digest(r.PLAN / "manifest.json")
            or archive_record["registered_path"] != batch.c.MEASURED_PATH
            or archive_record["measured_code_archive"] != batch.c.MEASURED_ARCHIVE
            or archive_record["measured_code_sha256"] != batch.c.MEASURED_SHA256
            or archive_record["measured_scheduler_archive"] != batch.c.MEASURED_SCHEDULER_ARCHIVE
            or archive_record["measured_scheduler_sha256"] != registration["scheduler_sha256"]):
        raise ValueError("post-measurement code archive identifies different measured bytes")
    for rel, sha in archive_record["preserved_before_repair"].items():
        if r.digest(r.ROOT / rel) != sha:
            raise ValueError(f"pre-repair evidence changed: {rel}")
        preserved[rel] = sha
    preserved[str(archive_record_path.relative_to(ROOT))] = r.digest(archive_record_path)
    audit["measured_code_archive"] = {
        "registered_path": batch.c.MEASURED_PATH, "path": batch.c.MEASURED_ARCHIVE,
        "sha256": batch.c.MEASURED_SHA256,
        "scheduler_path": batch.c.MEASURED_SCHEDULER_ARCHIVE,
        "scheduler_sha256": registration["scheduler_sha256"],
        "preservation_record": str(archive_record_path.relative_to(ROOT)),
        "preservation_record_sha256": r.digest(archive_record_path),
        "qualification": "The public report command was repaired after all measurements completed. Verification uses the exact archived adapter and scheduler bytes recorded by the unchanged manifest and registration, not the updated reporting commands.",
    }
    audit["verified_local_prelaunch_failures"] = prelaunch
    audit["total_attempts_including_local_preflights"] = audit["actual_model_calls"] + len(prelaunch)
    audit["archived_scheduler_snapshots_verified"] = snapshots
    audit.update({"preliminary_condition": {"path": "notes/reference_rescore_2026-09-12_cborg/preliminary_audit.json", "sessions": preliminary["actual_model_calls"], "accepted_canaries_retained_separately": preliminary["accepted"], "excluded_attempts": preliminary["excluded_original_attempts"], "cli_reported_cost_usd": preliminary["cli_reported_total_cost_usd"]}, "provider": "LBL CBORG", "transport_manifest_sha256": r.digest(r.PLAN / "manifest.json"),
                  "batch_registration_sha256": r.digest(batch.REGISTRATION),
                  "original_successful_write_bindings": len(written),
                  "pre_batch_and_generation_preservation_hashes_verified": len(preserved),
                  "v9_generated_records": v9["generated_records"],
                  "v9_model_requests": v9["model_requests"],
                  "v9_catalogue_price_estimate_usd": v9["catalogue_price_estimate_usd"],
                  "cost_basis": "The known evaluation CLI subtotal includes priced excluded sessions and omits explicitly unpriced interruptions; total expenditure is unknown. Generation uses observed CBORG catalogue rates. Neither is a reconciled invoice; review-tool usage is outside these figures."})
    written_audit = {
        "verified_at": r.now(), "manifest_sha256": audit["manifest_sha256"], "accepted": len(written),
        "verification": "Every published rating and retained candidate matches the last successful original evaluator Write at its isolated output path.",
        "model_calls_during_verification": 0, "ratings": written}
    measured_pins = r.measured_pinned_files(manifest)
    immutable = {**measured_pins, **manifest["prior_evaluations"], **preserved}
    for directory in (r.PLAN / "attempts", r.PLAN / "batch_runs"):
        for path in directory.rglob("*"):
            if path.is_file():
                immutable[str(path.relative_to(ROOT))] = r.digest(path)
    for job in manifest["jobs"]:
        immutable[job["output"]] = r.digest(ROOT / job["output"])
    measurement_inventory = {
        "verified_at": r.now(), "search_scope": "Filesystem walk includes ignored attempt and controller files.",
        "measured_code_archives": {
            "scripts/reference_rescore_cborg_batch.py": {
                "path": batch.c.MEASURED_SCHEDULER_ARCHIVE,
                "sha256": registration["scheduler_sha256"],
                "basis": "Exact scheduler bytes used for the completed measurements, preserved before #1356.",
            },
            "scripts/reference_rescore_cborg.py": {
                "path": batch.c.MEASURED_ARCHIVE,
                "sha256": batch.c.MEASURED_SHA256,
                "basis": "Exact adapter bytes used for the completed measurements; the public command was subsequently repaired under #1356. The original manifest and receipts are unchanged.",
            }
        },
        "files": immutable}
    # This condition is complete. Re-audit the retained evidence without
    # rewriting its originals or invalidating the pinned preservation index.
    for name, current, timestamp in (
        ("completion_audit.json", audit, "audited_at"),
        ("final_written_output_audit.json", written_audit, "verified_at"),
        ("measurement_file_hashes.json", measurement_inventory, "verified_at"),
    ):
        saved = json.loads((r.PLAN / name).read_bytes())
        if name == "measurement_file_hashes.json":
            # The original index's descriptive search_scope wording is not
            # recomputed evidence. Compare its complete path/hash inventory.
            equal = saved["files"] == current["files"] and saved["measured_code_archives"] == current["measured_code_archives"]
        else:
            equal = ({k: v for k, v in saved.items() if k != timestamp}
                     == {k: v for k, v in current.items() if k != timestamp})
        if not equal:
            raise ValueError(f"completed audit differs from retained evidence: {name}")
    print(json.dumps({k: v for k, v in audit.items() if k not in ("ratings", "original_calls")}, indent=2))


if __name__ == "__main__":
    main()
