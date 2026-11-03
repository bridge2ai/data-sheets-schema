#!/usr/bin/env python3
# Purpose: reversible scratch-only gate mutations and G2 Round 3 evidence ledger.
# Inputs: pinned archive, mutation mode / completed pytest and D35 artifacts.
# Outputs: exact mutation bytes/pins, restored source, or a JSON validation report.
# Serves the lead's G2 Round 3 test-sensitivity ruling; 2026-11-01, offline only.
import argparse
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path


SOURCE = Path("scripts/build_api_registrations.py")
ROOT = Path(__file__).resolve().parents[2]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def save(path, value):
    raw = json.dumps(value, indent=2, sort_keys=True).encode() + b"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    assert path.read_bytes() == raw


def mutate(tree, output, mode):
    tree = tree.resolve()
    assert tree.is_relative_to(ROOT.parent / "scratch-g2") and tree != ROOT
    identity = read(tree / ".g2-archive.json")
    output.mkdir(parents=True, exist_ok=False)
    path = tree / SOURCE
    before = path.read_bytes()
    source = before.decode()
    if mode == "calibration":
        node = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef)
                    and n.name == "_calibration_covered")
        lines = source.splitlines(True)
        after = "".join(lines[:node.body[0].lineno - 1] + ["    return True  # scratch mutation\n"]
                        + lines[node.end_lineno:]).encode()
    else:
        assert mode in ("context_limit_tokens", "max_input_tokens_per_call", "max_request_bytes")
        old = 'and all(limits[key] >= expected[key] for key in ADMISSION_CEILING_KEYS)'
        new = old[:-1] + f' if key != "{mode}")'
        assert source.count(old) == 1
        after = source.replace(old, new).encode()
    ast.parse(after)
    (output / "before.txt").write_bytes(before)
    (output / "mutated.txt").write_bytes(after)
    save(output / "mutation.json", {"tree": str(tree), "identity": identity, "mode": mode,
        "source": str(SOURCE), "before_sha256": sha(before), "mutated_sha256": sha(after),
        "tests": {str(p.relative_to(tree)): sha(p.read_bytes()) for p in
                  (tree / "tests/test_g2_round2.py", tree / "tests/test_bc1_generality.py")}})
    path.write_bytes(after)
    assert path.read_bytes() == after
    print(mode, sha(before), "->", sha(after))


def restore(output):
    row = read(output / "mutation.json")
    tree = Path(row["tree"])
    assert tree.is_relative_to(ROOT.parent / "scratch-g2")
    path = tree / row["source"]
    assert sha(path.read_bytes()) == row["mutated_sha256"]
    raw = (output / "before.txt").read_bytes()
    assert sha(raw) == row["before_sha256"]
    path.write_bytes(raw)
    assert path.read_bytes() == raw
    save(output / "restored.json", {"source_sha256": sha(raw), "restored": True})
    print("restored", path, sha(raw))


def outcomes(folder):
    result = {}
    for line in (folder / "events.jsonl").read_text().splitlines():
        row = json.loads(line)
        if row["when"] == "call" or row["outcome"] in {"failed", "skipped"}:
            result[row["nodeid"]] = row["outcome"]
    return result


def summary(scratch, byte_root, output):
    units = {p.parent.name: {**read(p), "sha256": sha(p.read_bytes())}
             for p in sorted(scratch.glob("*/result.json"))}
    green, red = outcomes(scratch / "final-tests"), outcomes(scratch / "red-final")
    tests = {}
    for name in ("test_g2_round2.py", "test_g2_comparator.py", "test_bc1_generality.py"):
        a, b = (scratch / "red/tests" / name).read_bytes(), (scratch / "green/tests" / name).read_bytes()
        assert a == b
        tests[name] = sha(a)
    mutations = {}
    for folder in sorted(scratch.glob("mutation-*")):
        row = read(folder / "mutation.json")
        restored = read(folder / "restored.json")
        result = outcomes(folder / "pytest")
        assert result and set(result.values()) == {"failed"}
        assert restored["restored"] and restored["source_sha256"] == row["before_sha256"]
        mutations[folder.name] = {**row, "results": result, "restored": restored}
    comparison = read(byte_root / ".bc1-byte-evidence/g2-exact-comparison.json")
    before = read(byte_root / ".bc1-byte-evidence/before/capture.json")
    after = read(byte_root / ".bc1-byte-evidence/after/capture.json")
    old = read(scratch / "byte-proof-round2-retained/.bc1-byte-evidence/after/capture.json")
    assert after["payloads"].keys() == old["payloads"].keys()
    assert all(pin["sha256"] == old["payloads"][name]["sha256"] for name, pin in after["payloads"].items())
    assert after["registration_sha256"] == old["registration_sha256"]
    collection = read(scratch / "collect/collected.json")
    result = {"units": units, "final_counts": dict(Counter(green.values())),
        "identical_red_green_tests": tests,
        "red_green": {node: {"before": outcome, "after": green[node]} for node, outcome in red.items()},
        "transitions": dict(Counter(outcome + " -> " + green[node] for node, outcome in red.items())),
        "mutations": mutations, "collection": {"items": len(collection), "unique": len(set(collection))},
        "d35": {"accepted": comparison["accepted"], "pairs": len(comparison["rows"]),
            "exact_pairs": sum(row["identical"] for row in comparison["rows"]),
            "leaves": comparison["identity_pin_ruling"]["changed_leaf_count"],
            "sizing_totals_equal": comparison["sizing_totals_equal"],
            "bindings": len(comparison["binding_checks"]),
            "verified": dict(Counter(item for row in comparison["binding_checks"] for item in row["verified"])),
            "unverified": [row for row in comparison["binding_checks"] if row["unverified"]],
            "host_packet_delta": comparison["host_packet_delta"],
            "round2_after_payloads_and_registration_identical": True,
            "comparison_sha256": sha((byte_root / ".bc1-byte-evidence/g2-exact-comparison.json").read_bytes()),
            "registration_sha256": [before["registration_sha256"], after["registration_sha256"]]}}
    save(output, result)
    print(json.dumps({key: result[key] for key in ("final_counts", "transitions", "collection", "d35")}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="action", required=True)
    mutate_parser = sub.add_parser("mutate")
    mutate_parser.add_argument("tree", type=Path)
    mutate_parser.add_argument("output", type=Path)
    mutate_parser.add_argument("mode")
    restore_parser = sub.add_parser("restore")
    restore_parser.add_argument("output", type=Path)
    summary_parser = sub.add_parser("summary")
    summary_parser.add_argument("scratch", type=Path)
    summary_parser.add_argument("byte_root", type=Path)
    summary_parser.add_argument("output", type=Path)
    args = vars(parser.parse_args())
    action = args.pop("action")
    globals()[action](**args)
