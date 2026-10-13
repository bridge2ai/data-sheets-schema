#!/usr/bin/env python3
"""Seal the final #5015 event replay review with its actual retention cap.

Purpose: reuse the preserved static review checks and bind the cap successor.
Inputs: --repo and --package; sibling 2026-10-12_4588_performance_static_reviews.py.
Outputs: new --output JSON, refusing overwrite. No application imports/tests.
Issue/PR: #5015, agent-performance implementation; no PR created by this helper.
Date: 2026-10-12.
"""
import argparse
import ast
import importlib.util
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    helper = Path(__file__).with_name("2026-10-12_4588_performance_static_reviews.py")
    spec = importlib.util.spec_from_file_location("saved_static_review_checks", helper)
    checks = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checks)
    freeze = json.loads((args.package / "freeze.json").read_text())
    for row in freeze["files"] + freeze["source"]:
        assert checks.pin(Path(row["path"])) == row
    prior_path = Path(freeze["prior"]["path"])
    assert checks.pin(prior_path) == freeze["prior"]
    prior = json.loads(prior_path.read_text())
    for row in prior["files"]:
        assert checks.pin(Path(row["path"])) == row
    for relative in ("src/data_sheets_schema/audit_omissions.py",
                     "src/data_sheets_schema/typed_audit.py", "tests/test_schema_event_replay.py"):
        old = (prior_path.parent / "after" / relative).read_bytes()
        new = (args.package / "after" / relative).read_bytes()
        expected = old.replace(b"MAX_SCHEMA_EVENTS = 65_536", b"MAX_SCHEMA_EVENTS = 131_072", 1)
        assert new == expected == (args.repo / relative).read_bytes()
        ast.parse(new, feature_version=(3, 9))
    unchanged = {}
    for relative, allowed in (
            ("src/data_sheets_schema/audit_omissions.py", {"_read", "_schema"}),
            ("src/data_sheets_schema/typed_audit.py", {"_capture"})):
        before = checks.definitions((args.package / "before" / relative).read_bytes())
        after = checks.definitions((args.package / "after" / relative).read_bytes())
        unchanged[relative] = [name for name in before if name not in allowed]
        for name in unchanged[relative]:
            assert checks.same_ast(before[name], after[name])
    metadata = json.loads((prior_path.parent / "metadata.json").read_text())
    for row in metadata["support"]:
        assert checks.pin(Path(row["path"])) == row
    report = {
        "kind": "schema-event-replay-5015-final-independent-static-review",
        "verdict": "STATIC_CLEAR_UNEXECUTED", "findings": [],
        "freeze": checks.pin(args.package / "freeze.json"),
        "prior_freeze": freeze["prior"], "source": freeze["source"],
        "unchanged_definitions": unchanged,
        "checks": [
            "Complete pure SafeLoader depth scan precedes all composition, retaining depth-before-composer error precedence.",
            "Parser/Unicode failure and storage overflow use the original UniqueLoader second parse; neither changes input admission.",
            "Only event-source accessors are replaced; existing composer/resolver/constructors consume original values and source marks. Fresh loader state and disposal are per call.",
            "Byte/mapping/traversal/root/import-closure checks remain fresh. Only schema validation opts in; default records/JSON remain unchanged.",
            "Nine test functions/44 cases compare the literal original oracle including complete error-cause messages, depth versus early composer errors, both storage fallbacks, directives/types/aliases, fresh objects and real schema parity.",
            "Current successor differs from frozen01 only in the event cap; test bytes are exact. Original long-node/cache tests and schema support pins remain exact."
        ],
        "cap_assessment": {"observed_real_stream_events_approx": 63467,
                           "memory_limit": "Event and retained-character bounds are not an RSS bound."},
        "limits": ["Static review only; no application imports, tests or benchmarks by reviewer.",
                   "Runtime differential validation and end-to-end performance evidence remain root-owned."]
    }
    tree = ast.parse((args.repo / "src/data_sheets_schema/audit_omissions.py").read_bytes())
    cap = [ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
           and any(isinstance(t, ast.Name) and t.id == "MAX_SCHEMA_EVENTS" for t in n.targets)]
    assert cap == [131072]
    report["cap_assessment"]["current_events"] = cap[0]
    report["cap_assessment"]["recommendation"] = (
        "Adopted 131072-event cap provides bounded headroom above the observed roughly "
        "63467-event schema. Retention overflow remains an equivalent parser fallback."
    )
    report["review_helper"] = checks.pin(Path(__file__).resolve())
    report["supporting_review_helper"] = checks.pin(helper)
    report["readers_released"] = True
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2)
        stream.write("\n")
    print(json.dumps(checks.pin(args.output)))


if __name__ == "__main__":
    main()
