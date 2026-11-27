#!/usr/bin/env python3
"""Verify saved root/legacy plans against original records; issue 6358, 2026-11-25.

Inputs: two plan-only outputs, Git data ref and committed scope declarations.
Output: fresh JSON verification receipt. Never executes a scorer or changes data.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


# Definition hashes frozen in reviewed candidate 26b74b67e before composition.
FROZEN_DEFINITIONS = {
    "rubric10": "84f42966ae968881aa65263c8d4f32a0ffe6988a85d24ea8d5a933e99ee1354d",
    "rubric20": "6beda6a0a46230b9c6128f9251c9eac0b5771f022c10b47cbc752f017432de52",
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def verify_definition(plan, repo_root):
    family = plan["identity"]["rubric"].removesuffix("-semantic")
    source = f".claude/agents/d4d-{family}-semantic.md"
    overrides = f"data/rubric/root_scope_v6/{family}_definition_overrides.json"
    expected = {
        "source_path": source, "source_sha256": sha((repo_root / source).read_bytes()),
        "overrides_path": overrides, "overrides_sha256": sha((repo_root / overrides).read_bytes()),
        "composed_sha256": FROZEN_DEFINITIONS[family],
    }
    assert plan["definition_provenance"] == expected
    assert plan["inputs"]["agent-definition.md"] == {
        "source": "root_scope_v6_composition", "sha256": FROZEN_DEFINITIONS[family],
    }
    assert plan["deterministic_fields"]["metadata"]["instrument_sha256"] == FROZEN_DEFINITIONS[family]
    descriptor = next(json.loads(line) for line in plan["prompt"].splitlines()
                      if line.startswith("{") and '"required_deterministic_fields"' in line)
    assert descriptor["definition_provenance"] == expected
    beginning = plan["prompt"].index("BEGIN agent-definition.md (")
    header, rest = plan["prompt"][beginning:].split("\n", 1)
    composed, _ = rest.split("\nEND agent-definition.md\n", 1)
    raw = composed.encode()
    assert sha(raw) == FROZEN_DEFINITIONS[family]
    assert header == f"BEGIN agent-definition.md ({len(raw)} bytes; sha256 {sha(raw)})"
    assert (repo_root / source).read_text() not in plan["prompt"]
    assert (repo_root / overrides).read_text() not in plan["prompt"]
    assert not (repo_root / f".claude/agents/d4d-{family}-semantic-v6.md").exists()
    return expected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--root-plans", type=Path, required=True)
    parser.add_argument("--legacy-plans", type=Path, required=True)
    parser.add_argument("--data-ref", default="0a1bb84d1449edc27822fd76ffcfd1df7e913cd9")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root_raw, legacy_raw = args.root_plans.read_bytes(), args.legacy_plans.read_bytes()
    root, legacy = json.loads(root_raw), json.loads(legacy_raw)
    assert root["record_count"] == legacy["record_count"] == 15
    assert root["evaluation_count"] == legacy["evaluation_count"] == 30
    keyed = {(plan["identity"]["d4d_file"], plan["identity"]["rubric"]): plan
             for plan in legacy["plans"]}
    assert len(keyed) == 30
    records, outputs, runs, definitions = {}, set(), set(), {}
    for plan in root["plans"]:
        identity = plan["identity"]
        path = identity["d4d_file"]
        old = keyed.pop((path, identity["rubric"]))
        raw = subprocess.run(["git", "-C", str(args.repo_root), "show", args.data_ref + ":" + path],
                             check=True, capture_output=True).stdout
        assert (args.repo_root / path).read_bytes() == raw
        digest = sha(raw)
        assert plan["inputs"]["record.yaml"]["sha256"] == old["inputs"]["record.yaml"]["sha256"] == digest
        declaration_path = Path(plan["inputs"]["scope-context.json"]["source"])
        declaration_raw = declaration_path.read_bytes()
        declaration = json.loads(declaration_raw)
        assert set(declaration) == {"policy", "input_sha256", "reason"}
        assert declaration["policy"] == "root_dataset_v1" and declaration["input_sha256"] == digest
        assert declaration["reason"].strip()
        fields = plan["deterministic_fields"]
        assert fields["metadata"]["scope_context_sha256"] == sha(declaration_raw)
        assert plan["inputs"]["scope-context.json"]["sha256"] == sha(declaration_raw)
        scope = fields["evaluation_scope"]
        assert scope["selection_policy"] == "root_dataset_v1"
        assert scope["policy"] == "single_dataset" and scope["collection_metadata_inherited"] is False
        assert len(scope["units"]) == 1 and scope["units"][0]["path"] == "#"
        assert fields["applicability_context"] == old["deterministic_fields"]["applicability_context"]
        for key in ("context_sha256", "input_sha256", "rubric_sha256", "evidence_authority_sha256"):
            assert fields["metadata"][key] == old["deterministic_fields"]["metadata"][key]
        assert identity["version"] == "6.0" and old["identity"]["version"] == "3.0"
        definitions[identity["rubric"]] = verify_definition(plan, args.repo_root)
        assert plan["instrument"] != old["instrument"]
        assert declaration_raw.decode() in plan["prompt"]
        assert str(args.repo_root) not in plan["prompt"]
        assert "--scope-context" in plan["validation_command"]
        assert "--semantic-version" in plan["validation_command"]
        assert plan["runner_sha256"] == sha(Path(plan["runner"]).read_bytes())
        for source, expected in plan["validation_sha256"].items():
            assert sha(Path(source).read_bytes()) == expected
        assert not Path(plan["run_directory"]).exists() and not Path(old["run_directory"]).exists()
        assert not Path(plan["output"]).exists()
        outputs.add(plan["output"])
        runs.add(plan["run_directory"])
        row = {"record": path, "record_sha256": digest, "scope_file": str(declaration_path.relative_to(args.repo_root)),
               "scope_sha256": sha(declaration_raw), "root_unit": scope["units"][0],
               "legacy_scope": old["deterministic_fields"]["evaluation_scope"]}
        if path in records:
            assert records[path] == row
        records[path] = row
    assert not keyed and len(records) == 15 and len(outputs) == len(runs) == 30
    result = {"data_ref": args.data_ref, "record_count": len(records), "evaluation_count": len(outputs),
              "root_plan_sha256": sha(root_raw), "legacy_plan_sha256": sha(legacy_raw),
              "run_directories_created": 0, "scoring_calls": 0,
              "records": list(records.values()), "definition_provenance": definitions}
    with args.output.open("x") as handle:
        json.dump(result, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print(json.dumps({"receipt": str(args.output), "sha256": sha(args.output.read_bytes()),
                      "records": len(records), "evaluations": len(outputs),
                      "legacy_unit_counts": {path: len(row["legacy_scope"]["units"]) for path, row in records.items()},
                      "run_directories_created": 0}, indent=2))


if __name__ == "__main__":
    main()
