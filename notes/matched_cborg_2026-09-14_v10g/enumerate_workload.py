"""Enumerate the existing proposal; this public inventory cannot launch jobs."""
from collections import Counter
from decimal import Decimal
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REGISTRATION = HERE / "registration.public.json"
PRIOR_AUTHORIZATION = HERE.parent / "matched_cborg_2026-09-14_v10f_cap20/budget_authorization_2026-09-14.json"


def build(public):
    if public.get("kind") != "public_review_view_not_executable":
        raise ValueError("expected a non-executable public registration view")
    registration = public["view"]
    jobs = registration["generation"]["jobs"]
    if len({job["id"] for job in jobs}) != len(jobs):
        raise ValueError("duplicate generation job identity")
    default = Decimal(str(registration["budget"]["per_attempt_usd"]))
    proposed = registration["budget"].get("per_job_attempt_usd", {})
    approved = json.loads(PRIOR_AUTHORIZATION.read_bytes())["approved_whole_attempt_caps_usd"]
    records, ratings, generations = [], [], []
    for job in jobs:
        if job["purpose"] not in {"manuscript_cohort", "external_general_user_canary"}:
            raise ValueError("an unrecognized cohort purpose needs explicit treatment")
        scope = "study" if job["purpose"] == "manuscript_cohort" else "external"
        cap = Decimal(str(proposed.get(job["id"], default)))
        if job["id"] in proposed:
            if cap > Decimal(str(approved[job["id"]])):
                raise ValueError("candidate cap exceeds the previously approved financial ceiling")
        generations.append({
            "id": job["id"], "scope": scope, "project": job["project"],
            "runtime_arm": job["execution_arm"], "replicate": job["replicate"],
            "canary": job["canary"],
            "proposed_attempt_cap_usd": str(proposed.get(job["id"], default)),
            "cap_exception_approval": "within_previously_approved_financial_ceiling" if job["id"] in proposed else "not_required",
            "attempt_authorization": ("additional_attempt_pending_user_approval" if job["id"] == "CHORUS_api_rep1"
                                      else "requires_preceding_canary_acceptance" if job["canary"]
                                      else "requires_workload_and_expansion_decision"),
            "outputs": {variant: job["outputs"][variant] for variant in ("full", "core")},
        })
        for variant in ("full", "core"):
            record_id = f"{job['id']}__{variant}"
            records.append({
                "id": record_id, "generation_job": job["id"], "scope": scope,
                "project": job["project"], "runtime_arm": job["execution_arm"],
                "generation_replicate": job["replicate"], "variant": variant,
                "planned_output": job["outputs"][variant], "accepted_original_sha256": None,
                "source_bundle_sha256": registration["pinned_files"][job["bundle"]],
                "profile": job["profile"],
                "status": "awaiting_generation_and_original_artifact_acceptance",
            })
            for rubric in (10, 20):
                # Replicate 1's primary is already part of the cohort total.
                # Two extra ratings create three observations per repeat cell.
                repeats = 3 if job["replicate"] == 1 else 1
                for rating in range(1, repeats + 1):
                    ratings.append({
                        "id": f"{record_id}__semantic_rubric{rubric}__rating{rating}",
                        "record_id": record_id, "scope": scope,
                        "style": "semantic_agent", "rubric": rubric,
                        "rating": rating, "role": "primary" if rating == 1 else "extra_repeat",
                        "evaluator_canary": job["canary"],
                        "proposed_attempt_cap_usd": str(default),
                    })
                if job["canary"]:
                    for style in ("direct_api_quality", "field_agent"):
                        ratings.append({
                            "id": f"{record_id}__{style}_rubric{rubric}__rating1",
                            "record_id": record_id, "scope": scope, "style": style,
                            "rubric": rubric, "rating": 1, "role": "primary",
                            "evaluator_canary": True,
                            "proposed_attempt_cap_usd": str(default),
                        })
    if len({row["id"] for row in ratings}) != len(ratings):
        raise ValueError("duplicate rating identity")
    record_ids = {row["id"] for row in records}
    if any(row["record_id"] not in record_ids for row in ratings):
        raise ValueError("rating refers to an unknown record")
    totals = Counter((row["scope"], row["style"], row["role"]) for row in ratings)
    generation_caps = sum((Decimal(row["proposed_attempt_cap_usd"]) for row in generations), Decimal(0))
    rating_caps = sum((Decimal(row["proposed_attempt_cap_usd"]) for row in ratings), Decimal(0))
    return {
        "kind": "proposed_workload_inventory_not_a_launch_registration",
        "source_registration_sha256": public["original_sha256"],
        "prior_financial_authorization_sha256": hashlib.sha256(PRIOR_AUTHORIZATION.read_bytes()).hexdigest(),
        "provider": registration["provider_base_url"], "model": registration["model"]["model"],
        "status": "generation_canaries_and_evaluator_registrations_pending",
        "generation_jobs": generations, "records": records, "rating_jobs": ratings,
        "totals": {
            "generation_jobs": len(generations), "full_records": len(jobs), "derived_cores": len(jobs),
            "generation_canaries": sum(job["canary"] for job in jobs),
            "enumerated_rubric_ratings": len(ratings),
            "evaluator_canary_ratings_included_in_total": sum(row["evaluator_canary"] for row in ratings),
            "ratings_by_scope_style_role": [
                {"scope": scope, "style": style, "role": role, "ratings": count}
                for (scope, style, role), count in sorted(totals.items())],
            "offline_presence_scores": len(records) * 2,
            "full_core_pairs_for_validation_and_source_review": len(jobs),
        },
        "cost_bounds": {
            "kind": "sum_of_proposed_attempt_caps_not_a_cost_forecast_or_reservation",
            "generation_caps_usd": str(generation_caps), "enumerated_rating_caps_usd": str(rating_caps),
            "sum_for_enumerated_future_jobs_usd": str(generation_caps + rating_caps),
            "additional_allocation_cap_usd": str(registration["budget"]["additional_usd"]),
            "prior_settled_cost_usd": registration["budget"]["continuation"]["cost_usd"],
            "entire_matrix_funded": False,
            "basis": "The shared allocation remains binding. Sum-of-caps accounting shows exposure only; measured canary usage is required for an empirical projection before expansion.",
        },
        "other_required_styles": [
            "Offline rubric10/rubric20 presence on each eligible exact file",
            "Schema, duplicate-key, full/core consistency and deterministic derivation checks",
            "Provenance, receipts, snippets, chunks and report-claim checks with their source denominators",
            "Grounding, fitness and subtype judgments with applicability and complete specification identities",
            "Independent original-record/source review and separate historical adjudication",
        ],
        "unquantified_paid_extensions": [
            "Applicable model-judged fitness, subtype, grounding or adjudication work",
            "Any direct-API quality or field-agent expansion beyond the enumerated canaries",
        ],
        "launch_requirements": [
            "Accept unchanged original generation artifacts before registering their evaluation inputs",
            "Register exact accepted input hashes, trusted applicability, instrument, request/instructions and exclusive output paths",
            "Register repeat panels before observing scores; retain all attempts and exclusions",
            "Use CBORG and the same cumulative sequence ledger, with no implicit paid retries",
            "Direct API uses streaming; agent styles prepend the pinned preamble and verify check-echo",
            "Independently review each applicable canary style; a failed canary stops expansion",
            "Fix the full workload and empirical cost projection before production expansion; omit no planned style silently",
        ],
    }


def main():
    raw = REGISTRATION.read_bytes()
    result = build(json.loads(raw))
    result["public_registration_file_sha256"] = hashlib.sha256(raw).hexdigest()
    rendered = json.dumps(result, indent=2) + "\n"
    output = HERE / "workload.json"
    if output.exists():
        if output.read_text() != rendered:
            raise ValueError("refusing to overwrite a changed workload proposal")
    else:
        output.write_text(rendered)
    print(json.dumps(result["totals"], indent=2))


if __name__ == "__main__":
    main()
