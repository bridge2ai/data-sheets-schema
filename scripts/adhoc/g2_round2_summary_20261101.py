#!/usr/bin/env python3
# Purpose: join G2 round 2 immutable pytest/D35 evidence without hiding failures.
# Inputs: scratch round2 root, byte-proof root, output JSON. Outputs: pinned counts,
# red/green node matrix, changed code pins and hash-verification coverage.
# Serves the G2 round 2 review report; 2026-11-01. Offline, standard library only.
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


def read(path):
    return json.loads(path.read_bytes())


def nodes(folder):
    events = [json.loads(line) for line in (folder / "events.jsonl").read_text().splitlines()]
    outcomes = {}
    for event in events:
        if event["when"] == "call" or event["outcome"] in {"failed", "skipped"}:
            outcomes[event["nodeid"]] = event["outcome"]
    return outcomes


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("scratch", type=Path)
    parser.add_argument("byte_root", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--verify-capture", choices=("before", "after"))
    args = parser.parse_args()
    if args.verify_capture:
        side = args.verify_capture
        capture_path = args.byte_root / ".bc1-byte-evidence" / side / "capture.json"
        capture = read(capture_path)
        assert not capture["errors"] and len(capture["payloads"]) == 20
        pins = []
        for pin in capture["payloads"].values():
            pins.append(pin)
            for key in ("host_packet", "host_request"):
                if key in pin:
                    pins.append(pin[key])
        for pin in pins:
            raw = (args.byte_root / pin["path"]).read_bytes()
            assert raw and len(raw) == pin["bytes"] and hashlib.sha256(raw).hexdigest() == pin["sha256"]
        registration = capture_path.with_name("registration.json").read_bytes()
        assert capture["registration_sha256"] == hashlib.sha256(registration).hexdigest()
        if side == "before":
            previous = read(args.scratch / "byte-proof-round1-retained/.bc1-byte-evidence/before/capture.json")
            assert previous["payloads"].keys() == capture["payloads"].keys()
            assert all(previous["payloads"][name]["sha256"] == pin["sha256"] for name, pin in capture["payloads"].items())
        value = {"condition": side, "payloads": 20, "checked_pins": len(pins),
                 "reproduces_round1_base": side == "before", "registration_sha256": capture["registration_sha256"],
                 "capture_sha256": hashlib.sha256(capture_path.read_bytes()).hexdigest()}
        args.output.write_text(json.dumps(value, indent=2) + "\n")
        assert read(args.output) == value
        print(json.dumps(value))
        return
    units = {}
    for result in sorted(args.scratch.glob("*/result.json")):
        units[result.parent.name] = {**read(result), "path": str(result),
            "sha256": hashlib.sha256(result.read_bytes()).hexdigest()}
    final = {}
    # These complete files cover the narrow requested scope. The comparator's
    # final execution replaces the earlier execution at the preceding head.
    for name in ("green-regressions", "narrow", "final-regressions"):
        if (args.scratch / name / "result.json").exists():
            final.update(nodes(args.scratch / name))
    red = nodes(args.scratch / "red-final")
    matrix = {node: {"before": status, "after": final.get(node, "NOT_RUN")}
              for node, status in sorted(red.items())}
    comparison_path = args.byte_root / ".bc1-byte-evidence/g2-exact-comparison.json"
    comparison = read(comparison_path)
    checked = comparison["binding_checks"]
    after = read(args.byte_root / ".bc1-byte-evidence/after/registration.json")
    previous = read(args.scratch / "byte-proof-round1-retained/.bc1-byte-evidence/after/registration.json")
    old_code = previous["bounded_carry"]["contract"]["code"]
    new_code = after["bounded_carry"]["contract"]["code"]
    collection = read(args.scratch / "collect/collected.json")
    old_base = read(args.scratch / "byte-proof-round1-retained/.bc1-byte-evidence/before/capture.json")
    new_base = read(args.byte_root / ".bc1-byte-evidence/before/capture.json")
    assert old_base["payloads"].keys() == new_base["payloads"].keys()
    assert all(old_base["payloads"][name]["sha256"] == pin["sha256"] for name, pin in new_base["payloads"].items())
    overlays = {}
    for name in ("test_g2_round2.py", "test_g2_comparator.py"):
        baseline_test = (args.scratch / "red/tests" / name).read_bytes()
        final_test = (args.scratch / "green/tests" / name).read_bytes()
        assert baseline_test == final_test
        overlays[name] = hashlib.sha256(final_test).hexdigest()
    result = {"units": units, "narrow_unique_counts": dict(Counter(final.values())),
        "narrow_by_file": {file: dict(Counter(status for node, status in final.items() if node.split("::")[0] == file))
                           for file in sorted({node.split("::")[0] for node in final})},
        "red_green": matrix,
        "identical_red_green_test_blobs": overlays,
        "transitions": dict(Counter(row["before"] + " -> " + row["after"] for row in matrix.values())),
        "collection": {"items": len(collection), "unique": len(set(collection))},
        "d35": {"accepted": comparison["accepted"], "pairs": len(comparison["rows"]),
            "exact_pairs": sum(row["identical"] for row in comparison["rows"]),
            "sizing_totals_equal": comparison["sizing_totals_equal"], "base_reproduces_round1_payloads": True,
            "ruling": comparison["identity_pin_ruling"], "binding_checks": len(checked),
            "unverified": [row for row in checked if row["unverified"]],
            "verified": dict(Counter(item for row in checked for item in row["verified"])),
            "comparison_sha256": hashlib.sha256(comparison_path.read_bytes()).hexdigest(),
            "code_pins_moved_this_round": {name: {"before": old_code[name], "after": new_code[name]}
                                            for name in old_code if old_code[name] != new_code[name]}}}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(result, sort_keys=True, indent=2).encode() + b"\n"
    args.output.write_bytes(raw)
    assert args.output.read_bytes() == raw
    print(json.dumps({key: result[key] for key in ("narrow_unique_counts", "narrow_by_file", "transitions", "collection", "d35")}, indent=2))


if __name__ == "__main__":
    main()
