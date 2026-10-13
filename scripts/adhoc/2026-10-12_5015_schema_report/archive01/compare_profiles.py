#!/usr/bin/env python3
"""Verify completed pipeline profiles and emit portable #5015 evidence.

Purpose: compare baseline/event-replay attribution plus the four-call ABBA run.
Inputs: completed profile directories, ABBA summary, exact owned checkout.
Output: a new --output portable JSON report; never overwrites prior evidence.
Issue: bridge2ai/data-sheets-schema#5015; no PR yet. Date: 2026-10-12.
Stdlib metadata/AST only. No project imports, test execution or benchmarks.
Do not execute until root confirms profile03 is terminal.
"""
import argparse
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET


NODE = "tests/test_shared_generation_runtime.py::test_real_complete_api_pipeline_and_completed_recheck"
TESTS = ("tests/test_shared_generation_runtime.py", "tests/test_shared_generation_completed_replay.py")
CHANGED = {"src/data_sheets_schema/audit_omissions.py", "src/data_sheets_schema/typed_audit.py"}
MUTATIONS = ["bundle", "context", "receipt", "rehashed_packet", "rehashed_assembly", "usage", "lost_progress"]
TIMES = ("wall_ns", "thread_ns", "exclusive_wall_ns", "exclusive_thread_ns")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def evidence(path, label):
    raw = path.read_bytes()
    return {"label": label, "filename": path.name, "bytes": len(raw), "sha256": sha(raw)}


def relative(path, root):
    value = Path(path)
    if value.is_absolute():
        value = value.relative_to(root)
    require(".." not in value.parts, "noncanonical source path")
    return value.as_posix()


def pin_map(document, root):
    if isinstance(document, dict) and all(isinstance(value, str) for value in document.values()):
        rows = document.items()
    else:
        rows = ((row["path"], row["sha256"]) for row in document["files"])
    result = {}
    for path, digest in rows:
        name = relative(path, root)
        require(name not in result, "duplicate source pin")
        require(len(digest) == 64 and all(c in "0123456789abcdef" for c in digest), "invalid source digest")
        result[name] = digest
    return result


def profile(directory, root, label):
    events_path, xml_path = directory / "events.json", directory / "junit.xml"
    pins_path = directory / "source-pins-before.json"
    document = json.loads(events_path.read_text())
    require(document["kind"] == "d4d_single_node_passthrough_profile_v1", label + " wrong profiler kind")
    require(document["nodeid"] == NODE and Path(document["root"]).resolve() == root, label + " wrong target/root")
    require(document["session_exit"] == 0 and document["restored"] is True and document["errors"] == [],
            label + " incomplete, failed, unrestored or observer errors")
    phases = document["phases"]
    require([(row["when"], row["outcome"]) for row in phases] ==
            [(name, "passed") for name in ("setup", "call", "teardown")], label + " wrong phase roster")
    xml = ET.fromstring(xml_path.read_bytes())
    cases = list(xml.iter("testcase"))
    require(len(cases) == 1 and cases[0].get("name") == NODE.split("::")[1], label + " wrong JUnit case")
    require(not any(list(xml.iter(tag)) for tag in ("failure", "error", "skipped")), label + " JUnit did not pass")
    sources = pin_map(json.loads(pins_path.read_text()), root)
    for row in document["sources"]:
        name = relative(row["path"], root)
        require(name not in sources or sources[name] == row["sha256"], label + " recorded source conflict")
        sources[name] = row["sha256"]
    require(all(name in sources for name in TESTS), label + " missing test pins")
    rows = sorted(document["events"], key=lambda row: row["id"])
    require([row["id"] for row in rows] == list(range(1, len(rows) + 1)), label + " incomplete/duplicate event IDs")
    ids = {row["id"] for row in rows}
    require(len({row["thread"] for row in rows}) == 1, label + " nonserial event stream")
    for row in rows:
        require(row["parent"] is None or row["parent"] in ids and row["parent"] < row["id"], label + " invalid parent")
        require(all(isinstance(row[key], int) and row[key] >= 0 for key in TIMES), label + " invalid timing")
    signature = [[row["id"], row["parent"], row["function"], row["exception"], row.get("caller")] for row in rows]
    functions = {}
    for row in rows:
        data = functions.setdefault(row["function"], {"calls": 0, "outcomes": Counter(), **{key: 0 for key in TIMES}})
        data["calls"] += 1
        data["outcomes"][row["exception"] or "returned"] += 1
        for key in TIMES:
            data[key] += row[key]
    for data in functions.values():
        data["outcomes"] = dict(sorted(data["outcomes"].items()))
        for key in TIMES:
            data[key.replace("_ns", "_seconds")] = data.pop(key) / 1e9
    execute = [row for row in rows if row["function"] == "api_runner.execute"]
    require(len(execute) == 19 and sum(row["exception"] is None for row in execute) == 6,
            label + " expected19 execute attempts/6 successful returns")
    observed_mutations = [row["caller"]["mutation"] for row in execute if "mutation" in row.get("caller", {})]
    require(observed_mutations == MUTATIONS[2:], label + " changed mutation execute sequence")
    require(functions["shared_generation.capture"]["calls"] == 2341 and
            functions["shared_generation.assert_current"]["calls"] == 2032, label + " changed fresh-check counts")
    receipt = [evidence(path, label + ":" + key) for key, path in
               (("events", events_path), ("junit", xml_path), ("source-before", pins_path))]
    summary = {"phases": phases, "junit_seconds": float(cases[0].get("time")),
               "source_pins": sources, "functions": functions, "events": len(rows),
               "event_signature_sha256": sha(json.dumps(signature, sort_keys=True).encode()),
               "session_exit": document["session_exit"], "restored": document["restored"], "errors": document["errors"]}
    return document, summary, signature, execute, receipt


def change(before, after):
    return {"baseline": before, "candidate": after, "difference": after - before,
            "percent_change": None if before == 0 else 100 * (after - before) / before}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--abba", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--candidate-after", type=Path)
    parser.add_argument("--baseline-after", type=Path)
    parser.add_argument("--terminal-confirmed", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(args.terminal_confirmed, "root must explicitly confirm both runtime sessions terminal")
    require(not args.output.exists(), "output exists; preserve old evidence")
    root = args.root.resolve()
    old_doc, old, old_sig, old_execute, receipts = profile(args.baseline, root, "baseline")
    new_doc, new, new_sig, new_execute, more = profile(args.candidate, root, "candidate")
    receipts += more
    require(old_doc["python"] == new_doc["python"] and old_doc["executable"] == new_doc["executable"], "interpreter differs")
    require(old_sig == new_sig, "instrumented caller/function/outcome/parent order differs")
    require(set(old["source_pins"]) == set(new["source_pins"]), "source pin roster differs")
    changed = {name for name in old["source_pins"] if old["source_pins"][name] != new["source_pins"][name]}
    require(changed == CHANGED, "unexpected source delta")
    require(all(sha((root / name).read_bytes()) == digest for name, digest in new["source_pins"].items()),
            "current candidate files differ from recorded inputs")
    after_evidence = {}
    for label, path, run in (("baseline", args.baseline_after, old), ("candidate", args.candidate_after, new)):
        after_evidence[label] = None
        if path is not None:
            after = pin_map(json.loads(path.read_text()), root)
            require(after and all(run["source_pins"].get(name) == digest for name, digest in after.items()),
                    label + " after pins differ")
            require(all(name in after for name in TESTS), label + " after pins omit tests")
            after_evidence[label] = sorted(after)
            receipts.append(evidence(path, label + ":source-after"))
    runtime_test = root / TESTS[0]
    tree = ast.parse(runtime_test.read_text())
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and
                    node.name == "assert_completed_mutations_refuse_without_calls")
    loops = [node for node in ast.walk(function) if isinstance(node, ast.For) and
             isinstance(node.target, ast.Name) and node.target.id == "mutation"]
    require(len(loops) == 1 and list(ast.literal_eval(loops[0].iter)) == MUTATIONS, "seven mutation controls changed")
    require(all(old["source_pins"][name] == new["source_pins"][name] for name in TESTS), "test source changed")
    abba = json.loads(args.abba.read_text())
    require(abba["kind"] == "schema_admission_abba_v1" and abba["passed"] is True and abba["error"] is None and
            abba["restored"] is True and abba["source_preserved"] is True, "ABBA failed")
    require(abba["source_before"] == abba["source_after"], "ABBA source drift")
    require(abba["python"] == new_doc["python"] and abba["executable"] == new_doc["executable"], "ABBA interpreter differs")
    calls = abba["calls"]
    require([(row["position"], row["variant"]) for row in calls] == list(enumerate(("old", "new", "new", "old"), 1)), "ABBA order differs")
    require(all(row["catalog_equal"] is True for row in calls) and
            len({(row["catalog_bytes"], row["catalog_sha256"]) for row in calls}) == 1, "ABBA catalog mismatch")
    for row in abba["source_before"]:
        name = relative(row["path"], root)
        require(sha((root / name).read_bytes()) == row["sha256"], "ABBA/current source mismatch")
        if name in new["source_pins"]:
            require(new["source_pins"][name] == row["sha256"], "ABBA/profile source mismatch")
    receipts.append(evidence(args.abba, "abba:summary"))
    old_call = old["phases"][1]["duration"]
    new_call = new["phases"][1]["duration"]
    comparison = [{"function": name, "baseline": old["functions"][name], "candidate": new["functions"][name],
                   "wall_change": change(old["functions"][name]["wall_seconds"], new["functions"][name]["wall_seconds"]),
                   "thread_change": change(old["functions"][name]["thread_seconds"], new["functions"][name]["thread_seconds"])}
                  for name in sorted(old["functions"])]
    result = {"kind": "schema_event_replay_performance_comparison_v1", "issue": 5015, "date": "2026-10-12",
              "verified": True, "nodeid": NODE, "evidence": receipts,
              "helper": evidence(Path(__file__), "report-helper"), "python": new_doc["python"],
              "baseline": old, "candidate": new, "call_phase_wall_change": change(old_call, new_call),
              "function_comparison": comparison,
              "execute_sequence": [{"caller": before.get("caller"), "exception": before["exception"],
                                    "wall_change": change(before["wall_ns"] / 1e9, after["wall_ns"] / 1e9)}
                                   for before, after in zip(old_execute, new_execute)],
              "preservation": {"changed_source_paths": sorted(changed), "test_files_byte_identical": True,
                               "event_order_and_outcomes_identical": True, "candidate_current_files_match": True,
                               "provided_after_pin_coverage": after_evidence},
              "mutation_controls": {"literal_order": MUTATIONS, "unchanged_test_passed_both": True,
                                    "observed_execute_labels": MUTATIONS[2:], "not_entering_execute": MUTATIONS[:2],
                                    "interpretation": "Seven controls remain. Bundle/context refuse during RunSpec reconstruction before api.execute; five controls reach the instrumented execute wrapper. Passing unchanged test plus its saved byte pins supplies control evidence; not seven execute events."},
              "abba": {"calls": calls, "packages": abba["packages"], "platform": abba["platform"],
                       "load_before": abba["load_before"], "load_after": abba["load_after"],
                       "cpu_count": abba["cpu_count"], "source_preserved": True,
                       "wall_mean_change": change(sum(row["wall_seconds"] for row in calls if row["variant"] == "old") / 2,
                                                  sum(row["wall_seconds"] for row in calls if row["variant"] == "new") / 2)},
              "limitations": ["Two profiled pipeline observations and four unprofiled admissions; no statistical-significance/general-throughput claim.",
                               "Wall times are host/load-sensitive. Thread CPU excludes subprocess CPU; cumulative instrumented times overlap and must not be summed.",
                               "Pipeline phases measure pytest timing, not outer /usr/bin/time; the historical time -l sandbox error is not the test outcome.",
                               "Profiler hashes source at installation only. Independent after receipts are reported when supplied; later current-file equality is not a contemporaneous baseline after receipt.",
                               "No provider, scientific quality, generation completeness or schema-content change is inferred from timing."]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(json.dumps({"output": args.output.name, "sha256": sha(args.output.read_bytes()), "verified": True}))


if __name__ == "__main__":
    main()
