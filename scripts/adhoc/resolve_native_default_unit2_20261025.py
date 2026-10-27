#!/usr/bin/env python3
"""Resolve N2 default recovery against current guards (2026-10-25, #4354).

Inputs: cached 7c target and explicit three-way recovery conflicts. Outputs:
scoped source edits; preserve newer legacy native implementations unchanged.
Run once after recover_native_default_unit2_20261025.py, before manual review.
"""
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
PREFIX = ROOT / "src/data_sheets_schema"
CONFLICT = re.compile(r"^<<<<<<< cached-target-7c1002cae\n(.*?)^=======\n(.*?)^>>>>>>> preowner-a33d80d84\n", re.M | re.S)


def resolve(name, decisions):
    path = PREFIX / name
    text = path.read_text()
    count = 0
    def replace(match):
        nonlocal count
        left, right = match.groups()
        choice = decisions[count]
        count += 1
        return choice(left, right)
    text = CONFLICT.sub(replace, text)
    assert count == len(decisions), (name, count)
    path.write_text(text)


def main():
    # Current legacy modules already include original-receipt and lifecycle
    # hardening. New native-shared entrypoints use new engines directly; the
    # old launch/readback paths need no refactor for that integration.
    for name in ("native_execution", "native_execution_registration", "native_execution_gates", "native_attempt_supervisor"):
        relative = f"src/data_sheets_schema/{name}.py"
        raw = subprocess.check_output(["git", "show", f"7c1002cae:{relative}"], cwd=ROOT)
        (ROOT / relative).write_bytes(raw)
    resolve("receipt_completion_policy.py", [
        lambda left, right: right[:right.index("    version =")] + left,
    ])
    resolve("schema/d4d_generation_record.yaml", [
        lambda left, right: left + "        required: true\n\n" + right,
        lambda left, right: left + "\n" + right,
    ])
    resolve("audit_omissions.py", [
        lambda left, right: left + right,
        lambda left, right: right[:right.index("def _read(")] + left,
        lambda left, right: "        if _schema_events and not json_only:\n            value = _schema_yaml(text)\n        el" + right[8:],
        lambda left, right: right.replace('_mapping(raw, "schema")', '_mapping(raw, "schema", _schema_events=True)'),
        lambda left, right: "        replay = _capture_schema(root, frozen_read, strict=True, logical_paths=logical_paths)\n",
    ])


if __name__ == "__main__":
    main()
