#!/usr/bin/env python3
# Purpose: summarize retained N2-R3 offline acceptance failure, 2026-10-25. Refs #4354.
# Inputs: finalized acceptance directory; outputs: compact JSON with input pins.
# This reads saved evidence only; it never imports generation code or reruns gates.
import argparse
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def take(value, names):
    return {name: value[name] for name in names if name in value}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    root = args.evidence.resolve(strict=True)
    pins = {}

    def read(relative):
        path = root / relative
        raw = path.read_bytes()
        pins[str(relative)] = {"bytes": len(raw), "sha256": sha(raw)}
        return raw

    def document(relative):
        return json.loads(read(relative))

    case = Path("cases/neutral/test_actual_public_correction_0/native26")
    final = document(case / "native-evidence/final.json")
    replay = document(case / "native-evidence/attribution-replay.json")
    published = document(case / "native-evidence/published.json")
    registration = document(case / "native-attempt/registration.json")
    runtime = document(case / "authority/runtime-execution.json")
    policy = document(case / "authority/receipt-policy.json")
    stderr = read(case / "native-attempt/stderr.txt").decode()
    transcript = [json.loads(line) for line in
                  read(case / "native-attempt/transcript.jsonl").splitlines()]
    provenance = read(case / "data/d4d_concatenated/claudecode_direct_core/"
                      "offline-neutral/SYNTHETIC_provenance.yaml").decode()
    before = document("source-before.json")
    after = document("source-after-neutral.json")
    source_final = document("source-final.json")
    run = document("run.json")
    outcome = document("outcome.json")
    preservation = document("preservation.json")
    manifest = document("upload/case-manifest.json")
    artifact_manifest = document("upload/artifact-manifest.json")
    xml = ET.fromstring(read("neutral.xml"))
    testcases = xml.findall(".//testcase")
    suites = xml.findall("testsuite")
    log = read("neutral.log").decode()
    phase = replay["result"]["phase"]
    draft = replay["result"]["draft"]
    gates = {name: take(value, ("checked", "passed", "reason", "problems", "scope"))
             for name, value in final["gates"].items()}
    calls, results = [], []
    for event in transcript:
        for block in event.get("message", {}).get("content", []):
            if block.get("type") == "tool_use" and block.get("name") == "Bash":
                if " provenance record " in block.get("input", {}).get("command", ""):
                    calls.append(block["id"])
            if block.get("type") == "tool_result":
                results.append(block.get("tool_use_id"))
    top_keys = re.findall(r"^([a-z_]+):", provenance, re.M)
    inline_keys = ("pair_consistency", "report_claims", "grounding", "form", "receipts", "review")
    report = {
        "purpose": "Retained offline software evidence; no rerun or scientific acceptance",
        "evidence_root": str(root),
        "helper": {"path": str(Path(__file__).resolve()),
                   "sha256": sha(Path(__file__).read_bytes())},
        "source": {"head": run["head"], "tree": run["tree"],
                   "before_after_final_equal": before == after == source_final,
                   "tracked_exact": source_final["tracked_exact"]},
        "outcome": outcome,
        "preservation": preservation,
        "archive": {"unchanged_during_archive": manifest["unchanged_during_archive"],
                    "identity": artifact_manifest["cases.tar.gz"]},
        "junit": {"suites": [s.attrib for s in suites],
                  "cases": [{**t.attrib, "failure_count": len(t.findall("failure")),
                             "error_count": len(t.findall("error")),
                             "skipped_count": len(t.findall("skipped"))} for t in testcases]},
        "console_summary": [line for line in log.splitlines()
                            if "failed" in line and "warnings" in line][-1:],
        "final": take(final, ("state", "runtime_gates_passed", "first_stop",
                              "scientific_acceptance", "provider_billing", "shutdown",
                              "evidence_authentication", "runtime_observation")),
        "gates": gates,
        "live_attribution": take(final["gates"]["live_attribution"]["result"],
                                 ("checks", "draft_gate_passed", "recorder_completed",
                                  "problems", "controller_stop")),
        "saved_reconstruction": take(replay["result"], ("checked", "passed", "problems",
                                   "recorder_completed_in_trace", "additional_gate_passed")),
        "phase": phase,
        "draft": draft,
        "recorder": {"call_ids": calls, "settled_call_ids": [c for c in calls if c in results],
                     "provenance_top_level_keys": top_keys,
                     "inline_check_blocks_present": [key for key in inline_keys if key in top_keys]},
        "timeout": {"registered_child_seconds": runtime["deadline_seconds"],
                    "helper_timeout_180_observed": "subprocess.TimeoutExpired:" in stderr
                    and "timed out after 180 seconds" in stderr,
                    "stderr_has_outer_deadline_message": "native attempt deadline elapsed" in stderr},
        "coverage_floor": policy["coverage_floor"],
        "joins": {"registration_sha256_matches": final["registration_sha256"] ==
                  pins[str(case / "native-attempt/registration.json")]["sha256"],
                  "registration_attempt_id": registration["attempt_id"],
                  "published": published,
                  "replay_sha256_matches": final["additional_report"]["sha256"] ==
                  pins[str(case / "native-evidence/attribution-replay.json")]["sha256"]},
        "limits": ["Saved flags are extracted, not independently recomputed acceptance gates.",
                   "Archive identity is copied from the finalized manifest, not rehashed here.",
                   "Pytest elapsed time includes preparation and post-child evidence collection.",
                   "No inference about the exact slow function or provider behavior is made."],
        "input_sha256": pins,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x") as handle:
        json.dump(report, handle, sort_keys=True, indent=2)
        handle.write("\n")
    print(json.dumps({"output": str(args.out), "state": final["state"],
                      "source_unchanged": report["source"]["before_after_final_equal"]}))


if __name__ == "__main__":
    main()
