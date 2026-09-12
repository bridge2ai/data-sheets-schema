"""Render the completed CBORG condition after its separate Q19 inspection.

Original model outputs are read only. The frozen reporter computes repeated
ratings and generation-replicate summaries; this wrapper attaches the dated
semantic qualification before publishing derived manuscript tables.
"""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
import reference_rescore_cborg_batch as batch


def main():
    if batch.PLAN != Path(__file__).resolve().parents[1]:
        raise ValueError("This dated helper requires its own registered condition; use the current condition helper or check out the recorded revision.")
    r, manifest, registration = batch.load_registered()
    plan = r.PLAN
    audit = json.loads((plan / "completion_audit.json").read_bytes())
    writes = json.loads((plan / "final_written_output_audit.json").read_bytes())
    if (audit["status"] != "verified" or audit["accepted"] != audit["planned"] or audit["planned"] != 56
            or writes["accepted"] != 56 or audit["manifest_sha256"] != r.digest(plan / "manifest.json")
            or writes["manifest_sha256"] != audit["manifest_sha256"] or audit["unresolved_attempts"]
            or not audit["session_accounting_complete"]
            or audit["batch_registration_sha256"] != r.digest(batch.REGISTRATION)):
        raise ValueError("complete original measurements and matching session evidence are required before reporting")
    import reference_rescore_cborg_deadline as deadline
    current = deadline.accounted_audit(r, registration)
    for field in ("accepted", "actual_model_calls", "cost_accounting_complete", "cli_reported_total_cost_usd",
                  "known_terminal_cli_cost_usd", "unpriced_excluded_sessions", "cost_qualification"):
        if current.get(field) != audit.get(field):
            raise ValueError("session/cost evidence changed after the audit")
    inventory = json.loads((plan / "measurement_file_hashes.json").read_bytes())["files"]
    for rel, sha in inventory.items():
        if r.digest(ROOT / rel) != sha:
            raise ValueError(f"measurement changed after audit: {rel}")
    review = json.loads((plan / "semantic_review.json").read_bytes())
    if (review["manifest_sha256"] != audit["manifest_sha256"]
            or review["definition_sha256"] != manifest["instruments"]["rubric20-semantic"]["definition_sha256"]):
        raise ValueError("semantic review identifies another condition or instrument")
    jobs = {j["id"]: j for j in manifest["jobs"] if j["rubric"] == "rubric20-semantic"}
    cases = review["cases"]
    if len(cases) != len(jobs) or len(cases) != 24 or {c["job_id"] for c in cases} != set(jobs):
        raise ValueError("inspect all 24 new Q19 rationales before the final report")
    for case in cases:
        job = jobs[case["job_id"]]
        if (case["output"] != job["output"] or case["input"] != job["input"]
                or case["evaluation_sha256"] != r.digest(ROOT / job["output"])
                or case["input_sha256"] != manifest["pinned_files"][job["input"]]
                or case["status"] not in {"requires_adjudication", "not_flagged_by_this_inspection"}
                or not case["assessment"].strip()):
            raise ValueError("semantic review lacks matching original evidence or disposition")
        doc = json.loads((ROOT / job["output"]).read_bytes())
        question, = [q for category in doc["categories"] for q in category["questions"] if q["id"] == 19]
        if question != case["q19"]:
            raise ValueError("semantic inspection does not quote the original Q19 object")
    flagged = [case for case in cases if case["status"] == "requires_adjudication"]
    if len(flagged) != review["ratings_requiring_adjudication"]:
        raise ValueError("semantic qualification count disagrees with its case dispositions")
    qualification = {
        "source": "semantic_review.json", "scope": review["scope"],
        "interpretation": review["qualification"], "issue": review.get("issue"),
        "affected_job_ids": [c["job_id"] for c in flagged],
        "affected_evaluations": [c["output"] for c in flagged],
    }
    execution = audit["execution_permission_boundary"]
    if r.digest(ROOT / execution["registration"]) != execution["registration_sha256"]:
        raise ValueError("execution-boundary registration changed after the audit")
    deadline_boundary = audit["execution_deadline_boundary"]
    if r.digest(ROOT / deadline_boundary["registration"]) != deadline_boundary["registration_sha256"]:
        raise ValueError("deadline-boundary registration changed after the audit")
    banner = ("**Semantic inspection — Q19:** " + review["qualification"]
              + " See the [24-rating inspection](semantic_review.md).\n\n"
              + "**Execution boundary:** " + execution["qualification"]
              + " Repeat panels spanning it: " + ", ".join(execution["repeat_panels_spanning_boundary"])
              + ". See [the dated registration](validator_status_registration.json).\n\n"
              + "**Execution deadline:** " + deadline_boundary["qualification"]
              + " See [the deadline registration](deadline_registration_1351.json).\n\n"
              + "**Incomplete cost accounting:** " + audit["cost_qualification"] + "\n\n")
    reports = [plan / name for name in ("results.json", "results.md", "completion_summary.md", "semantic_review.md")]
    before = {path: path.read_bytes() if path.exists() else None for path in reports}
    try:
        results = r.report_results(manifest)
        if (results["completed"] != 56 or results["pending"]
                or any(row["ratings"] != 3 for row in results["repeatability"])):
            raise ValueError("reported cohort or repeat panel is incomplete")
        results["provider_condition"] = "LBL CBORG / 2026-09-12 with execution-metadata provenance; separate from preliminary and prior reference runs"
        results["semantic_qualification"] = qualification
        results["execution_permission_boundary"] = execution
        results["execution_deadline_boundary"] = deadline_boundary
        results["cost_accounting"] = {key: audit[key] for key in (
            "cost_accounting_complete", "cli_reported_total_cost_usd", "known_terminal_cli_cost_usd",
            "unpriced_excluded_sessions", "cost_qualification")}
        r.write_json(plan / "results.json", results)
        text = (plan / "results.md").read_text().replace(str(ROOT) + "/", "")
        title, rest = text.split("\n", 1)
        for case in flagged:
            text_path = case["output"]
            rest = rest.replace(f"| {text_path} |", f"| {text_path} [Q19 inspection](semantic_review.md) |")
        (plan / "results.md").write_text(title + "\n\n" + banner + rest.lstrip("\n"))
        lines = ["# CBORG reference rescore completion — 2026-09-12", "", banner.rstrip(), "",
                 "Completed **56 accepted ratings** of the 24 existing v7/v8 D4Ds: 48 primary ratings across both semantic rubrics and eight additional rubric10 ratings. All original scores remain unchanged; this provider condition is separate from the earlier reference run.", "",
                 f"The [completion audit](completion_audit.json) accounts for {audit['actual_model_calls']} evaluator CLI sessions, including {audit['excluded_original_attempts']} retained excluded attempts in this completed condition. The separate preliminary condition used {audit['preliminary_condition']['sessions']} sessions and ${audit['preliminary_condition']['cli_reported_cost_usd']:.8f}, retaining one accepted canary and three excluded attempts; none is pooled into these 56 ratings. All {audit['prior_evaluations_unchanged']} prior evaluations retain their hashes, all 56 accepted outputs match their original successful Writes, and peak completed-session concurrency was {audit['peak_completed_session_concurrency']}. The known terminal CLI subtotal is **${audit['known_terminal_cli_cost_usd']:.8f}**; it excludes the two unpriced interrupted sessions and is not a complete expenditure total. A session may contain multiple model/tool turns; this is not a count of HTTP requests or a reconciled invoice. Review-tool usage is outside this figure.", "",
                 f"The audit separately retains {len(audit['verified_local_prelaunch_failures'])} verified local pre-launch failure(s). These stopped at the registered CLI version guard before evaluator exec, produced no model-session cost record and are not counted as evaluator sessions.", "",
                 "The runtime trace identifies `claude-opus-5`, requested through CBORG as `claude-opus-5[1m]` at high effort with temperature unspecified. Definitions, inputs, complete prompts and schemas are pinned by the [manifest](manifest.json). Every accepted rating passed identity, check-echo, arithmetic, schema and original-output checks. All rubric10 headings match the source rubric.", "",
                 f"Rubric10 definition: `{manifest['instruments']['rubric10-semantic']['definition_sha256']}`. Rubric20 definition: `{manifest['instruments']['rubric20-semantic']['definition_sha256']}`.", "",
                 "## Repeated ratings", "",
                 "Three independent rubric10 ratings cover one v7 record per project. These descriptive ranges and sample standard deviations do not estimate population uncertainty. Rubric20 repeatability is unmeasured. Generation-replicate spread is reported separately in [results.md](results.md); small score differences do not establish a preferred generation run.", "",
                 "| Project | Fixed percentages | Adjusted percentages | Fixed SD | Adjusted SD | Adjusted range | Stable applicability |",
                 "|---|---|---|---|---|---|---|"]
        for row in results["repeatability"]:
            lines.append(f"| {row['project']} | {row['fixed_percentages']} | {row['adjusted_percentages']} | {row['fixed_sample_sd']:.4f} | {row['adjusted_sample_sd']:.4f} | {row['adjusted_range']:.4f} | {row['applicability_stable']} |")
        lines += ["", "## Primary recorded totals", "", "Q19 inspection flags qualify the affected rubric20 totals; no scores were edited or adjudicated by this report.", "",
                  "| Record | Rubric10 | Rubric20 |", "|---|---|---|"]
        primary = {}
        flagged_ids = {case["job_id"] for case in flagged}
        for job in manifest["jobs"]:
            if job["purpose"] == "primary":
                doc = json.loads((ROOT / job["output"]).read_bytes())
                score = doc["overall_score"]
                value = f"{score['total_points']}/{score['max_points']}"
                if job["id"] in flagged_ids:
                    value += " [Q19 inspection](semantic_review.md)"
                primary.setdefault((job["project"], job["cohort"], job["generation_rep"]), {})[job["rubric"]] = value
        for (project, cohort, rep), values in sorted(primary.items()):
            lines.append(f"| {project} {cohort} rep{rep} | {values['rubric10-semantic']} | {values['rubric20-semantic']} |")
        lines += ["", "## Separate v9 generation canary", "",
                  f"Exactly one CHORUS v9 full/core pair was generated from the existing source bundle and passed the registered gates. It made {audit['v9_model_requests']} native API requests, with a catalogue-rate usage estimate of ${float(audit['v9_catalogue_price_estimate_usd']):.8f}. The [generation review](../cborg_canaries_2026-09-12/v9_canary_review.md) retains the source checks and limits. This is one canary, not a completed v9 manuscript cohort; no downloads or additional v9 generation occurred.", ""]
        (plan / "completion_summary.md").write_text("\n".join(lines))
        lines = ["# Q19 inspection of the CBORG reference measurements", "", review["scope"], "", banner.rstrip(), "",
                 "The frozen rule permits complete textual provenance as well as W3C PROV-O graphs. A representation-related objection is flagged for adjudication; this inspection does not assign replacement scores or certify other judgments or external source truth.", ""]
        for case in cases:
            q = case["q19"]
            lines += [f"## {case['job_id']}", "", f"Recorded Q19: {q['score']}/{q['max_score']}. Status: `{case['status']}`.", "", case["assessment"], "",
                      f"Original output: [evaluation](../../{case['output']}); SHA256 `{case['evaluation_sha256']}`.", "",
                      "Original Q19 object:", "", "```json", json.dumps(q, indent=2), "```", ""]
        (plan / "semantic_review.md").write_text("\n".join(lines))
    except BaseException:
        for path, content in before.items():
            if content is None:
                path.unlink(missing_ok=True)
            else:
                path.write_bytes(content)
        raise
    print(f"Rendered 56 original measurements and {len(cases)} Q19 inspections; {len(flagged)} require adjudication.")


if __name__ == "__main__":
    main()
