#!/usr/bin/env python3
"""#5212/D73, 2026-10-31: select and run the requested offline validation phases.

Inputs: phase, optional unique suffix, committed CI timing/plugin and collection.
Outputs: exact phase selection and launcher reports under scratch-5212fix only.
The xdist canary uses the full real shard selection before retaining one node.
"""
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / "scratch-5212fix"
FOCUSED = ["tests/test_d68_legacy_readonly.py", "tests/test_d70_record_age.py",
           "tests/test_latch_journal.py", "tests/test_api_latch_guard.py", "tests/test_usage_ledger.py"]
BROAD_EXTRA = ["tests/test_shared_generation_runtime.py", "tests/test_receipt_completion_runtime.py",
    "tests/test_removal_repair.py", "tests/test_canary_gate.py", "tests/test_resume_inputs.py",
    "tests/test_snapshot_attempt_recovery.py", "tests/test_resume_instrument_and_activation.py",
    "tests/test_profiles.py", "tests/test_download/test_api_runner.py", "tests/test_thinking_request.py",
    "tests/test_method_resolution.py", "tests/test_report_gate.py", "tests/test_duplicate_keys.py",
    "tests/test_registered_eval_runner.py", "tests/test_packaging_review_r7.py",
    "tests/test_pr5212_d55_fixes.py", "tests/test_d42_claude_d55.py", "tests/test_pr5212_r3_fixes.py",
    "tests/test_pr5212_r4_fixes.py", "tests/test_d41_request_parity.py"]

phase = sys.argv[1]
name = phase + ("-" + sys.argv[2] if len(sys.argv) > 2 else "")
if phase == "focused":
    args = [*FOCUSED, "-q", "--tb=short"]
elif phase == "broad":
    changed = subprocess.check_output(["git", "diff", "--name-only", "f5e78ff02", "--", "tests"],
                                      cwd=ROOT, text=True).splitlines()
    files = sorted(set(FOCUSED + BROAD_EXTRA + [p for p in changed if p.endswith(".py")]))
    args = [*files, "-q", "--tb=short"]
elif phase == "collect":
    args = ["tests", "--collect-only", "-q"]
elif phase in {"xdist-canary", "shard"}:
    # Import exactly the CI plugin, not a copied balancing implementation.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from d41_legacy_controls_20261029 import bootstrap
    bootstrap(ROOT, SCRATCH)
    from utils.pytest_shard import balanced_files, partition_lanes, read_weights
    collection = json.loads((SCRATCH / "collect/d73-result.json").read_text())
    assert collection["exit_code"] == 0 and not collection["collection_errors"]
    ordinary = partition_lanes(collection["selected"])["ordinary"]
    weights = read_weights(ROOT / "utils/ci_test_durations.json")
    owners = balanced_files((node.split("::", 1)[0] for node in ordinary), 4, weights)
    shard = owners[FOCUSED[0]]
    selected = [node for node in ordinary if owners[node.split("::", 1)[0]] == shard]
    (SCRATCH / "d73-shard-plan.json").write_text(json.dumps({"shard": f"{shard}/4",
        "collection_head": collection["environment"]["head"], "owners": owners,
        "selected": selected, "collected": len(collection["selected"])}, indent=2) + "\n")
    args = ["tests", "-v", "-p", "no:cacheprovider", "-p", "utils.pytest_shard",
        f"--ci-shard={shard}/4", "--ci-shard-timings=utils/ci_test_durations.json", "--ci-lane=ordinary",
        "--durations=25", "-n", "logical", "--maxprocesses=4", "--dist", "load", "--maxschedchunk=1",
        f"--junitxml={SCRATCH / (name + '.xml')}"]
    if phase == "xdist-canary":
        canary = next(node for node in selected if "test_completed_legacy_verifier_is_readonly[i1]" in node)
        args.extend(["--d73-canary-node", canary])
else:
    raise SystemExit(f"unknown phase: {phase}")
args.extend(["--basetemp", str(SCRATCH / name)])
(SCRATCH / (name + "-selection.json")).write_text(json.dumps(args, indent=2) + "\n")
os.execv(sys.executable, [sys.executable, "-S", "-P", "-B",
    str(ROOT / "scripts/adhoc/run_d73_offline_20261031.py"), *args])
