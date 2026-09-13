"""Render the completed CBORG condition after its separate Q19 inspection.

Original model outputs are read only. The frozen reporter computes repeated
ratings and generation-replicate summaries; this wrapper attaches the dated
semantic qualification before publishing derived manuscript tables.
"""
from pathlib import Path
from contextlib import contextmanager
from datetime import datetime
import json
import os
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
import reference_rescore_cborg_batch as batch


REPORT_NAMES = ("results.json", "results.md", "completion_summary.md", "semantic_review.md")


class ReportDestinations:
    """Redirect only report paths; receipt and manifest reads keep their sources."""

    def __init__(self, source, staging):
        self.source, self.staging = source, staging

    def __truediv__(self, name):
        return (self.staging if name in REPORT_NAMES else self.source) / name


class ReportRecoveryError(RuntimeError):
    """A filesystem failure prevented rollback; retained backups need recovery."""


def publish_staged_reports(plan, staging, state=None):
    """Publish completed files, retaining the old inodes until all renames pass."""
    state = {"safe_to_clean": True} if state is None else state
    if not all((staging / name).is_file() for name in REPORT_NAMES):
        raise ValueError("all four qualified reports must be staged before publication")
    backups = staging / "backups"
    backups.mkdir()
    for name in REPORT_NAMES:
        if (plan / name).exists():
            os.link(plan / name, backups / name)
    replaced = []
    state["safe_to_clean"] = False
    try:
        for name in REPORT_NAMES:
            # Include the destination before the syscall, so an interruption
            # immediately after a successful rename cannot evade rollback.
            replaced.append(name)
            os.replace(staging / name, plan / name)
    except BaseException as error:
        failed = []
        for name in reversed(replaced):
            try:
                if (backups / name).exists():
                    os.replace(backups / name, plan / name)
                else:
                    (plan / name).unlink(missing_ok=True)
            except BaseException as recovery_error:
                failed.append(f"{name} ({type(recovery_error).__name__})")
        if failed:
            raise ReportRecoveryError(
                f"report rollback failed for {failed}; original backups retained at {backups}") from error
        state["safe_to_clean"] = True
        raise
    else:
        state["safe_to_clean"] = True


@contextmanager
def staged_publication(r):
    """Keep intermediate output off published paths, including on disk-full errors."""
    plan = r.PLAN
    # Reuse the condition lock to serialize report publication. This completed
    # condition no longer permits new canary or worker launches.
    with r.canary_lock():
        staging = Path(tempfile.mkdtemp(prefix=".report-staging-", dir=plan))
        state = {"safe_to_clean": True}
        try:
            r.PLAN = ReportDestinations(plan, staging)
            yield staging
            r.PLAN = plan
            publish_staged_reports(plan, staging, state)
        except BaseException as error:
            if not state["safe_to_clean"] and not isinstance(error, ReportRecoveryError):
                raise ReportRecoveryError(
                    f"report recovery is unconfirmed; original backups retained at {staging / 'backups'}") from error
            raise
        finally:
            r.PLAN = plan
            if state["safe_to_clean"]:
                shutil.rmtree(staging)


def require_qualification(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} requires nonblank qualification text")


def timestamp_qualification(r, manifest, writes, inventory):
    """Retain model timestamps while binding execution timing to audited receipts."""
    bindings = {entry["job_id"]: entry for entry in writes["ratings"]}
    jobs = manifest["jobs"]
    if (len(bindings) != len(writes["ratings"]) or len(jobs) != len(bindings)
            or set(bindings) != {job["id"] for job in jobs}):
        raise ValueError("timestamp inspection requires every original Write binding")
    cases = []
    for job in jobs:
        binding = bindings[job["id"]]
        output = ROOT / job["output"]
        source = ROOT / binding["original_attempt"]
        if source.resolve().parent != (r.PLAN / "attempts" / job["id"]).resolve():
            raise ValueError("timestamp source is outside this job's original attempts")
        receipt_path = source / "receipt.json"
        receipt_rel = str(receipt_path.relative_to(ROOT))
        output_sha = r.digest(output)
        receipt_sha = r.digest(receipt_path)
        if (inventory.get(job["output"]) != output_sha
                or binding["evaluation_sha256"] != output_sha
                or inventory.get(receipt_rel) != receipt_sha):
            raise ValueError("timestamp source differs from the audited measurement bytes")
        receipt = json.loads(receipt_path.read_bytes())
        if (receipt.get("status") != "passed" or receipt.get("job_id") != job["id"]
                or receipt.get("evaluation_sha256") != output_sha):
            raise ValueError("timestamp source is not the matching successful receipt")
        started = datetime.fromisoformat(receipt["started_at"].replace("Z", "+00:00"))
        completed = datetime.fromisoformat(receipt["completed_at"].replace("Z", "+00:00"))
        if started.utcoffset() is None or completed.utcoffset() is None or completed < started:
            raise ValueError("launcher receipt lacks a valid timezone-aware execution interval")
        original = json.loads(output.read_bytes()).get("evaluation_timestamp")
        relation = "missing_unparseable_or_timezone_unspecified"
        if isinstance(original, str):
            try:
                timestamp = datetime.fromisoformat(original.replace("Z", "+00:00"))
                if timestamp.utcoffset() is not None:
                    relation = ("within_receipt_interval" if started <= timestamp <= completed
                                else "outside_receipt_interval")
            except ValueError:
                pass
        cases.append({"job_id": job["id"], "output": job["output"],
                      "evaluation_sha256": output_sha, "model_evaluation_timestamp": original,
                      "relation_to_receipt_interval": relation, "receipt": receipt_rel,
                      "receipt_sha256": receipt_sha, "started_at": receipt["started_at"],
                      "completed_at": receipt["completed_at"]})
    outside = sum(case["relation_to_receipt_interval"] == "outside_receipt_interval" for case in cases)
    incomparable = sum(case["relation_to_receipt_interval"] == "missing_unparseable_or_timezone_unspecified" for case in cases)
    return {"issue": 1353, "related_issue": 667, "cases": cases,
            "outside_receipt_interval": outside, "not_comparable": incomparable,
            "qualification": ("Execution times and condition boundaries use launcher receipt started_at/completed_at, "
                "with original receipt hashes recorded in results.json. Model-written evaluation_timestamp values "
                "remain unchanged and are not independently verified, including values inside the recorded interval. "
                f"Of {len(cases)} accepted ratings, {outside} metadata timestamps lie outside their session intervals "
                f"and {incomparable} cannot be compared as timezone-aware timestamps. An interval mismatch alone "
                "does not establish fabrication; approximations and timezone errors can also cause it.")}


def read_narrative_qualification(r, manifest_sha, jobs, path):
    import yaml

    narrative = json.loads(path.read_bytes())
    if narrative["manifest_sha256"] != manifest_sha or not narrative["cases"]:
        raise ValueError("narrative qualification identifies another condition or has no cases")
    for case in narrative["cases"]:
        job = jobs[case["job_id"]]
        if (case["output"] != job["output"] or case["input"] != job["input"]
                or case["evaluation_sha256"] != r.digest(ROOT / job["output"])
                or case["input_sha256"] != r.digest(ROOT / job["input"])):
            raise ValueError("narrative qualification lacks matching source bytes")
        original = json.loads((ROOT / job["output"]).read_bytes())
        if (case["original_score_preserved"] != original["overall_score"]
                or case["operator_score_changes"] != 0 or not case["statements"]):
            raise ValueError("narrative qualification does not preserve the original score or statements")
        for statement in case["statements"]:
            value = original
            for key in statement["pointer"]:
                value = value[key]
            if value != statement["original"]:
                raise ValueError("narrative qualification does not quote the original statement")
        if case.get("input_evidence"):
            source = yaml.safe_load((ROOT / job["input"]).read_bytes())
            for evidence in case["input_evidence"]:
                value = source
                for key in evidence["pointer"]:
                    value = value[key]
                if value != evidence["original"]:
                    raise ValueError("narrative qualification does not quote the original input")
    summary = {"source": path.name, "source_sha256": r.digest(path),
               "scope": narrative["scope"], "qualification": narrative["qualification"],
               "issue": narrative.get("issue"),
               "affected_job_ids": [case["job_id"] for case in narrative["cases"]]}
    return narrative, summary


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
        if r.digest(r.ROOT / rel) != sha:
            raise ValueError(f"measurement changed after audit: {rel}")
    code_archive = audit["measured_code_archive"]
    if (code_archive["registered_path"] != batch.c.MEASURED_PATH
            or code_archive["path"] != batch.c.MEASURED_ARCHIVE
            or code_archive["sha256"] != batch.c.MEASURED_SHA256
            or inventory.get(code_archive["path"]) != code_archive["sha256"]
            or code_archive["scheduler_path"] != batch.c.MEASURED_SCHEDULER_ARCHIVE
            or code_archive["scheduler_sha256"] != batch.c.MEASURED_SCHEDULER_SHA256
            or inventory.get(code_archive["scheduler_path"]) != code_archive["scheduler_sha256"]
            or r.digest(ROOT / code_archive["preservation_record"]) != code_archive["preservation_record_sha256"]):
        raise ValueError("report lacks the matching measured-code archive")
    timing = timestamp_qualification(r, manifest, writes, inventory)
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
    all_jobs = {j["id"]: j for j in manifest["jobs"]}
    narrative, narrative_qualification = read_narrative_qualification(
        r, audit["manifest_sha256"], all_jobs, plan / "canary_narrative_qualification.json")
    cm4ai_narrative, cm4ai_qualification = read_narrative_qualification(
        r, audit["manifest_sha256"], all_jobs, plan / "cm4ai_pilot_narrative_qualification_1355.json")
    for name, value in (
            ("semantic inspection", review["qualification"]),
            ("execution boundary", execution["qualification"]),
            ("execution deadline", deadline_boundary["qualification"]),
            ("cost accounting", audit["cost_qualification"]),
            ("evaluation prose", narrative["qualification"]),
            ("CM4AI pilot judgments", cm4ai_narrative["qualification"]),
            ("evaluation timing", timing["qualification"]),
            ("measured code archive", code_archive["qualification"])):
        require_qualification(value, name)
    banner = ("**Semantic inspection — Q19:** " + review["qualification"]
              + " See the [24-rating inspection](semantic_review.md).\n\n"
              + "**Execution boundary:** " + execution["qualification"]
              + " Repeat panels spanning it: " + ", ".join(execution["repeat_panels_spanning_boundary"])
              + ". See [the dated registration](validator_status_registration.json).\n\n"
              + "**Execution deadline:** " + deadline_boundary["qualification"]
              + " See [the deadline registration](deadline_registration_1351.json).\n\n"
              + "**Incomplete cost accounting:** " + audit["cost_qualification"] + "\n\n"
              + "**Evaluation prose:** " + narrative["qualification"]
              + " See [the original statements and interpretation](canary_narrative_qualification.json).\n\n"
              + "**CM4AI pilot judgments:** " + cm4ai_narrative["qualification"]
              + " See [the original statements and input evidence](cm4ai_pilot_narrative_qualification_1355.json).\n\n"
              + "**Evaluation timing:** " + timing["qualification"] + "\n\n"
              + "**Measured code archive:** " + code_archive["qualification"]
              + " See [the preservation record](report_dispatch_preservation_1356.json).\n\n")
    with staged_publication(r) as staging:
        results = r.report_results(manifest)
        if (results["completed"] != 56 or results["pending"]
                or any(row["ratings"] != 3 for row in results["repeatability"])):
            raise ValueError("reported cohort or repeat panel is incomplete")
        results["provider_condition"] = "LBL CBORG / 2026-09-12 with execution-metadata provenance; separate from preliminary and prior reference runs"
        results["semantic_qualification"] = qualification
        results["execution_permission_boundary"] = execution
        results["execution_deadline_boundary"] = deadline_boundary
        results["evaluation_narrative_qualification"] = narrative_qualification
        results["additional_evaluation_narrative_qualifications"] = [cm4ai_qualification]
        results["evaluation_timestamp_qualification"] = timing
        results["measured_code_archive"] = code_archive
        results["cost_accounting"] = {key: audit[key] for key in (
            "cost_accounting_complete", "cli_reported_total_cost_usd", "known_terminal_cli_cost_usd",
            "unpriced_excluded_sessions", "cost_qualification")}
        r.write_json(staging / "results.json", results)
        text = (staging / "results.md").read_text().replace(str(ROOT) + "/", "")
        title, rest = text.split("\n", 1)
        for case in flagged:
            text_path = case["output"]
            rest = rest.replace(f"| {text_path} |", f"| {text_path} [Q19 inspection](semantic_review.md) |")
        (staging / "results.md").write_text(title + "\n\n" + banner + rest.lstrip("\n"))
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
        (staging / "completion_summary.md").write_text("\n".join(lines))
        lines = ["# Q19 inspection of the CBORG reference measurements", "", review["scope"], "", banner.rstrip(), "",
                 "The frozen rule permits complete textual provenance as well as W3C PROV-O graphs. A representation-related objection is flagged for adjudication; this inspection does not assign replacement scores or certify other judgments or external source truth.", ""]
        for case in cases:
            q = case["q19"]
            lines += [f"## {case['job_id']}", "", f"Recorded Q19: {q['score']}/{q['max_score']}. Status: `{case['status']}`.", "", case["assessment"], "",
                      f"Original output: [evaluation](../../{case['output']}); SHA256 `{case['evaluation_sha256']}`.", "",
                      "Original Q19 object:", "", "```json", json.dumps(q, indent=2), "```", ""]
        (staging / "semantic_review.md").write_text("\n".join(lines))
    print(f"Rendered 56 original measurements and {len(cases)} Q19 inspections; {len(flagged)} require adjudication.")


if __name__ == "__main__":
    main()
