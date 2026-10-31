#!/usr/bin/env python3
"""D68-D70/#5212 serial integration gates, 2026-10-30.

Input: installed Python and stage; run from the packet/scratch merge worktree.
Output: per-process JSON reports under .d68-validation and a stage ledger.
Canary exercises the exact sandbox/launcher/subprocess path before shard fanout.
No remotes, provider calls or concurrency. CI test selection, native interpreter.
"""
import argparse
import json
from pathlib import Path
import shlex
import subprocess
import sys
from d68_process_logging_20261030 import run_logged

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("python")
parser.add_argument("stage", choices=("canary", "logging-canary", "collect", "shards", "notes-canary", "notes",
                                     "repair-canary", "repairs", "d41", "focused"))
parser.add_argument("--tag", default="merge-final")
parser.add_argument("--canary-node", help="One explicit ordinary test node for an unchanged baseline")
parser.add_argument("--only", action="append", choices=(
    *(f"shard-{i}-of-6" for i in range(1, 7)),
    "routing-dispatch", "routing-portable", "routing-regate", "routing-default-layout"),
    help="Rerun explicitly affected CI jobs; retained full coverage must account for the other jobs")
args = parser.parse_args()
storage = ROOT / ".d68-validation"
storage.mkdir(exist_ok=True)
head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


if args.stage in {"shards", "notes"}:
    subprocess.run(["git", "merge-base", "--is-ancestor", "50bc50af6", head], cwd=ROOT, check=True)
if args.stage in {"shards", "notes", "repairs", "d41", "focused"}:
    prerequisite = ("notes-canary" if args.stage == "notes" else
                    "repair-canary" if args.stage == "repairs" else "canary")
    canary = json.loads((storage / f"{args.tag}-{prerequisite}.json").read_text())
    assert canary["head"] == head and canary["runs"][0]["exit_code"] == 0

if args.stage == "canary":
    canary_node = args.canary_node or "tests/test_d68_legacy_readonly.py::test_completed_legacy_verifier_is_readonly[i1]"
    assert "::" in canary_node and not canary_node.startswith("-"), canary_node
    cases = [("canary", [canary_node])]
elif args.stage == "logging-canary":
    cases = [("logging-canary", ["scripts/adhoc/d68_logging_probe_20261030.py::test_live_log_preserves_checkout"])]
elif args.stage == "repair-canary":
    cases = [("repair-canary", ["tests/test_d68_legacy_readonly.py::test_cli_refuses_legacy_and_stripped_runs_readonly[P4]"])]
elif args.stage == "repairs":
    cases = [("repairs", [
        "tests/test_d68_legacy_readonly.py::test_cli_refuses_legacy_and_stripped_runs_readonly",
        "tests/test_shared_output_ownership_entrypoints.py::test_legacy_public_boundary_refuses_residue_before_any_write",
        "tests/test_profiles.py::TestRoundFour::test_a_repair_round_sends_the_specs_digest"])]
elif args.stage == "focused":
    cases = [("focused", ["tests/test_d68_legacy_readonly.py", "tests/test_d70_record_age.py",
        "tests/test_latch_journal.py", "tests/test_api_latch_guard.py",
        "tests/test_usage_ledger.py::test_new_identity_in_a_shared_directory_starts_its_own_generation",
        "tests/test_usage_ledger.py::test_output_aliases_share_the_physical_file_lock",
        "tests/test_abandoned_journal.py::test_a_legacy_continuation_adopts_rows_without_a_generation_before_its_boundary"])]
elif args.stage == "d41":
    cases = [("d41", [f"tests/{name}" for name in (
        "test_latch_journal.py", "test_api_latch_guard.py", "test_pr5212_d55_fixes.py",
        "test_d42_claude_d55.py", "test_pr5212_r3_fixes.py", "test_pr5212_r4_fixes.py",
        "test_d41_request_parity.py")])]
elif args.stage == "collect":
    cases = [("collect-whole", ["--collect-only"]), ("collect-ci", ["tests", "--collect-only"])]
elif args.stage == "shards":
    cases = [(f"shard-{i}-of-6", ["tests", "-p", "utils.pytest_shard", f"--ci-shard={i}/6",
               "--ci-shard-timings=utils/ci_test_durations.json", "--ci-lane=ordinary"])
             for i in range(1, 7)]
    cases += [(lane, ["tests", "-p", "utils.pytest_shard", f"--ci-lane={lane}"])
              for lane in ("routing-dispatch", "routing-portable", "routing-regate", "routing-default-layout")]
elif args.stage == "notes-canary":
    cases = [("notes-canary", ["notes/matched_cborg_2026-09-13/test_budgeted_cborg.py::test_reserve_before_generation_and_capture_every_charge"])]
else:
    import yaml
    workflow = yaml.safe_load((ROOT / ".github/workflows/main.yaml").read_text())
    cases = []
    for job in ("offline-canary", "offline-audit", "offline-evaluation"):
        for number, step in enumerate(workflow["jobs"][job]["steps"]):
            command = step.get("run", "")
            if "python -m pytest" not in command:
                continue
            paths = [word for word in shlex.split(command.replace("\\\n", " ")) if word.startswith("notes/")]
            assert paths
            cases.append((f"{job}-{number}", paths))
    assert len(cases) == 4, cases

if args.only:
    assert args.stage == "shards", "--only selects complete CI shard/lane jobs"
    cases = [case for case in cases if case[0] in args.only]
assert args.canary_node is None or args.stage == "canary"

ledger = {"head": head, "stage": args.stage, "runs": []}
destination = storage / f"{args.tag}-{args.stage}.json"
for name, selected in cases:
    base = storage / f"{args.tag}-{name}"
    assert not base.exists(), f"preserve prior gate: {base}"
    command = ["/usr/bin/sandbox-exec", "-D", f"TREE={ROOT}", "-f",
               str(ROOT / "scripts/adhoc/d68_offline_20261030.sb"), args.python,
               "-S", "-P", "-B", str(ROOT / "scripts/adhoc/run_d68_offline_20261030.py"),
               *selected, "-q", "--tb=short", "--basetemp", str(base)]
    print(f"START {name} {head}", flush=True)
    code = run_logged(command, base, cwd=ROOT)
    report = base / "d68-result.json"
    result = json.loads(report.read_text())
    assert report.stat().st_size and result["environment"]["head"] == head
    row = {"name": name, "exit_code": code, "selected": len(result["selected"]),
           "collection_errors": len(result["collection_errors"]), "report": str(report.relative_to(ROOT))}
    ledger["runs"].append(row)
    destination.write_text(json.dumps(ledger, indent=2) + "\n")
    print(f"FINISH {json.dumps(row)}", flush=True)
    if args.stage in {"canary", "notes-canary", "logging-canary", "repair-canary"}:
        assert code == 0 and row["selected"] == 1
    if args.stage == "repairs":
        assert code == 0 and row["selected"] == 12
    if args.stage in {"shards", "notes", "repairs", "d41", "focused"}:
        assert not result["collection_errors"]
        assert len([r for r in result["reports"] if r["when"] == "teardown"]) == row["selected"]
print(f"COMPLETE {destination}", flush=True)
