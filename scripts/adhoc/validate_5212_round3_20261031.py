#!/usr/bin/env python3
"""#5212 round 3, 2026-10-31: serial validation of a pinned archive, offline.

Inputs: archive directory, phase, unique output name. Outputs: external pytest
logs/reports and a scratch-only shard plan using CI's actual plugin/timings.
Launch under d73_offline_20261031.sb; no tests execute in the live checkout.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / "scratch-5212fix"
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("tree")
parser.add_argument("phase", choices=["canary", "regressions", "focused", "broad", "collect", "shard", "xdist-canary"])
parser.add_argument("name")
parser.add_argument("--collection")
args = parser.parse_args()
tree = (SCRATCH / args.tree).resolve()
assert tree.parent == SCRATCH and tree != ROOT
base = SCRATCH / args.name
assert base.parent == SCRATCH and not base.exists()
head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=tree, text=True).strip()
assert not subprocess.check_output(["git", "diff", "HEAD", "--name-only"], cwd=tree, text=True)
FOCUSED = ["tests/test_d68_legacy_readonly.py", "tests/test_d69_fail_closed.py",
    "tests/test_d69_artifact_completeness.py", "tests/test_d70_record_age.py",
    "tests/test_latch_journal.py", "tests/test_abandoned_journal.py", "tests/test_api_latch_guard.py",
    "tests/test_registered_eval_runner.py", "tests/test_canary_gate.py"]
BROAD = ["tests/test_shared_generation_runtime.py", "tests/test_receipt_completion_runtime.py",
    "tests/test_removal_repair.py", "tests/test_resume_inputs.py", "tests/test_snapshot_attempt_recovery.py",
    "tests/test_resume_instrument_and_activation.py", "tests/test_profiles.py",
    "tests/test_download/test_api_runner.py", "tests/test_usage_ledger.py", "tests/test_thinking_request.py",
    "tests/test_method_resolution.py", "tests/test_report_gate.py", "tests/test_duplicate_keys.py",
    "tests/test_packaging_review_r7.py", "tests/test_pr5212_d55_fixes.py", "tests/test_d42_claude_d55.py",
    "tests/test_pr5212_r3_fixes.py", "tests/test_pr5212_r4_fixes.py", "tests/test_d41_request_parity.py"]
changed = []
for before, after in (("c9567e3c3", head), ("f5e78ff02", "867e5bb04")):
    changed += subprocess.check_output(["git", "diff", "--name-only", before, after, "--", "tests"],
                                      cwd=tree, text=True).splitlines()
changed = [p for p in changed if p.endswith(".py") and (tree / p).is_file()]
if args.phase == "canary":
    selected = ["tests/test_d68_legacy_readonly.py::test_fresh_prefix_project_does_not_claim_sibling_artifacts[projects0-flat]"]
elif args.phase == "regressions":
    selected = ["tests/test_d69_fail_closed.py", "tests/test_resume_instrument_and_activation.py",
        "tests/test_download/test_api_runner.py::TestValidatorDrivenRepair::test_intermediates_do_not_claim_a_prefix_sibling_project",
        "tests/test_download/test_api_runner.py::TestResumeUsesArtifactsNotOnlyProgress::test_a_flat_out_dir_does_not_let_a_new_label_claim_old_outputs",
        "tests/test_pr5212_d55_fixes.py::test_resume_accepts_recorded_head_and_fresh_launch_needs_none",
        *["tests/test_usage_ledger.py::" + name for name in (
            "test_shared_outputs_reject_overlapping_resume_fresh_and_other_labels",
            "test_split_and_flat_layouts_cannot_overlap_in_either_direction",
            "test_the_concurrency_test_joins_its_worker_when_a_contender_check_fails",
            "test_the_concurrency_test_reports_a_first_run_that_fails_early",
            "test_the_concurrency_test_fails_a_first_run_that_hangs",
            "test_the_concurrency_test_reports_a_first_run_that_fails_after_polling_began",
            "test_the_concurrency_test_reports_a_first_run_that_fails_after_release",
            "test_the_concurrency_test_reports_a_first_run_that_ends_without_the_boundary")]]
elif args.phase == "focused":
    selected = sorted(set(FOCUSED + [p for p in changed if p not in BROAD]))
elif args.phase == "broad":
    selected = sorted(set(BROAD + changed) - set(FOCUSED))
elif args.phase == "collect":
    selected = ["tests", "--collect-only"]
else:
    assert args.collection
    collection = json.loads((SCRATCH / args.collection / "d73-result.json").read_text())
    assert collection["exit_code"] == 0 and not collection["collection_errors"]
    assert collection["environment"]["head"] == head
    sys.path.insert(0, str(ROOT / "scripts/adhoc"))
    from d41_legacy_controls_20261029 import bootstrap
    bootstrap(tree, SCRATCH)
    from utils.pytest_shard import balanced_files, partition_lanes, read_weights
    ordinary = partition_lanes(collection["selected"])["ordinary"]
    owners = balanced_files((node.split("::", 1)[0] for node in ordinary), 4,
                           read_weights(tree / "utils/ci_test_durations.json"))
    shard = owners[FOCUSED[0]]
    plan = {"head": head, "shard": f"{shard}/4", "selected": [node for node in ordinary
        if owners[node.split("::", 1)[0]] == shard]}
    (SCRATCH / (args.name + "-shard-plan.json")).write_text(json.dumps(plan, indent=2) + "\n")
    selected = ["tests", "-v", "-p", "utils.pytest_shard", f"--ci-shard={shard}/4",
        "--ci-shard-timings=utils/ci_test_durations.json", "--ci-lane=ordinary", "--durations=25",
        "-n", "logical", "--maxprocesses=4", "--dist", "load", "--maxschedchunk=1"]
    if args.phase == "xdist-canary":
        selected += ["--d73-canary-node",
            "tests/test_d68_legacy_readonly.py::test_completed_legacy_verifier_is_readonly[i1]"]
selected += ["-q", "--tb=short", "--basetemp", str(base), "--junitxml", str(base) + ".xml"]
command = [sys.executable, "-S", "-P", "-B", str(ROOT / "scripts/adhoc/run_d73_offline_20261031.py"),
           "--tree", str(tree), *selected]
(SCRATCH / (args.name + "-selection.json")).write_text(json.dumps(
    {"head": head, "tree": tree.name, "arguments": selected}, indent=2) + "\n")
os.execv(sys.executable, command)
