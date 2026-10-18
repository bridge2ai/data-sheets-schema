#!/usr/bin/env python3
"""Seal bounded static performance reviews without importing project code.

Purpose: verify frozen source/AST evidence and retain the reviewer's conclusions.
Inputs: --kind event-replay or cache-isolation, --repo, and --package for the
    frozen event replay package. Uses read-only Git object access for #5027.
Outputs: a new --output JSON review; refuses overwrite. No tests or benchmarks.
Issues/PR: #5015 event replay; #5027 test cache isolation and timing PR #5022.
Date: 2026-10-12.

Saved before first invocation under the new helper-provenance rule. Earlier
4588 review receipts were produced by inline stdlib checks; this script does
not claim to reproduce or to have generated those earlier artifacts.
"""

import argparse
import ast
import hashlib
import json
from pathlib import Path
import subprocess


def pin(path):
    raw = path.read_bytes()
    return {"path": str(path), "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest()}


def definitions(raw):
    return {node.name: node for node in ast.parse(raw).body
            if isinstance(node, (ast.FunctionDef, ast.ClassDef))}


def same_ast(left, right):
    return ast.dump(left, include_attributes=False) == ast.dump(right, include_attributes=False)


def event_replay(repo, package):
    freeze = json.loads((package / "freeze.json").read_text())
    for row in freeze["files"]:
        assert pin(Path(row["path"])) == row, row["path"]
    for row in freeze["source"]:
        assert pin(Path(row["path"])) == row, row["path"]
    unchanged = {}
    for relative, allowed in (
            ("src/data_sheets_schema/audit_omissions.py", {"_read", "_schema"}),
            ("src/data_sheets_schema/typed_audit.py", {"_capture"})):
        before = definitions((package / "before" / relative).read_bytes())
        after_raw = (package / "after" / relative).read_bytes()
        assert after_raw == (repo / relative).read_bytes()
        ast.parse(after_raw, feature_version=(3, 9))
        after = definitions(after_raw)
        unchanged[relative] = [name for name in before if name not in allowed]
        for name in unchanged[relative]:
            assert same_ast(before[name], after[name]), name
    metadata = json.loads((package / "metadata.json").read_text())
    for row in metadata["support"]:
        assert pin(Path(row["path"])) == row, row["path"]
    ast.parse((repo / "tests/test_schema_event_replay.py").read_bytes(), feature_version=(3, 9))
    return {
        "kind": "schema-event-replay-5015-independent-static-review",
        "verdict": "STATIC_CLEAR_UNEXECUTED",
        "freeze": pin(package / "freeze.json"),
        "verified_freeze_files": len(freeze["files"]),
        "source": freeze["source"], "unchanged_definitions": unchanged,
        "findings": [],
        "checks": [
            "The complete pure SafeLoader event pass precedes composition, retaining the old depth-before-composer precedence.",
            "Parser/Unicode error and event-storage overflow return to the original UniqueLoader second parse; overflow creates no new rejection.",
            "The private event source changes only check_event/peek_event/get_event; the existing composer, resolver, unique-key and scalar constructors consume original event values and source marks.",
            "Fresh loader state is per invocation, disposed in finally. Input bytes, traversal limits, mapping checks, root comparison and complete import-closure replay remain each call.",
            "Only the three existing schema mapping validation sites opt in. Default YAML and JSON reads retain their original implementation.",
            "Nine proposed test functions cover 44 cases: literal old oracle, complete cause/message equality, grammar/types, directives, aliases/cycles, depth versus early composer errors, both retention fallbacks, private objects, and actual captured schema parity.",
            "The withdrawn catalog cache is absent from the reviewed definitions; original packet cache and long-test support files remain pinned."
        ],
        "cap_assessment": {
            "current_events": 65536, "observed_real_stream_events_approx": 63467,
            "recommendation": "131072 offers useful bounded headroom; not a correctness requirement. Either limit falls back to the old parser without accepting or rejecting new inputs.",
            "memory_limit": "Counts/events and retained text characters are explicit bounds, not an RSS bound."
        },
        "limits": ["No project imports, tests or benchmarks by reviewer.",
                   "Installed pure PyYAML source was inspected; runtime differential and real-schema timing validation remain root-owned."]
    }


def cache_isolation(repo):
    relative = "tests/test_schema/test_datacite_relationships.py"
    before = subprocess.check_output(["git", "show", "HEAD:" + relative], cwd=repo)
    after = (repo / relative).read_bytes()
    old_tree, new_tree = ast.parse(before), ast.parse(after, feature_version=(3, 9))
    target = "test_truncation_still_announces_itself_if_it_ever_happens"
    old_defs = {n.name: n for n in ast.walk(old_tree) if isinstance(n, ast.FunctionDef)}
    new_defs = {n.name: n for n in ast.walk(new_tree) if isinstance(n, ast.FunctionDef)}
    assert old_defs.keys() == new_defs.keys()
    for name in old_defs:
        if name != target:
            assert same_ast(old_defs[name], new_defs[name]), name
    notes = repo / "notes/agent_performance_2026-10-12/ci-cache-isolation.json"
    evidence = json.loads(notes.read_text())
    assert evidence["standalone"]["counts"] == {"tests": 1, "failures": 0, "errors": 0, "skipped": 0}
    assert evidence["ordered"]["counts"] == {"tests": 2, "failures": 1, "errors": 0, "skipped": 0}
    helpers = [repo / "scripts/adhoc" / name for name in (
        "2026-10-12_trace_5022_ci_failure.py", "2026-10-12_trace_5027_cache_receipts.py")]
    for helper in helpers:
        ast.parse(helper.read_bytes(), feature_version=(3, 9))
    assert pin(helpers[1])["sha256"] == evidence["helper"]["sha256"]
    return {
        "kind": "datacite-cache-isolation-5027-independent-static-review",
        "verdict": "STATIC_CLEAR_UNEXECUTED", "findings": [],
        "source": pin(repo / relative), "portable_pre_fix_receipt": pin(notes),
        "documentation": pin(notes.with_suffix(".md")), "helpers": [pin(p) for p in helpers],
        "unchanged_test_functions": len(old_defs) - 1,
        "checks": [
            "The only existing test-body change is the truncation control; other test ASTs are exact and production cache/guard code is unchanged.",
            "Outer temporary build/text caches isolate the fixture from ambient process state; inner temporary caches prevent the deliberately prewarmed normal result from bypassing the synthetic cap.",
            "The cap and both inner caches restore with context managers on success or exception; outer originals are also restored rather than cleared or replaced permanently.",
            "Assertions strengthen the old generic more marker: actual relationship vocabulary first five values, exact omitted count and full rendered line, plus different capped text and restored normal text.",
            "The real schema-digest functions and real subsequent identifier/schema-sync test remain in use. No cache-key, sharding, timing or acceptance relaxation is added.",
            "Portable notes distinguish confirmed standalone/ordered pre-fix outcomes from pending post-fix validation and preserve the Python-version/timing limitations."
        ],
        "limits": ["Static source and portable receipt review only; no project runtime by reviewer.",
                   "Root must validate the repaired ordered pair and relevant CI lane; this review does not claim those results."]
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kind", required=True, choices=["event-replay", "cache-isolation"])
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--package", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.kind == "event-replay":
        if args.package is None:
            parser.error("event-replay requires --package")
        report = event_replay(args.repo, args.package)
    else:
        report = cache_isolation(args.repo)
    report["review_helper"] = pin(Path(__file__).resolve())
    report["readers_released"] = True
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2)
        stream.write("\n")
    print(json.dumps(pin(args.output)))


if __name__ == "__main__":
    main()
