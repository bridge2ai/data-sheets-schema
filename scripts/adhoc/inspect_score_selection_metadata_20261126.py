#!/usr/bin/env python3
"""Audit accepted plan/publication invariants for issue 6385, 2026-11-26.

Inputs: explicit complete corpus and receipt roots. Outputs: fresh audit JSON
and an optional sanitized real-shape fixture. Never opens refused output files.
"""
import argparse
from collections import Counter
import copy
import hashlib
import json
from pathlib import Path

from data_sheets_schema.score_selection import load_evidence_index, _accepted_metadata


def write(path, value):
    raw = (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()
    with path.open("xb") as handle:
        handle.write(raw)
    if path.read_bytes() != raw:
        raise ValueError("output persistence differs")
    return hashlib.sha256(raw).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--receipts", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fixture-output", type=Path)
    args = parser.parse_args()
    index = load_evidence_index(args.receipts)
    actual_plans = {row["value"].get("actual_plan") for row in index["manifests"]}
    jobs = []
    for key, entry in sorted(index["runs"].items()):
        if key in actual_plans or entry["receipt"].get("status") != "VALIDATED_AND_PUBLISHED":
            continue
        plan = entry["plan"]
        relative = Path(plan["output"]).relative_to(Path(plan["repo_root"]))
        jobs.append((entry, args.corpus / relative))
    for row in index["manifests"]:
        manifest = row["value"]
        if manifest.get("status") != "EXPORTED_VALIDATED_REPEAT":
            continue
        entry = index["runs"][manifest["actual_plan"]]
        destination = Path(manifest["destination"])
        relative = Path("data/evaluation_repeats", *destination.parts[-4:])
        jobs.append((entry, args.corpus / relative))
    if len(jobs) != 90:
        raise ValueError(f"expected complete 90-cell corpus, found {len(jobs)}")
    extras, mismatches, maxima, rows = Counter(), Counter(), Counter(), []
    fixture = None
    for entry, path in jobs:
        expected_hash = _accepted_metadata(entry)
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected_hash:
            raise ValueError("publication hash differs from accepted receipt")
        publication = json.loads(raw)
        planned = entry["plan"]["deterministic_fields"]
        differing = [key for key, value in planned.items() if publication.get(key) != value]
        missing_or_changed = [key for key, value in planned["metadata"].items()
                              if publication.get("metadata", {}).get(key) != value]
        extra = sorted(set(publication["metadata"]) - set(planned["metadata"]))
        extras.update(extra)
        mismatches.update(differing)
        score = publication["overall_score"]
        maxima[(publication["rubric"], score.get("adjusted_max_points"), score.get("max_points"))] += 1
        rows.append({"publication": str(path), "sha256": expected_hash,
                     "whole_object_differences": differing, "metadata_extra_keys": extra,
                     "planned_metadata_missing_or_changed": missing_or_changed,
                     "adjusted_max_points": score.get("adjusted_max_points"),
                     "max_points": score.get("max_points")})
        if fixture is None and extra and publication["rubric"] == "rubric10-semantic":
            plan_fields = copy.deepcopy(planned)
            output = {key: copy.deepcopy(publication[key]) for key in planned}
            for value in (plan_fields, output):
                for key in planned["metadata"]:
                    value["metadata"][key] = "synthetic_digest_" + key
                for unit in value.get("evaluation_scope", {}).get("units", []):
                    if "id" in unit:
                        unit["id"] = "example:record"
            for key in extra:
                output["metadata"][key] = "Synthetic publication annotation."
            output["overall_score"] = copy.deepcopy(score)
            output["overall_score"].update(total_points=1, fixed_percentage=2.0, normalized_percentage=2.0)
            fixture = {"provenance": {"basis": "accepted root-scope v6 plan/publication pair",
                                      "projection": "deterministic fields and overall-score structure",
                                      "redactions": "all input digests, unit identifiers, annotation text and points"},
                       "plan_deterministic_fields": plan_fields, "published_fields": output}
    result = {"status": "PASSED", "accepted_publications": len(rows),
              "whole_object_difference_counts": dict(mismatches), "metadata_extra_key_counts": dict(extras),
              "maxima": [{"rubric": key[0], "adjusted_max_points": key[1], "max_points": key[2], "count": count}
                         for key, count in sorted(maxima.items())], "cells": rows,
              "refused_outputs_opened": False, "scoring_calls": 0}
    if any(row["planned_metadata_missing_or_changed"] for row in rows):
        raise ValueError("a planned metadata invariant differs")
    if args.fixture_output:
        if fixture is None:
            raise ValueError("no accepted metadata-extension pair found")
        result["fixture_sha256"] = write(args.fixture_output, fixture)
    print(json.dumps({"output": str(args.output), "sha256": write(args.output, result)}))


if __name__ == "__main__":
    main()
