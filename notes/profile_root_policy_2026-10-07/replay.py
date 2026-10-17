"""Replay #4595 profile presence checks, preserving baseline failures.

Profile counts here are field-presence diagnostics, not LinkML validation,
semantic fidelity, or source coverage. Run each checkout into a fresh external
directory; no source bundle or historical record is modified.
"""

import argparse
import copy
import dataclasses
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import traceback
import zipfile

sys.dont_write_bytecode = True


def encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), default=lambda item: item.value).encode("utf-8")


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False,
                               default=lambda item: item.value) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    repo, out = args.repo.resolve(), args.output.resolve()
    if out == repo or repo in out.parents:
        parser.error("--output must be outside the inspected repository")
    out.mkdir(parents=True, exist_ok=False)
    sys.path.insert(0, str(repo / "src"))
    code_path = repo / "src/validation/unified_validator.py"
    spec = importlib.util.spec_from_file_location("d4d_profile_root_replay", code_path)
    module = importlib.util.module_from_spec(spec)
    # Dataclass annotation handling requires the module's registered namespace.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    validator = module.UnifiedValidator()

    paths = {
        "CHORUS": "data/ro-crate_packages/CHORUS/raw/ro-crate-metadata.json",
        "VOICE": "data/ro-crate_packages/VOICE/raw/ro-crate-metadata.json",
        "CM4AI_reduced": "data/ro-crate_packages/CM4AI/processed/CM4AI_crate_metadata_reduced.json",
        "VOICE_provenance": "data/ro-crate_packages/VOICE/raw/ro-crate-prov-graph.json",
    }
    inputs = {name: ((repo / path).read_bytes(), {"path": path})
              for name, path in paths.items()}
    archive = repo / "data/ro-crate_packages/CM4AI/raw/cm4ai_release_metadata.zip"
    member = "cm4ai_release_metadata/ro-crate-metadata.json"
    with zipfile.ZipFile(archive) as bundle:
        inputs["CM4AI_original"] = (
            bundle.read(member), {"path": str(archive.relative_to(repo)),
                                  "archive_sha256": digest(archive.read_bytes()),
                                  "member": member})

    priority = {"@graph": [
        {"@id": "ro-crate-metadata.json", "@type": "CreativeWork",
         "about": {"@id": "#root"}},
        {"@id": "./", "@type": "Dataset", "name": "Rich member",
         "description": "Member-only description", "datePublished": "2026-01-01",
         "license": "https://creativecommons.org/licenses/by/4.0/",
         "keywords": ["member"], "author": "Member author", "identifier": "member-id"},
        {"@id": "#root", "@type": "Dataset", "name": "Sparse authoritative root"},
    ]}
    unresolved = copy.deepcopy(priority)
    unresolved["@graph"][0]["about"]["@id"] = "#missing"
    for name, crate in (("descriptor_priority", priority),
                        ("descriptor_unresolved", unresolved)):
        inputs[name] = (encoded(crate), {"synthetic": True})

    summary = {
        "scope": "Profile field presence only; no LinkML, fidelity, or source-coverage claim",
        "replay_sha256": digest(Path(__file__).read_bytes()),
        "requirements": module.LEVEL_REQUIREMENTS,
        "requirements_sha256": digest(encoded(module.LEVEL_REQUIREMENTS)),
        "code_sha256": {
            "src/validation/unified_validator.py": digest(code_path.read_bytes()),
            "src/data_sheets_schema/rocrate_sources.py": digest(
                (repo / "src/data_sheets_schema/rocrate_sources.py").read_bytes()),
        },
        "inputs": {},
    }
    input_dir = out / "inputs"
    input_dir.mkdir()
    for name, (raw, binding) in inputs.items():
        original = input_dir / (name + ".json")
        original.write_bytes(raw)
        crate = json.loads(raw)
        reversed_crate = copy.deepcopy(crate)
        graph = reversed_crate.get("@graph")
        if isinstance(graph, list):
            graph.reverse()
        reverse = input_dir / (name + "_reversed.json")
        write_json(reverse, reversed_crate)
        entry = dict(binding, input_sha256=digest(raw),
                     graph_shape="array" if isinstance(graph, list) else "node object",
                     levels={})
        for level in ("minimal", "basic"):
            reports = {}
            for order, path in (("original", original), ("reversed", reverse)):
                try:
                    result = dataclasses.asdict(validator.validate_profile(path, level=level))
                except Exception as exc:
                    result = {"exception": {"type": type(exc).__name__, "message": str(exc)}}
                    (out / f"{name}_{level}_{order}.traceback.txt").write_text(
                        traceback.format_exc(), encoding="utf-8")
                write_json(out / f"{name}_{level}_{order}.json", result)
                reports[order] = result
            entry["levels"][level] = {
                **reports,
                "original_report_sha256": digest(encoded(reports["original"])),
                "reversed_report_sha256": digest(encoded(reports["reversed"])),
                "reversal_equal": encoded(reports["original"]) == encoded(reports["reversed"]),
            }
            if name == "descriptor_unresolved":
                entry["levels"][level]["refused_without_coverage"] = all(
                    report.get("passed") is False and report.get("coverage_percentage") is None
                    for report in reports.values())
            elif name == "descriptor_priority":
                entry["levels"][level]["counts_authoritative_root_only"] = all(
                    report.get("metadata", {}).get("found_count") == 2
                    for report in reports.values())
        summary["inputs"][name] = entry
        write_json(out / "summary.json", summary)
    print(json.dumps({"output": str(out), "inputs": len(inputs),
                      "profile_checks": len(inputs) * 4}))


if __name__ == "__main__":
    main()
