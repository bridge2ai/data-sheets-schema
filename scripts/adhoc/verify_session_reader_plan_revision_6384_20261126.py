#!/usr/bin/env python3
"""Build and compare thirty offline v6 plans for issue 6384, 2026-11-26.

Inputs: a fresh committed source checkout and thirty accepted baseline plans and
receipts. Outputs: a fresh plan-only bundle and identity receipt under an explicit
evidence directory. No auth content, response, candidate or evaluation is read;
no scorer, validator or native executable is invoked. The existing repeat-plan
verifier enumerates path relocation; the existing root-plan verifier pins the
composed definitions. Only the runner hash may differ after that relocation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True

from verify_root_scope_repeat_plans_20261126 import physical, relocated_plan
from verify_root_scope_plan_evidence_20261125 import verify_definition
from replay_scorer_session_identity_6384_20261126 import require_output_outside


RUNNER = "scripts/adhoc/score_semantic_rubric_codex_20261125.py"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path, maximum=32 * 1024 * 1024):
    path = physical(path)
    require(path.is_file() and 0 < path.stat().st_size <= maximum,
            "input is not a bounded nonempty regular file")
    return path.read_bytes()


def document(path):
    raw = read(path)
    value = json.loads(raw)
    require(isinstance(value, dict), "input JSON must be a mapping")
    return value, sha(raw)


def git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], check=True,
                          capture_output=True, timeout=60).stdout


def write_json(path, value):
    rendered = (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()
    with path.open("xb") as stream:
        stream.write(rendered)
    require(path.read_bytes() == rendered, "saved evidence bytes differ")
    return sha(rendered)


def preflight(args):
    """Check relocated input bytes before freezing source; never build a plan."""
    root, baseline_root = physical(args.repo_root), physical(args.baseline_runs)
    out = physical(args.evidence_directory)
    require(not out.exists() and root != out and root not in out.parents,
            "preflight evidence must be fresh and outside source")
    require(baseline_root != out and baseline_root not in out.parents,
            "preflight evidence must be outside baseline run tree")
    require_output_outside(out, (root, baseline_root))
    plan_paths = sorted(baseline_root.glob("*/plan.json"))
    require(len(plan_paths) == 30, "expected thirty baseline plans")
    checks, executables, records, problems = {}, {}, set(), []
    for path in plan_paths:
        plan, _ = document(path)
        receipt, _ = document(path.with_name("receipt.json"))
        require(receipt.get("status") == "VALIDATED_AND_PUBLISHED"
                and receipt.get("plan_sha256") == sha(json.dumps(plan, sort_keys=True).encode()),
                "baseline receipt is not accepted and bound")
        require(plan["runner_sha256"] == args.measured_runner_sha256, "measured runner hash differs")
        old_root = physical(plan["repo_root"])
        records.add(plan["identity"]["d4d_file"])
        verify_definition(plan, root)
        sources = [(item["source"], item["sha256"]) for name, item in plan["inputs"].items()
                   if name != "agent-definition.md"] + list(plan["validation_sha256"].items())
        for old_source, digest in sources:
            relative = physical(old_source).relative_to(old_root)
            target = root / relative
            if str(relative) not in checks:
                if not target.is_file():
                    checks[str(relative)] = {"expected_sha256": digest, "exists": False}
                    problems.append("missing relocated input: " + str(relative))
                    continue
                actual = sha(read(target))
                checks[str(relative)] = {"expected_sha256": digest, "actual_sha256": actual,
                                         "exists": True, "tracked": bool(git(root, "ls-files", "--", str(relative)).strip())}
            require(checks[str(relative)]["expected_sha256"] == digest, "baseline input hashes disagree")
            if checks[str(relative)].get("actual_sha256") != digest:
                problems.append("relocated input bytes differ: " + str(relative))
        for executable, digest in plan["executable_sha256"].items():
            if executable not in executables:
                actual = sha(read(Path(executable).resolve(strict=True), 512 * 1024 * 1024))
                executables[executable] = {"expected_sha256": digest, "actual_sha256": actual}
            require(executables[executable]["expected_sha256"] == digest, "baseline executable hashes disagree")
            if executables[executable]["actual_sha256"] != digest:
                problems.append("installed executable bytes differ from measured binding")
    out.mkdir(parents=False, exist_ok=False)
    receipt = {"status": "PASSED" if not problems else "BLOCKED", "baseline_count": len(plan_paths),
               "record_count": len(records), "relocated_inputs": checks, "executables": executables,
               "problems": sorted(set(problems)), "inputs_staged": 0, "scoring_calls": 0,
               "validator_calls": 0, "auth_content_read": False}
    digest = write_json(out / "preflight.json", receipt)
    print(json.dumps({"status": receipt["status"], "receipt_sha256": digest,
                      "baseline_count": len(plan_paths), "record_count": len(records),
                      "input_paths_checked": len(checks), "inputs_staged": 0,
                      "problems": receipt["problems"]}, sort_keys=True))
    return 0 if not problems else 2


def compare(args):
    root, baseline_root = physical(args.repo_root), physical(args.baseline_runs)
    out = physical(args.evidence_directory)
    require(not out.exists(), "evidence directory must be fresh")
    require(root != out and root not in out.parents, "evidence must be outside source checkout")
    require(baseline_root != out and baseline_root not in out.parents,
            "evidence must be outside baseline run tree")
    require_output_outside(out, (root, baseline_root))
    from score_semantic_rubric_codex_20261125 import build_plan, parser as scorer_parser

    require(root == physical(Path(__file__).resolve().parents[2]), "helper must run from the source checkout")
    expected_head = git(root, "rev-parse", args.expected_head).decode().strip()
    require(git(root, "rev-parse", "HEAD").decode().strip() == expected_head, "source HEAD differs")
    require(not git(root, "diff", "HEAD", "--"), "tracked source has uncommitted changes")
    runner_sha = sha(read(root / RUNNER))
    require(runner_sha != args.measured_runner_sha256, "reader revision did not change the runner hash")
    require(read(root / RUNNER) == git(root, "show", expected_head + ":" + RUNNER),
            "runner differs from frozen committed source")
    plan_paths = sorted(baseline_root.glob("*/plan.json"))
    require(len(plan_paths) == 30, "expected exactly thirty immediate accepted baseline plans")
    out.mkdir(parents=False, exist_ok=False)
    plans, rows, fingerprints, identities = [], [], {}, set()
    try:
        for old_path in plan_paths:
            baseline, plan_sha = document(old_path)
            receipt_path = old_path.with_name("receipt.json")
            receipt, receipt_sha = document(receipt_path)
            require(receipt.get("status") == "VALIDATED_AND_PUBLISHED", "baseline scoring was not accepted")
            require(receipt.get("plan_sha256") == sha(json.dumps(baseline, sort_keys=True).encode()),
                    "baseline receipt does not bind its saved plan")
            require(baseline["runner_sha256"] == args.measured_runner_sha256,
                    "baseline reader hash differs from the named measured revision")
            identity = baseline["identity"]
            require(identity["version"] == "6.0", "baseline is not root-scope v6")
            key = (identity["d4d_file"], identity["rubric"])
            require(key not in identities, "duplicate baseline record/rubric")
            identities.add(key)
            run = out / "uncreated-runs" / old_path.parent.name
            expected = relocated_plan(baseline, root, run)
            expected["runner_sha256"] = runner_sha
            argv = ["--repo-root", str(root), "--method-directory", identity["method"],
                    "--label", identity["label"], "--record", expected["inputs"]["record.yaml"]["source"],
                    "--rubric", identity["rubric"], "--run-directory", str(run),
                    "--semantic-version", "6.0", "--scope-context", expected["inputs"]["scope-context.json"]["source"],
                    "--codex-binary", baseline["command"][0],
                    "--poetry-binary", baseline["validation_command"][0],
                    "--validation-venv", baseline["validation_venv"], "--auth-file", baseline["auth_file"], "--plan"]
            if "caller-context.yaml" in expected["inputs"]:
                argv.extend(["--context", expected["inputs"]["caller-context.yaml"]["source"]])
            plan = build_plan(scorer_parser().parse_args(argv))
            differing = sorted(name for name in set(expected) | set(plan)
                               if name not in expected or name not in plan or expected[name] != plan[name])
            require(not differing, "new plan differs beyond explicit paths and runner hash: " + ", ".join(differing))
            require(plan["prompt"] == baseline["prompt"] and plan["prompt_sha256"] == baseline["prompt_sha256"],
                    "prompt bytes changed")
            require(plan["definition_provenance"] == baseline["definition_provenance"],
                    "composed definition provenance changed")
            definition = verify_definition(plan, root)
            for name, item in plan["inputs"].items():
                require(item["sha256"] == baseline["inputs"][name]["sha256"], "measured input changed: " + name)
                if name != "agent-definition.md":
                    path = physical(item["source"])
                    require(sha(read(path)) == item["sha256"], "source bytes differ from plan: " + name)
                    fingerprints[str(path)] = item["sha256"]
            for name, digest in plan["validation_sha256"].items():
                require(sha(read(name)) == digest, "validator dependency bytes changed")
                fingerprints[name] = digest
            fingerprints[str(old_path)], fingerprints[str(receipt_path)] = plan_sha, receipt_sha
            require(not run.exists() and not Path(plan["output"]).exists(), "plan created execution or publication output")
            plans.append(plan)
            rows.append({"identity": identity, "baseline_plan_sha256": plan_sha,
                         "baseline_receipt_sha256": receipt_sha,
                         "new_plan_sha256": sha(json.dumps(plan, sort_keys=True).encode()),
                         "prompt_sha256": plan["prompt_sha256"], "definition_provenance": definition,
                         "input_sha256": {name: value["sha256"] for name, value in plan["inputs"].items()},
                         "full_plan_equal_after_explicit_paths_and_runner_hash": True})
        require(len(plans) == 30 and len({row["identity"]["d4d_file"] for row in rows}) == 15,
                "series must contain fifteen records and thirty evaluations")
        require(len({plan["run_directory"] for plan in plans}) == len({plan["output"] for plan in plans}) == 30,
                "planned runs or outputs are not distinct")
        require(len({row["identity"]["method"] for row in rows}) == 1, "plans span multiple methods")
        labels = {row["identity"]["label"] for row in rows}
        require(len(labels) == 3 and len({label.rsplit("_rep", 1)[0] for label in labels}) == 1,
                "plans do not describe one three-replicate series")
        for name, digest in fingerprints.items():
            require(sha(read(name)) == digest, "protected plan/receipt/input changed during verification")
        require(git(root, "rev-parse", "HEAD").decode().strip() == expected_head
                and not git(root, "diff", "HEAD", "--"), "source changed during verification")
        require(not (out / "uncreated-runs").exists(), "plan-only builds created a run directory")
        bundle = {"mode": "PLAN_ONLY", "record_count": 15, "evaluation_count": 30, "plans": plans}
        bundle_sha = write_json(out / "plans.json", bundle)
        receipt = {"status": "PASSED", "source_head": expected_head, "record_count": 15,
                   "evaluation_count": 30, "plans_sha256": bundle_sha,
                   "measured_runner_sha256": args.measured_runner_sha256,
                   "new_runner_sha256": runner_sha,
                   "allowed_non_path_changes": ["runner_sha256"],
                   "instrument_revision_discriminator": "scorer_instrument.runner_sha256",
                   "full_plan_equal_after_explicit_paths_and_runner_hash": True,
                   "all_prompts_byte_identical": True, "all_measured_inputs_byte_identical": True,
                   "scoring_calls": 0, "validator_calls": 0, "evaluation_writes": 0,
                   "run_directories_created": 0, "auth_content_read": False,
                   "protected_input_sha256": fingerprints, "rows": rows}
        receipt_sha = write_json(out / "verification.json", receipt)
        print(json.dumps({"status": "PASSED", "record_count": 15, "evaluation_count": 30,
                          "plans_sha256": bundle_sha, "verification_sha256": receipt_sha,
                          "measured_runner_sha256": args.measured_runner_sha256,
                          "new_runner_sha256": runner_sha}, sort_keys=True))
    except Exception as error:
        write_json(out / "failure.json", {"status": "REFUSED", "reason": str(error),
                                          "source_head": expected_head, "completed_plans": len(plans),
                                          "scoring_calls": 0, "validator_calls": 0,
                                          "evaluation_writes": 0, "auth_content_read": False})
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--baseline-runs", type=Path, required=True)
    parser.add_argument("--evidence-directory", type=Path, required=True)
    parser.add_argument("--expected-head")
    parser.add_argument("--measured-runner-sha256", required=True)
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()
    if args.preflight:
        return preflight(args)
    require(args.expected_head, "final plan builds require --expected-head")
    compare(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
