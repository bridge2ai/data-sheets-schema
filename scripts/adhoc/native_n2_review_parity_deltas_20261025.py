#!/usr/bin/env python3
# Purpose: inspect N2d/#4354 historical/current instruction deltas, 2026-10-25.
# Inputs: seven hash-pinned r1 text/diff artifacts. Outputs: a new JSON review
# bundle under the requested evidence directory. Never executes rendered commands.
"""Expose embedded recorder JSON as exact structural differences for review."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shlex


PINS = {
    "historical-current-target-api25-instruction.txt": "489a4b59f675990bf2b37921be1a234bdac9dbe05f6ea3c031ed2c5b06dfcc78",
    "historical-hypothetical-native26-instruction.txt": "0b693a535bdccfb6d8f5f49410fc84b82c8af396cb2d82b68a3c84257f344ca4",
    "current-api25-instruction.txt": "2e8efbeb608959740cd80ecdcddee35e965928525fe4564046c68bb0d3314083",
    "current-native26-instruction.txt": "cc503fd057e73ccef748f3f3d4926011d4b7eb1738a6d68bca3160846d5d9241",
    "instructions.diff": "00001a136c7277cbed96f56ed27aec0a543a0f4ff94c3b8a6c33fa3f2e2c8094",
    "historical-to-current-api.diff": "305bfe1ac460818260680281cd3becaa6c5ab7c2a21d5f0c60cd4dd7668f15a0",
    "historical-to-current-native.diff": "06d6c6624605ad4191403f9ef339d1f49043cd3b0fa27c84f335e3fb12df76f2",
}
MISSING = {"__missing_key__": True}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def pairs(rows):
    result = {}
    for key, value in rows:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load(raw):
    return json.loads(raw, object_pairs_hook=pairs)


def expand(value):
    """Decode embedded JSON without hiding original serialized byte identity."""
    if isinstance(value, dict):
        result = {key: expand(item) for key, item in value.items() if key != "raw_json"}
        if "raw_json" in value:
            raw = value["raw_json"].encode("utf-8")
            if "sha256" in value and sha(raw) != value["sha256"]:
                raise ValueError("embedded raw_json/hash mismatch")
            result["raw_json"] = {
                "utf8_bytes": len(raw), "sha256": sha(raw), "decoded": expand(load(raw))}
        return result
    if isinstance(value, list):
        return [expand(item) for item in value]
    return value


def differences(before, after, path=""):
    if type(before) is type(after) and before == after:
        return []
    if type(before) is dict and type(after) is dict:
        result = []
        for key in sorted(before.keys() | after.keys()):
            child = path + "/" + key.replace("~", "~0").replace("/", "~1")
            result.extend(differences(before.get(key, MISSING), after.get(key, MISSING), child))
        return result
    if type(before) is list and type(after) is list and len(before) == len(after):
        return [row for index, (left, right) in enumerate(zip(before, after))
                for row in differences(left, right, path + "/" + str(index))]
    return [{"path": path, "before": before, "after": after}]


def commands(text):
    result = {}
    for name, command in re.findall(r"^([a-z][a-z0-9_]*):\n\n```bash\n([^\n]+)\n```", text, re.M):
        if name in result:
            raise ValueError(f"duplicate command role: {name}")
        result[name] = shlex.split(command, posix=True)
    if "recorder" not in result or len(result) != text.count("```bash\n"):
        raise ValueError("missing recorder or incompletely parsed command fences")
    recorder = result["recorder"]
    if recorder.count("--render-spec-json") != 1:
        raise ValueError("ambiguous render spec argument")
    index = recorder.index("--render-spec-json") + 1
    metadata = expand(load(recorder[index]))
    recorder[index] = "<render-spec-json separately expanded>"
    return result, metadata


def native_context(text):
    marker = "## Complete selected generation context\n\n"
    if text.count(marker) != 1:
        raise ValueError("ambiguous complete generation context")
    value, _end = json.JSONDecoder(object_pairs_hook=pairs).raw_decode(text.split(marker)[1])
    return expand(value)


def api_receipt(text):
    marker = "Registration: "
    if text.count(marker) != 1:
        raise ValueError("ambiguous API receipt registration")
    return expand(load(text.split(marker)[1]))


def excerpt(text, first, last, *, strip=False):
    if text.count(first) != 1 or text.count(last) != 1:
        raise ValueError("ambiguous rule boundary")
    selected = text[text.index(first):text.index(last)].encode("utf-8")
    if strip:
        selected = selected.strip()
    return {"bytes": len(selected), "sha256": sha(selected)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    text, identities = {}, {}
    for name, expected in PINS.items():
        path = args.evidence / name
        raw = path.read_bytes()
        if sha(raw) != expected:
            raise ValueError("input hash differs: " + str(path))
        text[name] = raw.decode("utf-8")
        identities[name] = {"path": str(path), "bytes": len(raw), "sha256": expected}
    old_api, new_api = (text[name] for name in (
        "historical-current-target-api25-instruction.txt", "current-api25-instruction.txt"))
    old_native, new_native = (text[name] for name in (
        "historical-hypothetical-native26-instruction.txt", "current-native26-instruction.txt"))
    old_commands, old_metadata = commands(old_native)
    new_commands, new_metadata = commands(new_native)
    report = {
        "scope": "Read-only structural comparison; no scientific equivalence or execution certification.",
        "inputs": identities,
        "helper": {"path": str(Path(__file__)), "sha256": sha(Path(__file__).read_bytes())},
        "native_command_rosters": {"before": list(old_commands), "after": list(new_commands)},
        "native_command_token_changes": differences(old_commands, new_commands),
        "native_recorder_metadata_changes": differences(old_metadata, new_metadata),
        "native_generation_context_changes": differences(native_context(old_native), native_context(new_native)),
        "api_receipt_registration_changes": differences(api_receipt(old_api), api_receipt(new_api)),
        "hunk_headers": {name: [line for line in value.splitlines() if line.startswith("@@ ")]
                         for name, value in text.items() if name.endswith(".diff")},
        "rules": {label: {
            "r9": excerpt(value, "- A slot whose declared range is an enumeration", "\n- `raw_data_format`"),
            "uniform": excerpt(value, "UNIFORM DECISION RULES", "## Shared generation rules v1", strip=True),
        } for label, value in (("old_api", old_api), ("old_native", old_native),
                               ("new_api", new_api), ("new_native", new_native))},
        "interpretation": "Every changed leaf is retained; path/hash changes are not automatically judged harmless.",
    }
    args.output.mkdir(parents=True, exist_ok=False)
    output = args.output / "structural_deltas.json"
    with output.open("x") as stream:
        json.dump(report, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    print(json.dumps({"output": str(output), "sha256": sha(output.read_bytes()),
                      "native_metadata_changes": len(report["native_recorder_metadata_changes"]),
                      "native_context_changes": len(report["native_generation_context_changes"]),
                      "native_command_token_changes": len(report["native_command_token_changes"])}))


if __name__ == "__main__":
    main()
