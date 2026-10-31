#!/usr/bin/env python3
"""D68-D70/#5212 review item 7: retain LR9-LR13 repairs, 2026-10-30.

Inputs: original merge failures, unchanged-d9 controls and the 13-case repair
report. Output: explicit introduced-failure dispositions with original traces
and successful replacement phases. Does not run tests or alter input evidence.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("repair_report", type=Path)
parser.add_argument("--verifier-before", required=True, type=Path)
parser.add_argument("--verifier-after", required=True, type=Path)
parser.add_argument("--output", required=True, type=Path)
args = parser.parse_args()
repair = json.loads(args.repair_report.read_text())
assert repair["exit_code"] == 0 and len(repair["selected"]) == 13
assert len(repair["reports"]) == 39 and all(row["outcome"] == "passed" for row in repair["reports"])
old_reports = sorted((ROOT / ".d68-validation/merge/.d68-validation").glob("merge-serial-shard-*-of-6/d68-result.json"))
assert {f"merge-serial-shard-{i}-of-6" for i in (1, 2, 3)}.issubset(
    {path.parent.name for path in old_reports})
baseline_reports = sorted((ROOT / ".d68-validation/base/.d68-validation").glob("*/d68-result.json"))
base_passes = {}
for path in baseline_reports:
    data = json.loads(path.read_text())
    assert data["environment"]["head"] == "d9b69d84d9a6936809681ae240bb8e767649ca11"
    for row in data["reports"]:
        if row["when"] == "call" and row["outcome"] == "passed":
            base_passes.setdefault(row["nodeid"], []).append(str(path.relative_to(ROOT)))
tracked = set(subprocess.check_output([
    "git", "ls-tree", "-r", "--name-only", "d9b69d84d"], cwd=ROOT, text=True).splitlines())
cli_prefix = "tests/test_d68_legacy_readonly.py::test_cli_refuses_legacy_and_stripped_runs_readonly["
ownership = "tests/test_shared_output_ownership_entrypoints.py::test_legacy_public_boundary_is_unchanged"
profile = "tests/test_profiles.py::TestRoundFour::test_a_repair_round_sends_the_specs_digest"
current = "tests/test_download/test_api_runner.py::TestResumeUsesArtifactsNotOnlyProgress::test_legacy_completed_outputs_without_accounting_are_not_clean_resumes"
rows = []
for path in old_reports:
    data = json.loads(path.read_text())
    for old in data["reports"]:
        node = old["nodeid"]
        if old["outcome"] != "failed" or not (node.startswith(cli_prefix) or node in {ownership, profile, current}):
            continue
        assert old["when"] == "call"
        if node.startswith(cli_prefix):
            finding = "LR9"
            replacement = [node]
            assert node.split("::")[0] not in tracked
            baseline = "New test file absent from committed d9; this is an introduced test setup failure."
            resolution = "Satisfy the independent cwd guard using checkout_at before CLI invocation; retain absolute evidence paths, the provider trap and whole-tree preservation."
        elif node == ownership:
            finding = "LR10"
            replacement = [node.replace("is_unchanged", "refuses_residue_before_any_write") + f"[{value}]" for value in ("True", "False")]
            assert base_passes.get(node), "Demonstrate the old assertion passed on unchanged d9"
            baseline = base_passes[node]
            resolution = "D68/D69 intentionally replace orphan-residue continuation with a pre-lock refusal, for both resume values; assert zero execution and unchanged whole tree."
        elif node == profile:
            finding = "LR11"
            replacement = [node]
            assert base_passes.get(node), "Demonstrate the old fixture passed on unchanged d9"
            baseline = base_passes[node]
            resolution = "Prepare a current guarded generation before writing its deliberately invalid partial output; retain the actual repair call and selected-profile digest assertion."
        else:
            finding = "LR13"
            replacement = [node.replace("test_legacy_completed_outputs", "test_journalless_current_outputs")]
            assert base_passes.get(node), "Demonstrate the old diagnostic assertion passed on unchanged d9"
            baseline = base_passes[node]
            resolution = "The synthesized record names the current post-D41 commit. Expect the earlier journal-less inspection-only refusal and preserve the entire temporary tree, zero calls and absent ledger/journal."
        phases = [row for row in repair["reports"] if row["nodeid"] in replacement]
        assert len(phases) == 3 * len(replacement) and all(row["outcome"] == "passed" for row in phases)
        rows.append({"finding": finding, "old_nodeid": node, "old_head": data["environment"]["head"],
                     "old_report": str(path.relative_to(ROOT)), "old_trace": old["message"],
                     "baseline": baseline, "resolution": resolution, "replacement_nodes": replacement,
                     "repair_head": repair["environment"]["head"], "repair_phases": phases,
                     "repair_report": str(args.repair_report),
                     "repair_report_sha256": hashlib.sha256(args.repair_report.read_bytes()).hexdigest(),
                     "resolution_verified": True})
assert len(rows) == 12 and {row["finding"] for row in rows} == {"LR9", "LR10", "LR11", "LR13"}
before = json.loads(args.verifier_before.read_text())
after = json.loads(args.verifier_after.read_text())
node = "tests/test_d68_legacy_readonly.py::test_completed_legacy_verifier_is_readonly[split]"
assert before["selected"] == [node] and before["exit_code"] == 1
[failed] = [row for row in before["reports"] if row["outcome"] == "failed"]
assert failed["nodeid"] == node and failed["when"] == "call"
assert not before["collection_errors"] and not after["collection_errors"]
assert after["exit_code"] == 0 and all(row["outcome"] == "passed" for row in after["reports"])
replacement = [value for value in after["selected"] if value == node or
               "::test_verifier_ignores_unrelated_projects" in value or
               "::test_verifier_rejects_incomplete_or_changed_evidence" in value]
assert node in replacement and any("ignores_unrelated_projects" in value for value in replacement)
phases = [row for row in after["reports"] if row["nodeid"] in replacement]
assert len(phases) == len(replacement) * 3
rows.append({"finding": "LR12", "old_nodeid": node,
    "old_head": before["environment"]["head"], "old_report": str(args.verifier_before),
    "old_report_sha256": hashlib.sha256(args.verifier_before.read_bytes()).hexdigest(),
    "old_trace": failed["message"],
    "baseline": "New verifier regression; the verifier is absent from d9. The old packet fails on an authentic f8 default-layout capture.",
    "resolution": "Map declared full/core paths independently, scope inventory to selected project artifacts and bound inputs, and retain ownership/hash/accounting and selected-symlink checks.",
    "replacement_nodes": replacement, "repair_head": after["environment"]["head"],
    "repair_phases": phases, "repair_report": str(args.verifier_after),
    "repair_report_sha256": hashlib.sha256(args.verifier_after.read_bytes()).hexdigest(),
    "resolution_verified": True})
assert not args.output.exists(), "Preserve previous evidence"
args.output.write_text(json.dumps(rows, indent=2) + "\n")
print(json.dumps({"resolved_failed_phases": len(rows), "repair_cases": 13,
                  "verifier_regression_cases": len(replacement), "output": str(args.output)}))
