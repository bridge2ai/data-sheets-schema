"""Replay profile availability and field-presence reports without changing sources.

Run the same script separately against baseline and candidate checkouts, using
fresh external output directories. Optional --compare reads a baseline replay
and checks the candidate transition; it never rewrites either source checkout.
There are no scientific labels, schema-validation calls, or provider requests.
"""

import argparse
import copy
import dataclasses
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import traceback
import zipfile

sys.dont_write_bytecode = True

FORMAT = "d4d_profile_availability_replay_v1"
LEVELS = ("minimal", "basic", "complete")
ORDERS = ("original", "reversed")
CODE_PATHS = ("src/validation/unified_validator.py", "src/data_sheets_schema/rocrate_sources.py")
INPUT_PATHS = {
    "CHORUS": "data/ro-crate_packages/CHORUS/raw/ro-crate-metadata.json",
    "VOICE": "data/ro-crate_packages/VOICE/raw/ro-crate-metadata.json",
    "CM4AI_reduced": "data/ro-crate_packages/CM4AI/processed/CM4AI_crate_metadata_reduced.json",
    "VOICE_provenance": "data/ro-crate_packages/VOICE/raw/ro-crate-prov-graph.json",
}
ARCHIVE = "data/ro-crate_packages/CM4AI/raw/cm4ai_release_metadata.zip"
MEMBER = "cm4ai_release_metadata/ro-crate-metadata.json"


def encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
                      default=lambda item: item.value).encode("utf-8")


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False,
                               default=lambda item: item.value) + "\n", encoding="utf-8")


def hashes(repo, paths):
    return {path: digest((repo / path).read_bytes()) for path in paths}


def unavailable(report):
    metadata = report.get("metadata", {})
    return (report.get("passed") is False and report.get("coverage_percentage") is None
            and report.get("missing_fields") is None and metadata.get("status") == "unavailable"
            and metadata.get("reason") == "required_fields_not_defined"
            and metadata.get("required_count") is None and metadata.get("found_count") is None)


def compare(baseline_path, candidate):
    raw = (baseline_path / "summary.json").read_bytes()
    baseline = json.loads(raw)
    if baseline.get("format") != FORMAT or set(baseline.get("inputs", {})) != set(candidate["inputs"]):
        raise ValueError("--compare must name the same complete replay roster under this replay format")
    before, after = baseline["inputs"], candidate["inputs"]
    checks = {
        "same_original_input_bytes": all(before[name]["input_sha256"] == after[name]["input_sha256"]
                                         for name in after),
        "same_reversed_input_bytes": all(before[name]["reversed_input_sha256"] == after[name]["reversed_input_sha256"]
                                         for name in after),
        "minimal_basic_reports_unchanged": all(
            encoded(before[name]["levels"][level][order]) == encoded(after[name]["levels"][level][order])
            for name in after for level in ("minimal", "basic") for order in ORDERS),
        "complete_unavailable_on_valid_roots": all(
            unavailable(after[name]["levels"]["complete"][order])
            for name in after if name != "descriptor_unresolved" for order in ORDERS),
        "unresolved_root_errors_preserved": all(
            encoded(before["descriptor_unresolved"]["levels"][level][order]) ==
            encoded(after["descriptor_unresolved"]["levels"][level][order])
            for level in LEVELS for order in ORDERS),
        "all_candidate_reports_invariant_under_graph_reversal": all(
            after[name]["levels"][level]["reversal_equal"] for name in after for level in LEVELS),
        "source_files_unchanged_in_both_runs": baseline["source_files_unchanged"] and candidate["source_files_unchanged"],
        "implementations_unchanged_during_both_runs": baseline["code_unchanged"] and candidate["code_unchanged"],
        "no_exceptions": baseline["exception_count"] == candidate["exception_count"] == 0,
    }
    transitions = {}
    for name in after:
        transitions[name] = {}
        for order in ORDERS:
            transitions[name][order] = {
                "baseline": before[name]["levels"]["complete"][order],
                "candidate": after[name]["levels"]["complete"][order],
            }
    return {"baseline_label": baseline["label"], "baseline_summary_sha256": digest(raw),
            "candidate_label": candidate["label"], "checks": checks,
            "passed": all(checks.values()), "complete_transitions": transitions,
            "interpretation": "Removal of undefined numeric coverage; no source-coverage or scientific-completeness gain."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--label", required=True, help="fresh label for this baseline or candidate replay")
    parser.add_argument("--compare", type=Path, help="existing baseline replay directory; check the candidate transition")
    args = parser.parse_args()
    repo, out = args.repo.resolve(), args.output.resolve()
    if out == repo or repo in out.parents:
        parser.error("--output must be outside the inspected repository")
    if not args.label.strip() or args.label != args.label.strip():
        parser.error("--label must be nonblank trimmed text")
    out.mkdir(parents=True, exist_ok=False)

    # Read the source inputs once; inspect the captured archive bytes in memory.
    source_bytes = {path: (repo / path).read_bytes() for path in (*INPUT_PATHS.values(), ARCHIVE)}
    sources_before = {path: digest(raw) for path, raw in source_bytes.items()}
    code_before = hashes(repo, CODE_PATHS)
    inputs = {name: (source_bytes[path], {"path": path}) for name, path in INPUT_PATHS.items()}
    with zipfile.ZipFile(io.BytesIO(source_bytes[ARCHIVE])) as archive:
        inputs["CM4AI_original"] = (archive.read(MEMBER), {
            "path": ARCHIVE, "archive_sha256": sources_before[ARCHIVE], "member": MEMBER})

    priority = {"@graph": [
        {"@id": "ro-crate-metadata.json", "@type": "CreativeWork", "about": {"@id": "#root"}},
        {"@id": "./", "@type": "Dataset", "name": "Rich member", "description": "Member-only description",
         "datePublished": "2026-01-01", "license": "https://creativecommons.org/licenses/by/4.0/",
         "keywords": ["member"], "author": "Member author", "identifier": "member-id"},
        {"@id": "#root", "@type": "Dataset", "name": "Sparse authoritative root"},
    ]}
    unresolved = copy.deepcopy(priority)
    unresolved["@graph"][0]["about"]["@id"] = "#missing"
    for name, crate in (("descriptor_priority", priority), ("descriptor_unresolved", unresolved)):
        inputs[name] = (encoded(crate), {"synthetic": True})

    sys.path.insert(0, str(repo / "src"))
    spec = importlib.util.spec_from_file_location("d4d_profile_availability_replay", repo / CODE_PATHS[0])
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses needs the defining module registered.
    spec.loader.exec_module(module)
    from data_sheets_schema import rocrate_sources
    if Path(rocrate_sources.__file__).resolve() != (repo / CODE_PATHS[1]).resolve():
        raise RuntimeError("root selector was imported from a different checkout")
    validator = module.UnifiedValidator()
    summary = {
        "format": FORMAT, "label": args.label,
        "scope": "Profile availability and existing field presence only; no scientific scoring or source-coverage claim",
        "replay_sha256": digest(Path(__file__).read_bytes()),
        "requirements": module.LEVEL_REQUIREMENTS,
        "requirements_sha256": digest(encoded(module.LEVEL_REQUIREMENTS)),
        "source_sha256_before": sources_before, "code_sha256_before": code_before,
        "inputs": {}, "exception_count": 0,
    }
    input_dir = out / "inputs"
    input_dir.mkdir()
    for name, (raw, binding) in inputs.items():
        original = input_dir / f"{name}.json"
        original.write_bytes(raw)
        crate = json.loads(raw)
        reversed_crate = copy.deepcopy(crate)
        graph = reversed_crate.get("@graph")
        if isinstance(graph, list):
            graph.reverse()
        reverse = input_dir / f"{name}_reversed.json"
        write_json(reverse, reversed_crate)
        entry = {**binding, "input_sha256": digest(raw), "reversed_input_sha256": digest(reverse.read_bytes()),
                 "graph_shape": "array" if isinstance(graph, list) else "node object", "levels": {}}
        for level in LEVELS:
            reports = {}
            for order, path in (("original", original), ("reversed", reverse)):
                try:
                    report = validator.validate_profile(path, level=level)
                    result = dataclasses.asdict(report)
                    (out / f"{name}_{level}_{order}.txt").write_text(str(report) + "\n", encoding="utf-8")
                except Exception as exc:
                    summary["exception_count"] += 1
                    result = {"exception": {"type": type(exc).__name__, "message": str(exc)}}
                    (out / f"{name}_{level}_{order}.traceback.txt").write_text(traceback.format_exc(), encoding="utf-8")
                write_json(out / f"{name}_{level}_{order}.json", result)
                reports[order] = result
            entry["levels"][level] = {
                **reports, "original_report_sha256": digest(encoded(reports["original"])),
                "reversed_report_sha256": digest(encoded(reports["reversed"])),
                "reversal_equal": encoded(reports["original"]) == encoded(reports["reversed"]),
                "both_unavailable": all(unavailable(report) for report in reports.values()),
            }
        summary["inputs"][name] = entry
    summary["source_sha256_after"] = hashes(repo, sources_before)
    summary["code_sha256_after"] = hashes(repo, CODE_PATHS)
    summary["source_files_unchanged"] = summary["source_sha256_after"] == sources_before
    summary["code_unchanged"] = summary["code_sha256_after"] == code_before
    summary["profile_checks"] = len(inputs) * len(LEVELS) * len(ORDERS)
    write_json(out / "summary.json", summary)
    successful = summary["source_files_unchanged"] and summary["code_unchanged"] and not summary["exception_count"]
    if args.compare is not None:
        comparison = compare(args.compare.resolve(), summary)
        write_json(out / "comparison.json", comparison)
        successful = successful and comparison["passed"]
    print(json.dumps({"label": args.label, "output": str(out), "inputs": len(inputs),
                      "profile_checks": summary["profile_checks"], "checks_passed": successful}))
    return 0 if successful else 1


if __name__ == "__main__":
    raise SystemExit(main())
