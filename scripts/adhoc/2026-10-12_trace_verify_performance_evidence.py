#!/usr/bin/env python3
"""Verify principal saved performance summaries from retained raw metadata.

Purpose: preserve a reproducible reporting procedure reconstructed AFTER the
    original analysis; this is not represented as the original JSON generator.
Inputs: --repo with notes/agent_performance_2026-10-12 and Git baseline objects;
    --raw-root containing the original ci/ and implementation/timings/ receipts
    and implementation/profile-run01/{events.json,stdout.log}.
Outputs: NEW --output JSON with computed totals, input hashes, comparisons and
    explicit limits; optional NEW --summary-output compact publication receipt.
    No project imports, tests, profiling, network or writes
    to existing evidence. Read-only Git commands access historical source bytes.
Issues: #5014, #5015, #5016, #5020. Date: 2026-10-12.
"""

import argparse
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
import statistics
import subprocess
import xml.etree.ElementTree as ET
import zipfile


def sha(data):
    return hashlib.sha256(data).hexdigest()


def stats(values):
    return {"n": len(values), "min": min(values), "median": statistics.median(values),
            "max": max(values), "sum": sum(values)}


def elapsed(row):
    return (datetime.fromisoformat(row["updated_at"].replace("Z", "+00:00"))
            - datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))).total_seconds()


class Verification:
    def __init__(self, repo, raw):
        self.repo, self.raw = repo, raw
        self.inputs, self.checks = {}, []

    def read(self, path, label):
        data = path.read_bytes()
        self.inputs[label] = {"bytes": len(data), "sha256": sha(data)}
        return data

    def json(self, path, label):
        return json.loads(self.read(path, label))

    def check(self, label, actual, expected):
        result = {"check": label, "passed": actual == expected}
        if actual != expected:
            result.update(actual=actual, expected=expected)
        self.checks.append(result)

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.repo), *args])

    def audit(self, published):
        # Join original receipts by bytes before recalculating numerical claims.
        for entry in published["source_receipts"]:
            data = self.read(self.raw / entry["name"], "raw/" + entry["name"])
            self.check("original receipt: " + entry["name"],
                       [len(data), sha(data)], [entry["bytes"], entry["sha256"]])
        ci = published["ci"]
        runs = self.json(self.raw / "ci/main-runs-latest50.json", "raw/ci/main-runs-latest50.json")["workflow_runs"]
        docs = self.json(self.raw / "ci/docs-runs-latest20.json", "raw/ci/docs-runs-latest20.json")["workflow_runs"]
        for rows, table, name in ((runs, ci["main_workflow_runs"], "main"),
                                  (docs, ci["docs_workflow_runs"], "docs")):
            projected = [[row[key] for key in table["columns"]] for row in rows]
            self.check(name + " public run roster", projected, table["rows"])
        self.check("main sample count", len(runs), ci["sample"]["main_runs"])
        self.check("docs sample count", len(docs), ci["sample"]["docs_runs"])
        conclusions = dict(Counter(row["conclusion"] for row in runs))
        self.check("main conclusions", conclusions, ci["conclusions"])
        by_event = {}
        for event, expected in ci["successful_feedback_seconds_by_event"].items():
            by_event[event] = stats([elapsed(row) for row in runs
                                    if row["event"] == event and row["conclusion"] == "success"])
            self.check("feedback " + event, by_event[event], expected)
        docs_stats = stats([elapsed(row) for row in docs])
        self.check("docs feedback", docs_stats, ci["docs_feedback_seconds"])
        for record in ci["critical_test_log_excerpts"]:
            data = self.read(self.raw / "ci" / record["source_receipt_name"],
                             "raw/ci/" + record["source_receipt_name"])
            self.check("critical log bytes " + record["name"],
                       [len(data), sha(data)], [record["bytes"], record["sha256"]])
            lines = data.decode().splitlines()
            for excerpt in record["duration_lines"]:
                self.check("critical duration excerpt " + record["name"],
                           lines[excerpt["line"] - 1], excerpt["text"])
        return {"main_runs": len(runs), "docs_runs": len(docs),
                "conclusions": conclusions, "successful_feedback_seconds_by_event": by_event,
                "docs_feedback_seconds": docs_stats,
                "original_receipts_verified": len(published["source_receipts"])}

    def timings(self, published, weights):
        directory = self.raw / "implementation/timings"
        run = self.json(directory / "run-38158491197.json", "raw/timings/run.json")
        for key, source_key in (("run_id", "id"), ("commit", "head_sha"),
                                ("run_attempt", "run_attempt"), ("event", "event"),
                                ("branch", "head_branch"), ("conclusion", "conclusion")):
            self.check("timing run " + key, run[source_key], published[key])
        github = self.json(directory / "artifacts-38158491197.json", "raw/timings/artifacts.json")
        inventory = self.json(directory / "artifact-audit.json", "raw/timings/artifact-audit.json")
        api_by_id = {entry["id"]: entry for entry in github["artifacts"]}
        self.check("artifact count", len(inventory["artifacts"]), github["total_count"])
        self.check("artifact identity roster", set(api_by_id), {entry["id"] for entry in inventory["artifacts"]})
        xml_count = 0
        for entry in inventory["artifacts"]:
            archive = self.read(directory / "archives" / (str(entry["id"]) + ".zip"),
                                "raw/timings/archives/" + str(entry["id"]) + ".zip")
            actual = api_by_id[entry["id"]]
            self.check("archive digest " + entry["name"], "sha256:" + sha(archive), actual["digest"])
            self.check("archive saved pin " + entry["name"], sha(archive), entry["archive_sha256"])
            self.check("archive size " + entry["name"], len(archive), entry["archive_size"])
            with zipfile.ZipFile(directory / "archives" / (str(entry["id"]) + ".zip")) as zipped:
                for xml in entry["xml"]:
                    data = self.read(directory / xml["path"], "raw/timings/" + xml["path"])
                    self.check("XML bytes " + xml["path"], [len(data), sha(data)], [xml["bytes"], xml["sha256"]])
                    self.check("archive member " + xml["path"], sha(zipped.read(Path(xml["path"]).name)), sha(data))
                    xml_count += 1

        commit = published["commit"]
        files = self.git("ls-tree", "-r", "--name-only", commit, "--", "tests").decode().splitlines()
        modules = {name[:-3].replace("/", "."): name for name in files if name.endswith(".py")}
        file_seconds, identities = defaultdict(Decimal), defaultdict(list)
        counts = Counter()
        all_cases, artifact_pins = [], []
        for entry in published["core_artifacts"]:
            for xml in entry["xml"]:
                path = directory / xml["path"]
                raw = path.read_bytes()
                artifact_pins.append({"path": str(Path(xml["path"]).relative_to("artifacts")), "sha256": sha(raw)})
                for index, case in enumerate(ET.fromstring(raw).iter("testcase")):
                    classname, name = case.attrib["classname"], case.attrib["name"]
                    candidates = [key for key in modules if classname == key or classname.startswith(key + ".")]
                    if not candidates:
                        raise ValueError("unmapped JUnit class: " + classname)
                    mapped = modules[max(candidates, key=len)]
                    duration = Decimal(case.attrib["time"])
                    if not duration.is_finite() or duration < 0:
                        raise ValueError("invalid case time")
                    row = {"file": mapped, "classname": classname, "name": name,
                           "seconds": str(duration), "skipped": case.find("skipped") is not None,
                           "shard": entry["name"], "case_element_index": index}
                    all_cases.append(row)
                    identities[(classname, name)].append(row)
                    file_seconds[mapped] += duration
                    counts["case_records"] += 1
                    for tag, label in (("skipped", "skipped"), ("failure", "failures"), ("error", "errors")):
                        counts[label] += case.find(tag) is not None
        calculated = {name: float(max(value, Decimal("0.001"))) for name, value in sorted(file_seconds.items())}
        self.check("every file weight", calculated, weights["file_seconds"])
        self.check("weight artifact pins", artifact_pins, weights["source"]["artifacts"])
        self.check("weight testcase count", len(all_cases), weights["source"]["test_cases"])
        old = json.loads(self.git("show", commit + ":utils/ci_test_durations.json"))["file_seconds"]
        core = dict(counts)
        core.update(unique_classname_name_pairs=len(identities), mapped_files=len(file_seconds),
                    duplicate_id_groups=sum(len(rows) > 1 for rows in identities.values()),
                    cross_artifact_duplicate_id_groups=sum(len({row["shard"] for row in rows}) > 1
                                                           for rows in identities.values()),
                    unmapped_cases=0, total_case_seconds=str(sum(file_seconds.values(), Decimal())),
                    new_weighted_files=len(set(file_seconds) - set(old)),
                    old_weighted_files_missing_from_current=sorted(set(old) - set(file_seconds)))
        for key, value in core.items():
            self.check("core " + key, value, published["core"][key])
        duplicates = [{"classname": key[0], "name": key[1], "occurrences": rows}
                      for key, rows in identities.items() if len(rows) > 1]
        self.check("duplicate occurrence detail", duplicates, published["duplicate_occurrences"])
        self.check("largest case", max(all_cases, key=lambda row: Decimal(row["seconds"])), published["largest_case"])
        largest = [{"file": name, "seconds": str(seconds), "old_seconds": old.get(name)}
                   for name, seconds in sorted(file_seconds.items(), key=lambda item: (-item[1], item[0]))
                   [:len(published["largest_files"])]]
        self.check("largest files", largest, published["largest_files"])
        for size, expected in published["validation"]["estimated_case_seconds_per_shard"].items():
            loads, nfiles = [0.0] * int(size), [0] * int(size)
            for path in sorted(calculated, key=lambda path: (-calculated[path], path)):
                index = min(range(int(size)), key=lambda i: (loads[i], nfiles[i], i))
                loads[index] += calculated[path]
                nfiles[index] += 1
            self.check("scheduling estimate " + size, [round(n, 3) for n in loads], [round(n, 3) for n in expected])
        return {"archives": len(inventory["artifacts"]), "XML_files": xml_count, "core": core,
                "all_file_weights_match": calculated == weights["file_seconds"]}

    def profile(self, published):
        directory = self.raw / "implementation/profile-run01"
        data = self.read(directory / "events.json", "raw/profile-run01/events.json")
        profile = json.loads(data)
        self.check("profile raw pin", sha(data), published["raw_profile_sha256"])
        for key, raw_key in (("node", "nodeid"), ("python", "python"), ("phases", "phases"),
                             ("pytest_exit", "session_exit"), ("bindings_restored", "restored"),
                             ("instrumentation_errors", "errors")):
            self.check("profile " + key, profile[raw_key], published[key])
        source_pins = [{**entry, "path": str(Path(entry["path"]).relative_to(profile["root"]))}
                       for entry in profile["sources"]]
        self.check("profile source pins", source_pins, published["source_pins"])
        for entry in source_pins:
            original = self.git("show", published["commit"] + ":" + entry["path"])
            self.check("baseline source " + entry["module"], sha(original), entry["sha256"])
        grouped = defaultdict(list)
        for event in profile["events"]:
            grouped[event["function"]].append(event)
        totals = {}
        for name, expected in published["functions"].items():
            rows = grouped[name]
            totals[name] = {"calls": len(rows)}
            for label, field in (("inclusive_wall_seconds", "wall_ns"),
                                 ("exclusive_wall_seconds", "exclusive_wall_ns"),
                                 ("thread_cpu_seconds", "thread_ns")):
                totals[name][label] = round(sum(row[field] for row in rows) / 1e9, 6)
            self.check("profile totals " + name, totals[name], expected)
        stdout = self.read(directory / "stdout.log", "raw/profile-run01/stdout.log").decode()
        match = re.search(r"1 passed[^\n]* in ([0-9.]+)s", stdout)
        self.check("pytest displayed wall time", float(match.group(1)) if match else None,
                   published["pytest_wall_seconds"])
        return {"functions": totals, "phases": profile["phases"],
                "measured_API_execute_entries": len(grouped["api_runner.execute"])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--raw-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--summary-output", type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite a prior verification")
    if args.summary_output is not None and (args.summary_output.exists()
                                            or args.summary_output.resolve() == args.output.resolve()):
        raise SystemExit("summary must be a distinct new file")
    verifier = Verification(args.repo, args.raw_root)
    notes = args.repo / "notes/agent_performance_2026-10-12"
    audit = verifier.json(notes / "evidence.json", "published/evidence.json")
    timing = verifier.json(notes / "timing-refresh.json", "published/timing-refresh.json")
    baseline = verifier.json(notes / "replay-baseline.json", "published/replay-baseline.json")
    weights = verifier.json(args.repo / "utils/ci_test_durations.json", "published/ci_test_durations.json")
    results = {"audit": verifier.audit(audit), "timings": verifier.timings(timing, weights),
               "baseline": verifier.profile(baseline)}
    verifier.check("weight output digest", verifier.inputs["published/ci_test_durations.json"]["sha256"],
                   timing["validation"]["output_sha256"])
    output = {
        "kind": "retrospective_metadata_verification_not_original_generator",
        "passed": all(check["passed"] for check in verifier.checks),
        "computed": results, "checks": verifier.checks, "inputs": verifier.inputs,
        "helper_sha256": sha(Path(__file__).read_bytes()),
        "limits": [
            "Reconstructed after analysis; verifies retained bytes and principal arithmetic, not an original execution receipt.",
            "No project imports, tests, profiler, collection, provider or network calls.",
            "Archive hashes join saved GitHub metadata; no new remote freshness claim.",
            "JUnit aggregate and profile inclusive times overlap and are not wall-time speedup measurements.",
            "Historical host/workspace observations are hash-bound only; current state and narrative recommendations are not remeasured.",
            "The profile verifies 19 execute entries; the 21 attempted-operation explanation remains source-derived, not inferred from missing events.",
            "Existing focused-test pass claims and final CI acceptance are outside this arithmetic verification.",
        ],
    }
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(output, stream, indent=2, default=lambda value: sorted(value) if isinstance(value, set) else str(value))
        stream.write("\n")
    if args.summary_output is not None:
        compact = {
            "kind": output["kind"], "passed": output["passed"],
            "checks": len(verifier.checks),
            "failed_checks": [row["check"] for row in verifier.checks if not row["passed"]],
            "helper": {"path": "scripts/adhoc/" + Path(__file__).name,
                       "sha256": output["helper_sha256"]},
            "detailed_verification_sha256": sha(args.output.read_bytes()),
            "published_inputs": {name: pin for name, pin in verifier.inputs.items()
                                 if name.startswith("published/")},
            "verified_totals": {
                "main_run_sample": results["audit"]["main_runs"],
                "docs_run_sample": results["audit"]["docs_runs"],
                "successful_PR_feedback_median_seconds": results["audit"]["successful_feedback_seconds_by_event"]["pull_request"]["median"],
                "artifact_archives": results["timings"]["archives"],
                "artifact_XML_files": results["timings"]["XML_files"],
                "core_timing_records": results["timings"]["core"]["case_records"],
                "core_unique_labels": results["timings"]["core"]["unique_classname_name_pairs"],
                "core_weighted_files": results["timings"]["core"]["mapped_files"],
                "all_file_weights_match": results["timings"]["all_file_weights_match"],
                "profile_functions": len(results["baseline"]["functions"]),
                "profile_API_execute_entries": results["baseline"]["measured_API_execute_entries"],
            },
            "limits": output["limits"],
        }
        with args.summary_output.open("x", encoding="utf-8") as stream:
            json.dump(compact, stream, indent=2)
            stream.write("\n")
    print(json.dumps({"passed": output["passed"], "checks": len(verifier.checks),
                      "failed": [row["check"] for row in verifier.checks if not row["passed"]]}))
    raise SystemExit(0 if output["passed"] else 1)


if __name__ == "__main__":
    main()
